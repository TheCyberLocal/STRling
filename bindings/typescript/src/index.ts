/** Browser-safe TypeScript facade over the canonical raw-WASM boundary. */

import * as simply from "./STRling/simply/index.js";

export * from "./STRling/interop.js";
export * from "./STRling/compiler.js";
export { simply };

export default { simply };
