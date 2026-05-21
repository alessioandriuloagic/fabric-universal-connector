/**
 * shared/utils/validation.ts
 *
 * Common validation functions used across wizard steps in all workload
 * frontends. Each function returns `true` when the value is valid.
 *
 * Design principles:
 *   - No framework dependencies (plain TypeScript, browser-compatible)
 *   - Pure functions — no side effects, easy to unit-test
 *   - Fast-fail: checks cheapest conditions first
 *   - Returns boolean, not an error message (separate i18n concern)
 *
 * Validators are grouped by domain:
 *   - General  (non-empty, length, format)
 *   - URL / network
 *   - Azure / Entra ID
 *   - Schedule (cron)
 *   - SQL / database
 *   - Dataverse / Business Central
 */

// ── General ───────────────────────────────────────────────────────────────────

/**
 * Returns true when the string is not empty after trimming whitespace.
 */
export function isNonEmpty(value: string): boolean {
  return value.trim().length > 0;
}

/**
 * Returns true when the string length is between `min` and `max` (inclusive)
 * after trimming.
 */
export function isLengthBetween(
  value: string,
  min: number,
  max: number,
): boolean {
  const len = value.trim().length;
  return len >= min && len <= max;
}

/**
 * Returns true when the string contains only alphanumerics, hyphens, and
 * underscores (safe for use as an identifier or key).
 */
export function isSafeIdentifier(value: string): boolean {
  return /^[a-zA-Z0-9_-]+$/.test(value.trim());
}

// ── URL / network ─────────────────────────────────────────────────────────────

/**
 * Returns true when `value` is a syntactically valid http or https URL.
 *
 * Does NOT check reachability — use for client-side format validation only.
 */
