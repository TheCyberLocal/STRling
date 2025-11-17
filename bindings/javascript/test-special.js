import { specialChar } from './src/STRling/simply/static.js';

const pattern = specialChar();
const regex = pattern.toString();
console.log("Pattern:", regex);
console.log("Length:", regex.length);

// Try to use it as a regex
try {
    const re = new RegExp(regex);
    console.log("✓ Compiles successfully!");
    console.log("Matches '\\':", re.test("\\"));
    console.log("Matches ']':", re.test("]"));
    console.log("Matches '!':", re.test("!"));
} catch (e) {
    console.log("✗ Compilation failed:", e.message);
}
