import { Pattern } from "./simply/pattern.js";

/**
 * Compiles a STRling Pattern object into a final regex string.
 * This function should be used in Node.js environment.
 *
 * @param {Pattern} pattern The pattern to compile.
 * @param {string} target The emission target (e.g., "pcre2", "re2").
 * @param {object} options Additional compilation options.
 * @returns {string} The compiled regex string.
 */
export function compileNode(pattern, target = "pcre2", options = {}) {
    // In Node.js environment
    if (typeof require !== "undefined") {
        const { spawnSync } = require("child_process");

        const irJson = pattern.toString();

        // Path to your Python compiler script - adjust as needed
        const compilerCliPath = "../../../../tooling/parse_strl.py";

        const args = [compilerCliPath, "-", `--emit=${target}`];
        if (options.flags) {
            args.push(`--flags=${options.flags}`);
        }

        const process = spawnSync("python3", args, {
            input: irJson,
            encoding: "utf-8",
        });

        if (process.error) {
            throw new Error(
                `Failed to spawn compiler: ${process.error.message}`
            );
        }

        if (process.status !== 0) {
            throw new Error(`Compiler exited with error:\n${process.stderr}`);
        }

        const result = JSON.parse(process.stdout);
        return result.emitted;
    } else {
        throw new Error("Node.js environment required for compilation.");
    }
}

/**
 * Compiles a STRling Pattern object in a browser environment.
 * This sends the IR to a server endpoint that runs the compiler.
 *
 * @param {Pattern} pattern The pattern to compile.
 * @param {string} endpoint URL of the compiler service endpoint.
 * @param {string} target The emission target (e.g., "pcre2", "re2").
 * @returns {Promise<string>} A promise that resolves to the compiled regex string.
 */
export async function compileWeb(pattern, endpoint, target = "pcre2") {
    const irJson = pattern.toString();

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            ir: irJson,
            target: target,
        }),
    });

    if (!response.ok) {
        throw new Error(`Compilation failed: ${response.statusText}`);
    }

    const result = await response.json();
    return result.emitted;
}

/**
 * Creates a RegExp object from a STRling pattern.
 * In Node environment, compiles directly; in browser, must use a service endpoint.
 *
 * @param {Pattern} pattern The pattern to convert.
 * @param {string} flags RegExp flags (e.g., "g", "i").
 * @param {object} options Compilation options including target and endpoint.
 * @returns {RegExp} The compiled regular expression object.
 */
export function toRegExp(pattern, flags = "", options = {}) {
    const target = options.target || "pcre2";

    // Node.js environment
    if (typeof require !== "undefined") {
        const regexStr = compileNode(pattern, target, { flags });
        return new RegExp(regexStr, flags);
    }
    // Browser environment
    else if (options.endpoint) {
        // Can't be synchronous in browser
        throw new Error("In browser environment, use toRegExpAsync instead");
    } else {
        throw new Error("Must provide endpoint for browser compilation");
    }
}

/**
 * Creates a RegExp object from a STRling pattern asynchronously.
 * Useful for browser environments.
 *
 * @param {Pattern} pattern The pattern to convert.
 * @param {string} flags RegExp flags (e.g., "g", "i").
 * @param {object} options Compilation options including target and endpoint.
 * @returns {Promise<RegExp>} Promise resolving to the compiled RegExp object.
 */
export async function toRegExpAsync(pattern, flags = "", options = {}) {
    const target = options.target || "pcre2";
    const endpoint = options.endpoint;

    if (!endpoint) {
        throw new Error("Must provide endpoint for compilation");
    }

    const regexStr = await compileWeb(pattern, endpoint, target);
    return new RegExp(regexStr, flags);
}
