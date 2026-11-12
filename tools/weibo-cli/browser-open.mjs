import path from "node:path";

export function browserOpenCommand(url) {
  const quotedUrl = `'${url.replaceAll("'", "''")}'`;
  const command = `Start-Process -FilePath ${quotedUrl}`;
  const executable = path.win32.join(
    process.env.SystemRoot || "C:\\Windows",
    "System32",
    "WindowsPowerShell",
    "v1.0",
    "powershell.exe",
  );
  return {
    executable,
    args: [
      "-NoProfile",
      "-NonInteractive",
      "-EncodedCommand",
      Buffer.from(command, "utf16le").toString("base64"),
    ],
  };
}

export function wrapExecFile(original) {
  return function (file, args, ...rest) {
    // Only replace the official CLI's Windows browser-opening invocation.
    if (
      file.toLowerCase() === "cmd" &&
      Array.isArray(args) &&
      args.length === 4 &&
      args[0] === "/c" &&
      args[1] === "start" &&
      args[2] === '""' &&
      /^https?:\/\//i.test(args[3])
    ) {
      const command = browserOpenCommand(args[3]);
      return original(command.executable, command.args, { windowsHide: true }, ...rest);
    }
    return original(file, args, ...rest);
  };
}
