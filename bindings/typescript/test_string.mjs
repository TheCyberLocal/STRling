import * as s from './src/STRling/simply/index.js';

const d = s.digit();
console.log('digit() String:', String(d));

const d3 = s.digit()(3);
console.log('digit()(3) String:', String(d3));

const d34 = s.digit(3);
console.log('digit(3) String:', String(d34));
