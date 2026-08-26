import { spawnSync } from "node:child_process";
import process from "node:process";

function windowsPathToWsl(path) {
    const match = /^([A-Za-z]):[\\/](.*)$/.exec(path);
    if (!match) {
        throw new Error(`cannot translate Windows repository path: ${path}`);
    }
    return `/mnt/${match[1].toLowerCase()}/${match[2].replaceAll("\\", "/")}`;
}

const forwarded = process.argv.slice(2);
let invocation;
if (process.platform === "win32") {
    invocation = {
        command: "wsl.exe",
        args: [
            "-d",
            process.env.STRLING_PRODUCTION_WSL_DISTRIBUTION || "Ubuntu",
            "--cd",
            windowsPathToWsl(process.cwd()),
            "--",
            "bash",
            "-lc",
            'exec python3 -m tooling.production_certification "$@"',
            "strling-production-certification",
            ...forwarded,
        ],
    };
} else {
    invocation = {
        command: "python3",
        args: ["-m", "tooling.production_certification", ...forwarded],
    };
}

const completed = spawnSync(invocation.command, invocation.args, {
    cwd: process.cwd(),
    env: process.env,
    stdio: "inherit",
});
if (completed.error) {
    console.error(
        `production certification launcher failed: ${completed.error.message}`,
    );
    process.exit(2);
}
process.exit(completed.status ?? 2);
