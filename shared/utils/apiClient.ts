/**
 * shared/utils/apiClient.ts
 *
 * Workload-aware HTTP client factory.
 *
 * Single injection point for the X-Workload-Id header on all direct backend
 * calls.  Each workload frontend must use `createWorkloadFetch()` (or
 * `createWorkloadHeaders()`) instead of calling `fetch()` directly.
 *
 * The backend reads X-Workload-Id to:
 *   1. Scope entity ingestion to the workload's allowed entity set
 *   2. Route job execution to the correct workload configuration
 *
 * Usage:
 *   const backendFetch = createWorkloadFetch("customer-insight-journey");
 *   const res = await backendFetch("/v1/items/123/runs");
 */
import type { WorkloadId } from "../types/workload";

// ── Header factory ────────────────────────────────────────────────────────────

/**
 * Returns a headers object containing the X-Workload-Id header.
 * Use when you need to merge workload headers into an existing headers map.
 */
export function createWorkloadHeaders(workloadId: WorkloadId | string): Record<string, string> {
  return { "X-Workload-Id": workloadId };
}

// ── Fetch wrapper ─────────────────────────────────────────────────────────────

export interface WorkloadFetchOptions extends RequestInit {
  /** Additional headers merged with the workload header. */
  headers?: Record<string, string>;
}

/**
 * Creates a `fetch`-compatible function that automatically injects the
 * X-Workload-Id header on every call.
 *
 * @param workloadId - The workload identity to inject.
 * @param baseUrl    - Optional base URL prepended to every path (e.g. "http://localhost:8000").
 *
 * @example
 * const backendFetch = createWorkloadFetch("customer-insight-journey", BACKEND_URL);
 * const res = await backendFetch("/v1/items/abc123/runs");
 * const runs = await res.json();
 */
export function createWorkloadFetch(
  workloadId: WorkloadId | string,
  baseUrl = "",
): (path: string, options?: WorkloadFetchOptions) => Promise<Response> {
  const workloadHeaders = createWorkloadHeaders(workloadId);

  return (path: string, options: WorkloadFetchOptions = {}): Promise<Response> => {
    const { headers: callerHeaders = {}, ...rest } = options;
    return fetch(`${baseUrl}${path}`, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...callerHeaders,
        // workloadHeaders always wins — X-Workload-Id is not caller-overrideable
        ...workloadHeaders,
      },
    });
  };
}

