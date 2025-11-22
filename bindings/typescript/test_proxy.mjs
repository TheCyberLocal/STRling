import * as s from './src/STRling/simply/index.js';

console.log('Testing digit()...');
const d = s.digit();
console.log('Type of d:', typeof d);
console.log('d is function?', typeof d === 'function');
console.log('d.node:', d.node);

try {
    const d3 = d(3);
    console.log('Successfully called d(3)');
    console.log('d3.node:', d3.node);
} catch (e) {
    console.log('Error calling d(3):', e.message);
}
