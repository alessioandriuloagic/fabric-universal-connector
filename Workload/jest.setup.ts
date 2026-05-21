/**
 * jest.setup.ts
 *
 * Executed after the Jest test framework is installed, before each test file.
 * Extends the `expect` global with @testing-library/jest-dom matchers.
 */
import "@testing-library/jest-dom";
