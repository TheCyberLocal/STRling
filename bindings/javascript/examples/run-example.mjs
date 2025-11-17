import pkg from "../dist/index.js";

const { simply, parse, Compiler } = pkg;

// Parse a small pattern
const [flags, node] = parse("abc");
console.log("Parsed node:", node);

// Compile the node to IR
const compiler = new Compiler();
const ir = compiler.compile(node);
console.log("Compiled IR:", ir);

// Use the simply API (demonstrative)
if (simply && (simply).lit) {
  const lit = (simply).lit("hello");
  console.log("Simply lit:", lit);
}

console.log("Run-example completed");
