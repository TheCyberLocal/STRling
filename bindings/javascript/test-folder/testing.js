import { simply } from "../STRling/index.js";

const examplePattern = simply.letter();
console.log(examplePattern); // Outputs the object
console.log(`${examplePattern}`); // Outputs: [A-Za-z]
console.log(examplePattern(2, 4)); // Outputs: Pattern instance with repetition applied

console.log(simply.between(1, 2));
console.log(simply.between(3, 2));
