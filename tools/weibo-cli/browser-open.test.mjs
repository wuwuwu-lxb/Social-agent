import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { test } from "node:test";
import { browserOpenCommand, wrapExecFile } from "./browser-open.mjs";

test("PowerShell receives the complete OAuth URL without opening a browser", {
  skip: process.platform !== "win32",
}, () => {
  const url = "https://example.invalid/oauth/authorize?response_type=code&redirect_uri=http%3A%2F%2F127.0.0.1%3A47821%2Fcallback&state=a'b&code_challenge=abc-_&code_challenge_method=S256";
  const command = browserOpenCommand(url);
  const script = Buffer.from(command.args.at(-1), "base64").toString("utf16le");
  const probe = "function Start-Process { param([string]$FilePath) [Console]::Write($FilePath) }\n";
  const output = execFileSync(command.executable, [
    ...command.args.slice(0, -1),
    Buffer.from(probe + script, "utf16le").toString("base64"),
  ], { encoding: "utf8", windowsHide: true });
  assert.equal(output, url);
});

test("only the CLI browser opener is replaced; other subprocesses pass through", () => {
  const calls = [];
  const original = (...args) => { calls.push(args); return "child"; };
  const wrapped = wrapExecFile(original);
  const callback = () => {};
  const url = "https://example.invalid/?a=1&b=2";
  assert.equal(wrapped("cmd", ["/c", "start", '""', url], callback), "child");
  assert.deepEqual(calls[0], [
    browserOpenCommand(url).executable,
    browserOpenCommand(url).args,
    { windowsHide: true },
    callback,
  ]);
  wrapped("cmd", ["/c", "echo", "test"], callback);
  assert.deepEqual(calls[1], ["cmd", ["/c", "echo", "test"], callback]);
  wrapped("powershell.exe", ["-Command", "test"], callback);
  assert.deepEqual(calls[2], ["powershell.exe", ["-Command", "test"], callback]);
});
