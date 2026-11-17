import { chromium } from "playwright";
import { createWeiboAdapter } from "@webmcp-bridge/adapter-weibo";
import { mkdir, open, unlink } from "node:fs/promises";
import path from "node:path";

let context;
let adapter;
let session;
let lock;
let lockPath;
let result = { ok: false, status: "internal_error", submitted: false };
try {
  let text = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    text += chunk;
    if (text.length > 32768) throw new Error("input_too_large");
  }
  const request = JSON.parse(text);
  if (request.operation !== "statuses.update.preview") {
    throw new Error("unsupported_operation");
  }
  if (typeof request.status !== "string" || !request.status.trim() ||
      [...request.status].length > 140 || !path.isAbsolute(request.profile || "")) {
    throw new Error("validation_error");
  }
  const profile = path.resolve(request.profile);
  await mkdir(path.dirname(profile), { recursive: true });
  lockPath = `${profile}.social-agent.lock`;
  try {
    lock = await open(lockPath, "wx");
    await lock.writeFile(String(process.pid));
  } catch (error) {
    if (error.code === "EEXIST") throw new Error("busy");
    throw error;
  }
  context = await chromium.launchPersistentContext(profile, {
    channel: "msedge", headless: true, viewport: { width: 1280, height: 900 },
  });
  let blocked = 0;
  await context.route("**/*", async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (/(^|\.)weibo\.com$/.test(url.hostname) &&
        /^\/ajax\/(statuses|comments|attitudes)\//.test(url.pathname) &&
        !["GET", "HEAD", "OPTIONS"].includes(request.method())) {
      blocked++;
      await route.abort();
    } else {
      await route.continue();
    }
  });
  const page = context.pages()[0] || await context.newPage();
  adapter = createWeiboAdapter();
  session = { page };
  await adapter.start(session);
  await page.goto("https://weibo.com/", { waitUntil: "domcontentloaded", timeout: 35000 });
  await page.waitForFunction(() =>
    /\/(newlogin|login)(\/|$)/.test(location.pathname) ||
    Boolean(document.querySelector("textarea[placeholder*='新鲜事'], textarea[placeholder*='分享']")),
  null, { timeout: 15000 }).catch(() => {});
  const authenticated = await page.evaluate(() =>
    !/\/(newlogin|login)(\/|$)/.test(location.pathname) &&
    !/扫码登录|登录注册更精彩/.test(document.body?.innerText || "") &&
    Boolean(document.querySelector("textarea[placeholder*='新鲜事'], textarea[placeholder*='分享']")));
  if (!authenticated) throw new Error("auth_required");
  const preview = await adapter.callTool({
    name: "post.create",
    input: { text: request.status, dryRun: true },
  }, session);
  const ok = preview?.ok === true && preview?.dryRun === true &&
    preview?.submitVisible === true && blocked === 0;
  result = {
    ok,
    status: ok ? "preview_ready" : "preview_failed",
    authenticated,
    dry_run: true,
    submit_visible: preview?.submitVisible === true,
    submitted: false,
    blocked_mutations: blocked,
    adapter_error: preview?.error?.code || null,
  };
} catch (error) {
  const known = new Set(["validation_error", "unsupported_operation", "busy", "auth_required", "input_too_large"]);
  result = { ok: false, status: known.has(error.message) ? error.message : "browser_error", submitted: false };
} finally {
  if (session && adapter) await adapter.stop(session).catch(() => {});
  if (context) await context.close().catch(() => {});
  if (lock) {
    await lock.close().catch(() => {});
    await unlink(lockPath).catch(() => {});
  }
  console.log(JSON.stringify(result));
}
