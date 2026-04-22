/**
 * STRling Error Classes - Rich Error Handling for Instructional Diagnostics
 *
 * This module provides enhanced error classes that deliver context-aware,
 * instructional error messages. The STRlingParseError class stores detailed
 * information about syntax errors including position, context, and beginner-friendly
 * hints for resolution.
 */

/**
 * Rich parse error with position tracking and instructional hints.
 *
 * This error class transforms parse failures into learning opportunities by
 * providing:
 * - The specific error message
 * - The exact position where the error occurred
 * - The full line of text containing the error
 * - A beginner-friendly hint explaining how to fix the issue
 */
export class STRlingParseError extends Error {
    /** A concise description of what went wrong */
    message: string;

    /** The character position (0-indexed) where the error occurred */
    pos: number;

    /** The full input text being parsed */
    text: string;

    /** An instructional hint explaining how to fix the error */
    hint: string | null;

    /**
     * Initialize a STRlingParseError.
     *
     * @param message - A concise description of what went wrong
     * @param pos - The character position (0-indexed) where the error occurred
     * @param text - The full input text being parsed (default: "")
     * @param hint - An instructional hint explaining how to fix the error (default: null)
     */
    constructor(
        message: string,
        pos: number,
        text: string = "",
        hint: string | null = null,
    ) {
        super(message);
        this.message = message;
        this.pos = pos;
        this.text = text;
        this.hint = hint;
        this.name = "STRlingParseError";

        // Set the prototype explicitly for proper instanceof checks
        Object.setPrototypeOf(this, STRlingParseError.prototype);
    }

    /**
     * Format the error in the visionary state format.
     *
     * @returns A formatted error message with context and hints
     */
    private formatError(): string {
        if (!this.text) {
            // Fallback to simple format if no text provided
            return `${this.message} at position ${this.pos}`;
        }

        // Find the line containing the error
        const lines = this.text.split("\n");
        let currentPos = 0;
        let lineNum = 1;
        let lineText = "";
        let col = this.pos;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            const lineLen = line.length + 1; // +1 for newline
            if (currentPos + lineLen > this.pos) {
                lineNum = i + 1;
                lineText = line;
                col = this.pos - currentPos;
                break;
            }
            currentPos += lineLen;
        }

        // If error is beyond the last line
        if (!lineText && lines.length > 0) {
            lineNum = lines.length;
            lineText = lines[lines.length - 1];
            col = lineText.length;
        } else if (!lineText) {
            lineText = this.text;
            col = this.pos;
        }

        // Build the formatted error message
        const parts: string[] = [
            `STRling Parse Error: ${this.message}`,
            "",
            `> ${lineNum} | ${lineText}`,
            `>   | ${" ".repeat(col)}^`,
        ];

        if (this.hint) {
            parts.push("");
            parts.push(`Hint: ${this.hint}`);
        }

        return parts.join("\n");
    }

    /**
     * Get the formatted error message.
     *
     * @returns The formatted error string
     */
    toFormattedString(): string {
        return this.formatError();
    }

    /**
     * Override toString to return formatted error.
     *
     * @returns The formatted error string
     */
    toString(): string {
        return this.formatError();
    }
}

/**
 * Raised by an emitter when a valid AST/IR cannot be safely lowered to the
 * target engine's syntax. Examples:
 *   - The IR exceeds the configured `maxDepth` (host-stack safety guard).
 *   - The IR uses a variable-length lookbehind against an engine (PCRE2)
 *     that requires fixed-length lookbehinds.
 *
 * Per the Signpost Pattern, every message must (1) state the failure,
 * (2) explain the constraint, and (3) direct the user to a fix.
 */
export class STRlingCompilationError extends Error {
    /** Stable machine-readable code (e.g. "VLB_NOT_SUPPORTED", "MAX_DEPTH"). */
    code: string;

    /** Target engine that triggered the rejection (e.g. "pcre2"). */
    engine: string;

    constructor(
        message: string,
        code: string = "EMITTER_ERROR",
        engine: string = "pcre2",
    ) {
        super(message);
        this.name = "STRlingCompilationError";
        this.message = message;
        this.code = code;
        this.engine = engine;
        Object.setPrototypeOf(this, STRlingCompilationError.prototype);
    }

    toString(): string {
        return `STRlingCompilationError: ${this.message}`;
    }
}

/**
 * Diagnostic warning emitted alongside a successfully-produced pattern.
 *
 * Warnings do not abort emission. They are collected on the artifact's
 * `warnings` array (see `emitWithDiagnostics`). The canonical use-case is
 * `REDOS_RISK` for nested unbounded quantifiers and overlapping alternations.
 */
export class STRlingWarning {
    code: string;
    message: string;

    constructor(code: string, message: string) {
        this.code = code;
        this.message = message;
    }

    toString(): string {
        return `STRlingWarning [${this.code}]: ${this.message}`;
    }
}
