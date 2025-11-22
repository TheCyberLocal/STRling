/**
 * STRling TypeScript Entry Point
 *
 * This module provides a small, idiomatic TypeScript surface for consumers.
 * It re-exports the primary parts of the internal `STRling` tree so that
 * TypeScript projects can import from the package root.
 */

import * as simply from "./STRling/simply/index.js";
import { parse, parseToArtifact, ParseError } from "./STRling/core/parser.js";
import { Compiler } from "./STRling/core/compiler.js";

export { simply, parse, parseToArtifact, ParseError, Compiler };

export default {
    simply,
    parse,
    parseToArtifact,
    ParseError,
    Compiler,
};
