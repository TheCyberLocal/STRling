import STRling from './dist/index.js';

const s = STRling.simply;

// Use inChars which creates a character class
const phone = s.merge(
    s.start(),
    s.capture(s.digit(3)),
    s.may(s.inChars("-. ")),
    s.capture(s.digit(3)),
    s.may(s.inChars("-. ")),
    s.capture(s.digit(4)),
    s.end()
);

const regex = s.toRegExp(phone);
console.log("TypeScript output:", regex.source);

// Also test just the character class
const charClass = s.inChars("-. ");
const charRegex = s.toRegExp(charClass);
console.log("Character class:", charRegex.source);
