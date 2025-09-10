// jest.config.mjs
export default {
    preset: "ts-jest",
    testEnvironment: "node",
    testMatch: ["**/__tests__/**/*.test.[jt]s?(x)"],
    // Only list extensions Jest *can't* infer as ESM from package.json
    extensionsToTreatAsEsm: [".ts", ".tsx"],
    transform: {}, // no Babel/ts-jest transforms right now
};
