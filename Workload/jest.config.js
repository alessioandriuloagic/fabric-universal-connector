/** @type {import('jest').Config} */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "jsdom",
  // Runs after the test framework is installed — adds jest-dom matchers
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  roots: ["<rootDir>/app"],
  testMatch: ["**/__tests__/**/*.ts?(x)", "**/?(*.)+(spec|test).ts?(x)"],
  transform: {
    "^.+\\.tsx?$": [
      "ts-jest",
      {
        tsconfig: {
          noUnusedLocals: false,
          // importHelpers requires tslib which isn't available for shared/ files
          importHelpers: false,
          // Allow ts-jest to resolve shared/ paths (outside Workload/)
          baseUrl: ".",
          paths: {
            "src/*": ["./app/*"],
            "shared/*": ["../shared/*"],
          },
        },
      },
    ],
  },
  moduleNameMapper: {
    // The @ms-fabric/workload-client ships ESM (uuid dependency) — use a manual mock
    "^@ms-fabric/workload-client$": "<rootDir>/__mocks__/@ms-fabric/workload-client.js",
    // Ignore CSS/SCSS imports in tests
    "\\.(css|scss)$": "<rootDir>/__mocks__/styleMock.js",
    // Resolve workspace-relative shared/ paths via non-relative alias
    "^shared/(.*)$": "<rootDir>/../shared/$1",
  },
  collectCoverageFrom: [
    "app/**/*.{ts,tsx}",
    "!app/**/*.d.ts",
    "!app/**/index.ts",
  ],
};


