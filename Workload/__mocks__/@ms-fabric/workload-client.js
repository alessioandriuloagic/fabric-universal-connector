/**
 * __mocks__/@ms-fabric/workload-client.js
 *
 * Manual Jest mock for the @ms-fabric/workload-client package.
 * The real package ships ESM (uuid dependency) which Jest cannot parse in
 * CommonJS mode. This mock exposes only the values that ItemCRUDController
 * and other controller files use at runtime.
 */

// Mirror the PayloadType enum values used in ItemCRUDController.ts
const PayloadType = Object.freeze({
  InlineBase64: "InlineBase64",
});

module.exports = {
  PayloadType,
};
