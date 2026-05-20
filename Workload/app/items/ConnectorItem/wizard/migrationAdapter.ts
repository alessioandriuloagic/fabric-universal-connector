/**
 * migrationAdapter.ts
 *
 * Backward-compatibility layer for ConnectorItem definitions.
 *
 * Schema history:
 *   v1 (schemaVersion "1.0.0") — single-connector discriminated union.
 *       Top-level `moduleType` field selects among crm / businesscentral / sql.
 *   v2 (schemaVersion "2.0.0") — multi-connector array.
 *       All three connector types co-exist; `enabled` flags which are active.
 *
 * All load boundaries in the application should call `normalizeToV2` so that
 * the rest of the codebase only ever operates on `MultiConnectorItemDefinition`.
 */
import {
  ConnectorItemDefinition,
  MultiConnectorItemDefinition,
  AnyConnectorItemDefinition,
  ConnectorEntry,
  CrmConnectorEntry,
  BusinessCentralConnectorEntry,
  SqlConnectorEntry,
} from "../ConnectorItemDefinition";
import { buildDefaultConnectors } from "./connectorRegistry";

// ── Type guards ──────────────────────────────────────────────────

/** Returns true when the payload is already a v2 (multi-connector) definition. */
export function isV2Definition(
  def: AnyConnectorItemDefinition,
): def is MultiConnectorItemDefinition {
  return (def as MultiConnectorItemDefinition).schemaVersion === "2.0.0";
}

// ── Migration ────────────────────────────────────────────────────

/**
 * Promotes a v1 single-connector definition to the v2 multi-connector shape.
 *
 * Migration strategy:
 *  1. Build a default connectors array (all disabled) from the registry.
 *  2. Find the slot matching the v1 `moduleType` and replace it with the
 *     v1 data (source, auth, entities) — setting `enabled: true`.
 *  3. Shared fields (storage, scheduling, etc.) are carried over verbatim.
 *
 * The result is a valid `MultiConnectorItemDefinition` that produces identical
 * runtime behaviour to the original v1 payload.
 */
export function migrateV1toV2(v1: ConnectorItemDefinition): MultiConnectorItemDefinition {
  // Start from registry defaults (all connectors disabled)
  const connectors: ConnectorEntry[] = buildDefaultConnectors();

  const idx = connectors.findIndex((c) => c.connectorType === v1.moduleType);
  if (idx !== -1) {
    if (v1.moduleType === "crm") {
      const migrated: CrmConnectorEntry = {
        connectorType: "crm",
        enabled: true,
        status: v1.state === "configured" ? "valid" : "unconfigured",
        source: v1.source,
        auth: v1.authentication,
        entities: v1.entities,
      };
      connectors[idx] = migrated;
    } else if (v1.moduleType === "businesscentral") {
      const migrated: BusinessCentralConnectorEntry = {
        connectorType: "businesscentral",
        enabled: true,
        status: v1.state === "configured" ? "valid" : "unconfigured",
        source: v1.source,
        auth: v1.authentication,
        entities: v1.entities,
      };
      connectors[idx] = migrated;
    } else if (v1.moduleType === "sql") {
      const migrated: SqlConnectorEntry = {
        connectorType: "sql",
        enabled: true,
        status: v1.state === "configured" ? "valid" : "unconfigured",
        source: v1.source,
        auth: v1.authentication,
        entities: v1.entities,
      };
      connectors[idx] = migrated;
    }
  }

  return {
    schemaVersion: "2.0.0",
    state: v1.state,
    connectors,
    storage: v1.storage,
    scheduling: v1.scheduling,
    features: v1.features,
    runtime: v1.runtime,
    metadata: v1.metadata,
  };
}

/**
 * Coerces any saved definition (v1 or v2) to `MultiConnectorItemDefinition`.
 *
 * Call this at every load boundary so the rest of the application only ever
 * sees v2 definitions.  v2 payloads are returned as-is (no defensive copy).
 */
export function normalizeToV2(
  def: AnyConnectorItemDefinition,
): MultiConnectorItemDefinition {
  if (isV2Definition(def)) return def;
  return migrateV1toV2(def as ConnectorItemDefinition);
}

/**
 * Returns only the enabled connectors from a v2 definition.
 *
 * Use this wherever the runtime or service layer currently reads a single
 * active connector — iterate the returned array instead.
 */
export function getEnabledConnectors(
  def: MultiConnectorItemDefinition,
): ConnectorEntry[] {
  return def.connectors.filter((c) => c.enabled);
}
