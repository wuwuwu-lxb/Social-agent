import childProcess from "node:child_process";
import { syncBuiltinESMExports } from "node:module";
import { wrapExecFile } from "./browser-open.mjs";

if (process.platform === "win32") {
  childProcess.execFile = wrapExecFile(childProcess.execFile);
  syncBuiltinESMExports();
}

await import("./node_modules/@weibo-ai/weibo-cli/dist/index.js");
