// Example: TypeScript usage of the published STRling package
import { simply, parse, Compiler } from "..";

// Parse a small pattern
const [flags, node] = parse("abc");
console.log("Parsed node:", node);

// Compile the node to IR
const compiler = new Compiler();
const ir = compiler.compile(node);
console.log("Compiled IR:", ir);

// Use the simply API (demonstrative)
if ((simply as any).lit) {
    const lit = (simply as any).lit("hello");
    console.log("Simply lit:", lit);
}

console.log("TS example completed");