export function isValidUrl(value: string): boolean {
  if (!isNonEmpty(value)) return false;
  try {
    const url = new URL(value.trim());
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

/**
 * Returns true when `value` is a valid https URL (rejects plain http).
 *
 * Use for endpoints that MUST be encrypted (e.g. Dataverse, BC, backend API).
 */
export function isValidHttpsUrl(value: string): boolean {
  if (!isNonEmpty(value)) return false;
  try {
    return new URL(value.trim()).protocol === "https:";
  } catch {
    return false;
  }
}

// ── Azure / Entra ID ──────────────────────────────────────────────────────────

/**
 * Returns true when `value` is a well-formed GUID / UUID
 * (case-insensitive, with or without curly braces).
 *
 * Example valid inputs:
 *   "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
 *   "{6BA7B810-9DAD-11D1-80B4-00C04FD430C8}"
 */
export function isValidGuid(value: string): boolean {
  const cleaned = value.trim().replace(/^\{|\}$/g, "");
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    cleaned,
  );
}

/**
 * Returns true when `value` looks like a valid Entra ID tenant ID or domain.
 *
 * Accepts:
 *   - GUID format:  "72f988bf-86f1-41af-91ab-2d7cd011db47"
 *   - Domain format: "contoso.onmicrosoft.com" / "contoso.com"
 */
export function isValidTenantId(value: string): boolean {
  if (!isNonEmpty(value)) return false;
  const trimmed = value.trim();
  return isValidGuid(trimmed) || /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(trimmed);
}

/**
 * Returns true when `value` is a valid Azure Key Vault secret reference URI.
 *
 * Expected format:
 *   https://<vault-name>.vault.azure.net/secrets/<secret-name>[/<version>]
 */
export function isValidKeyVaultSecretUri(value: string): boolean {
  if (!isNonEmpty(value)) return false;
  return /^https:\/\/[a-zA-Z0-9-]+\.vault\.azure\.net\/secrets\/[a-zA-Z0-9-]+(\/[a-zA-Z0-9]+)?$/.test(
    value.trim(),
  );
}

// ── Schedule / cron ───────────────────────────────────────────────────────────

// Allowed field patterns for a 5-field Unix cron expression.
const CRON_FIELD_PATTERN =
  /^(\*|[0-9]+(-[0-9]+)?(\/[0-9]+)?)(,([0-9]+(-[0-9]+)?(\/[0-9]+)?))*$/;

// Valid ranges for each cron field [min, max].
const CRON_FIELD_RANGES: Array<[number, number]> = [
  [0, 59], // minute
  [0, 23], // hour
  [1, 31], // day of month
  [1, 12], // month
  [0, 7],  // day of week (0 and 7 both = Sunday)
];

/**
 * Returns true when `value` is a syntactically valid 5-field cron expression.
 *
 * Supports:
 *   - Wildcards:  `* * * * *`
 *   - Single values: `0 9 * * 1`
 *   - Ranges: `0 9-17 * * 1-5`
 *   - Steps: `0 */6 * * *`
 *   - Lists: `0 8,12,16 * * *`
 *
 * Does NOT support named values (JAN, MON, etc.) or @-macros (@daily).
 */
export function isValidCronExpression(value: string): boolean {
  if (!isNonEmpty(value)) return false;
  const fields = value.trim().split(/\s+/);
  if (fields.length !== 5) return false;

  return fields.every((field, index) => {
    if (field === "*") return true;
    if (!CRON_FIELD_PATTERN.test(field)) return false;

    // Validate numeric bounds for each sub-expression.
    const [min, max] = CRON_FIELD_RANGES[index];
    const parts = field.split(",");
    return parts.every((part) => {
      const stepParts = part.split("/");
      const rangeParts = stepParts[0].split("-");

      for (const num of rangeParts) {
        if (num === "*") continue;
        const n = parseInt(num, 10);
        if (isNaN(n) || n < min || n > max) return false;
      }

      if (stepParts[1] !== undefined) {
        const step = parseInt(stepParts[1], 10);
        if (isNaN(step) || step < 1) return false;
      }

      return true;
    });
  });
}

// ── Dataverse / CRM ───────────────────────────────────────────────────────────

/**
 * Returns true when `value` is a plausible Dataverse environment URL.
 *
 * Expected format:
 *   https://<org>.crm[N].dynamics.com   (e.g. https://myorg.crm4.dynamics.com)
 *   https://<org>.<region>.dynamics.com  (gov clouds)
 */
export function isValidDataverseUrl(value: string): boolean {
  if (!isValidHttpsUrl(value)) return false;
  try {
    const { hostname } = new URL(value.trim());
    return /^[a-zA-Z0-9-]+\.(crm[0-9]*|api)\.dynamics\.com$/.test(hostname)
      || /^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.dynamics\.com$/.test(hostname);
  } catch {
    return false;
  }
}

// ── Business Central ──────────────────────────────────────────────────────────

/**
 * Returns true when `value` is a non-empty Business Central environment name.
 * BC environment names are alphanumeric with optional hyphens, 1–30 chars.
 */
export function isValidBCEnvironmentName(value: string): boolean {
  return /^[a-zA-Z0-9][a-zA-Z0-9-]{0,29}$/.test(value.trim());
}

// ── SQL / database ────────────────────────────────────────────────────────────

/**
 * Returns true when `value` contains the minimum tokens expected in an ODBC
 * or ADO.NET SQL Server connection string.
 *
 * Does a minimal check — does not attempt an actual connection.
 */
export function isValidSqlConnectionString(value: string): boolean {
  if (!isNonEmpty(value)) return false;
  const lower = value.toLowerCase();
  return (
    (lower.includes("server=") || lower.includes("data source=")) &&
    (lower.includes("database=") || lower.includes("initial catalog="))
  );
}

/**
 * Returns true when `value` is a valid SQL Server table name or schema.table.
 * Allows alphanumeric characters, underscores, and dots (for schema prefix).
 */
export function isValidSqlTableName(value: string): boolean {
  return /^[a-zA-Z_][a-zA-Z0-9_.]*$/.test(value.trim());
}
