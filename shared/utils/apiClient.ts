/**
 * shared/utils/apiClient.ts
 *
 * Workload-aware header factory.
 * Each workload frontend passes its own workloadId at call time.
 * The X-Workload-Id header is read by the backend to scope entity ingestion.
 */

export function createWorkloadHeaders(workloadId: string): Record<string, string> {
  return { "X-Workload-Id": workloadId };
}
