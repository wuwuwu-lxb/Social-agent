import { chromium } from "playwright";
import { createWeiboAdapter } from "@webmcp-bridge/adapter-weibo";
import { mkdir, open, unlink } from "node:fs/promises";
import path from "node:path";
import {prepareComposer, requestHasStatus, submitPost} from "./publish.mjs";

let context;
let adapter;
let session;
let lock;
let lockPath;
const gate = {
  allow:false, clickStarted:false, sent:0, observedWrites:0, observedUpdates:0,
  blocked:0, blockedUpdate:0, lastUpdateTarget:null, lastWriteTarget:null,
};
let result = { ok: false, status: "internal_error", submitted: false };
try {
  let text = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    text += chunk;
    if (text.length > 32768) throw new Error("input_too_large");
  }
  const request = JSON.parse(text);
  if (!["statuses.update.preview", "statuses.update.publish", "statuses.update.preflight"].includes(request.operation)) {
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
    const incoming = route.request();
    const url = new URL(incoming.url());
    const weiboHost = /(^|\.)weibo\.(com|cn)$/.test(url.hostname);
    if (weiboHost && !["GET", "HEAD", "OPTIONS"].includes(incoming.method())) {
      let fields;
      try {fields=incoming.postDataJSON();} catch {fields=null;}
      const exactStatus = (typeof fields?.status === "string" &&
        fields.status.replace(/\r\n?/g, "\n").trim() === request.status.replace(/\r\n?/g, "\n").trim()) ||
        requestHasStatus(incoming.postData() || "", incoming.headers()["content-type"], request.status);
      if (gate.allow && gate.sent===0 && incoming.method()==="POST" &&
          url.pathname==="/ajax/statuses/update" && exactStatus && url.hostname==="weibo.com") {
        gate.sent++;
        gate.lastUpdateTarget = `${url.hostname}${url.pathname}`;
        await route.continue();
        return;
      }
      blocked++;
      gate.blocked++;
      gate.lastWriteTarget = `${url.hostname}${url.pathname}`;
      if (url.pathname==="/ajax/statuses/update") {
        gate.blockedUpdate++;
        gate.lastUpdateTarget = `${url.hostname}${url.pathname}`;
      }
      await route.abort();
    } else {
      await route.continue();
    }
  });
  const page = context.pages()[0] || await context.newPage();
  page.on("request", incoming => {
    const url = new URL(incoming.url());
    const weiboHost = /(^|\.)weibo\.(com|cn)$/.test(url.hostname);
    if (weiboHost && !["GET", "HEAD", "OPTIONS"].includes(incoming.method())) {
      gate.observedWrites++;
      gate.lastWriteTarget = `${url.hostname}${url.pathname}`;
      if (url.pathname==="/ajax/statuses/update") {
        gate.observedUpdates++;
        gate.lastUpdateTarget = `${url.hostname}${url.pathname}`;
      }
    }
  });
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
  if (request.operation === "statuses.update.publish") {
    result = await submitPost(context, page, request.status, gate);
  } else if (request.operation === "statuses.update.preflight") {
    const prepared=await prepareComposer(page,request.status);
    result={ok:true,status:"preflight_ready",submitted:false,ai_declaration_selected:prepared.ai_declaration_selected,
      visibility:prepared.visibility,authenticated:true,blocked_mutations:blocked};
  } else {
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
  }
} catch (error) {
  const known = new Set(["validation_error", "unsupported_operation", "busy", "auth_required", "input_too_large"]);
  const requestObserved = gate.sent > 0;
  result = { ok: false,
    status: gate.clickStarted && requestObserved ? "unknown" :
      gate.clickStarted ? "failed" : known.has(error.message) ? error.message : "browser_error",
    submitted: requestObserved ? null : false,
    reason: error.message || "browser_error",
    request_observed: gate.sent > 0,
    blocked_update_requests: gate.blockedUpdate,
    blocked_mutations: gate.blocked,
    request_target: gate.lastUpdateTarget,
    observed_write_requests: gate.observedWrites,
    observed_update_requests: gate.observedUpdates,
    last_write_target: gate.lastWriteTarget };
} finally {
  if (session && adapter) await adapter.stop(session).catch(() => {});
  if (context) await context.close().catch(() => {});
  if (lock) {
    await lock.close().catch(() => {});
    await unlink(lockPath).catch(() => {});
  }
  console.log(JSON.stringify(result));
}
