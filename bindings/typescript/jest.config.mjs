// jest.config.mjs
export default {
    preset: "ts-jest/presets/default-esm",
    testEnvironment: "node",
    testMatch: ["**/__tests__/**/*.test.[jt]s?(x)"],
    extensionsToTreatAsEsm: [".ts", ".tsx"],
    moduleNameMapper: {
        "^(\\.{1,2}/.*)\\.js$": "$1",
    },
    transform: {
        "^.+\\.tsx?$": [
            "ts-jest",
            {
                useESM: true,
            },
        ],
        "^.+\\.jsx?$": [
            "ts-jest",
            {
                useESM: true,
            },
        ],
    },
    transformIgnorePatterns: [
        "node_modules/(?!(.*\\.mjs$))",
    ],
};
