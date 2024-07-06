import { simply } from 'strling';

// Example usage
const pattern = simply.anyOf('a', 'b', 'c');
console.log(pattern.toString());  // Output: (a|b|c)
