/**
 * STRling Compiler Utilities - Pattern Compilation and RegExp Creation
 *
 * This module provides utilities for compiling STRling Pattern objects into
 * executable regular expressions. It replaces the legacy Python-bridge compiler
 * with a pure TypeScript implementation that runs locally in both Node.js
 * and browser environments.
 */

import { Pattern } from "./simply/pattern.js";
import { Compiler } from "./core/compiler.js";
import { emit as emitPCRE2 } from "./emitters/pcre2.js";

const compiler = new Compiler();

/**
 * Compiles a STRling Pattern object into a final regex string.
 *
 * @param pattern - The pattern to compile.
 * @param target - The emission target (currently only "pcre2" is supported).
 * @param options - Additional compilation options.
 * @returns The compiled regex string.
 */
export function compileNode(
    pattern: Pattern,
    target = "pcre2",
    options: any = {}
): string {
    if (target !== "pcre2") {
        throw new Error(
            `Target '${target}' not supported in TypeScript binding.`
        );
    }

    const ir = compiler.compile(pattern.node);

    let flagsObj: any = {};
    if (typeof options.flags === "string") {
        flagsObj = {
            ignoreCase: options.flags.includes("i"),
            multiline: options.flags.includes("m"),
            dotAll: options.flags.includes("s"),
            unicode: options.flags.includes("u"),
            extended: options.flags.includes("x"),
        };
    } else if (typeof options.flags === "object") {
        flagsObj = options.flags;
    }

    return emitPCRE2(ir, flagsObj);
}

/**
 * Compiles a STRling Pattern object (Web compatibility wrapper).
 *
 * In the TypeScript binding, this runs locally and synchronously, but returns
 * a Promise to maintain compatibility with the legacy async API.
 *
 * @param pattern - The pattern to compile.
 * @param endpoint - Ignored (compilation is local).
 * @param target - The emission target.
 * @returns A promise that resolves to the compiled regex string.
 */
export async function compileWeb(
    pattern: Pattern,
    endpoint: string,
    target = "pcre2"
): Promise<string> {
    return compileNode(pattern, target);
}

/**
 * Creates a RegExp object from a STRling pattern.
 *
 * @param pattern - The pattern to convert.
 * @param flags - RegExp flags (e.g., "g", "i").
 * @param options - Compilation options.
 * @returns The compiled regular expression object.
 */
export function toRegExp(
    pattern: Pattern,
    flags = "",
    options: any = {}
): RegExp {
    // Pass flags to compileNode if they affect the pattern (like 'x' or 's' in some engines),
    // but JS RegExp takes flags in constructor.
    // However, emitPCRE2 might add inline flags (?i) if we pass them.
    // If we pass flags to RegExp constructor, we shouldn't duplicate them in the pattern?
    // JS RegExp doesn't support inline flags for everything.
    // But emitPCRE2 emits (?i) etc.

    // If we pass flags to compileNode, it emits (?i).
    // If we pass flags to new RegExp(..., flags), it sets the flags on the object.
    // Usually we want one or the other.
    // If we use toRegExp, we probably want the JS RegExp flags.

    // But wait, compileNode logic above parses flags string and passes to emitPCRE2.
    // If I pass "i" to compileNode, it emits "(?i)...".
    // If I then do new RegExp("(?i)...", "i"), is that valid?
    // JS RegExp supports (?i) in recent versions (ES2018+ for s, etc).
    // But usually you don't mix them.

    // The legacy compiler.js did:
    // const regexStr = compileNode(pattern, target, { flags });
    // return new RegExp(regexStr, flags);

    // So it did BOTH.
    // Let's stick to that behavior.

    const regexStr = compileNode(pattern, options.target || "pcre2", {
        ...options,
        flags,
    });
    return new RegExp(regexStr, flags);
}

/**
 * Creates a RegExp object from a STRling pattern asynchronously.
 *
 * @param pattern - The pattern to convert.
 * @param flags - RegExp flags.
 * @param options - Compilation options.
 * @returns Promise resolving to the compiled RegExp object.
 */
export async function toRegExpAsync(
    pattern: Pattern,
    flags = "",
    options: any = {}
): Promise<RegExp> {
    return toRegExp(pattern, flags, options);
}
