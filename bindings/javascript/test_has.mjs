import * as s from './dist/STRling/simply/index.js';

const pattern = s.has(s.digit());
console.log('has(digit) node:', JSON.stringify(pattern.node, null, 2));

const pattern2 = s.hasNot(s.digit());
console.log('hasNot(digit) node:', JSON.stringify(pattern2.node, null, 2));

const startP = s.start();
console.log('start() node:', JSON.stringify(startP.node, null, 2));

const endP = s.end();
console.log('end() node:', JSON.stringify(endP.node, null, 2));
