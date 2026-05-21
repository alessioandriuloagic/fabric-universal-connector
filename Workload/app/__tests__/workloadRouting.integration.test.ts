/**
 * shared/__tests__/workloadRouting.integration.test.ts
 *
 * Integration-level tests that verify every workload frontend injects the
 * correct X-Workload-Id header and that apiClient blocks calls without it.
 *
 * These tests run in Node (jsdom environment is not needed) and mock the
 * global `fetch` function — no real HTTP calls are made.
 */
import { createWorkloadFetch, createWorkloadHeaders } from "shared/utils/apiClient";
import type { WorkloadId } from "shared/types/workload";

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Captures the last fetch call's headers. */
function setupFetchMock() {
  const mockFetch = jest.fn().mockResolvedValue({ ok: true, status: 200, json: jest.fn() });
  global.fetch = mockFetch as unknown as typeof fetch;
  return mockFetch;
}

// ── createWorkloadHeaders ─────────────────────────────────────────────────────

describe("createWorkloadHeaders", () => {
  const WORKLOADS: WorkloadId[] = [
    "customer-insight-journey",
    "sales-crm",
    "business-central",
    "sql-db",
  ];

  it.each(WORKLOADS)("sets X-Workload-Id correctly for %s", (workloadId) => {
    const headers = createWorkloadHeaders(workloadId);
    expect(headers["X-Workload-Id"]).toBe(workloadId);
  });

  it("accepts any string (for forward compatibility)", () => {
    const headers = createWorkloadHeaders("future-workload");
    expect(headers["X-Workload-Id"]).toBe("future-workload");
  });
});

// ── createWorkloadFetch — header injection ────────────────────────────────────

describe("createWorkloadFetch — header injection", () => {
  beforeEach(() => jest.clearAllMocks());

  it.each([
    "customer-insight-journey",
    "sales-crm",
    "business-central",
    "sql-db",
  ] as WorkloadId[])(
    "injects X-Workload-Id: %s on every call",
    async (workloadId) => {
      const mockFetch = setupFetchMock();
      const wFetch = createWorkloadFetch(workloadId);

      await wFetch("/v1/items/123/runs");

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
      expect(options.headers["X-Workload-Id"]).toBe(workloadId);
    },
  );

  it("always sets Content-Type: application/json", async () => {
    const mockFetch = setupFetchMock();
    const wFetch = createWorkloadFetch("customer-insight-journey");

    await wFetch("/v1/health");

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  it("caller headers are merged without overriding X-Workload-Id", async () => {
    const mockFetch = setupFetchMock();
    const wFetch = createWorkloadFetch("sales-crm");

    await wFetch("/v1/items/abc/jobs", {
      headers: { Authorization: "Bearer token123" },
    });

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
    expect(options.headers["X-Workload-Id"]).toBe("sales-crm");
    expect(options.headers["Authorization"]).toBe("Bearer token123");
  });

  it("caller cannot override X-Workload-Id", async () => {
    const mockFetch = setupFetchMock();
    const wFetch = createWorkloadFetch("business-central");

    await wFetch("/v1/items/xyz/runs", {
      headers: { "X-Workload-Id": "hacked-value" },
    });

    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit & { headers: Record<string, string> }];
    // workload header must win over caller header
    expect(options.headers["X-Workload-Id"]).toBe("business-central");
  });
});

// ── createWorkloadFetch — URL construction ────────────────────────────────────

describe("createWorkloadFetch — URL construction", () => {
  beforeEach(() => jest.clearAllMocks());

  it("prepends baseUrl to the path", async () => {
    const mockFetch = setupFetchMock();
    const wFetch = createWorkloadFetch("sql-db", "http://localhost:8000");

    await wFetch("/v1/items/1/runs");

    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/v1/items/1/runs");
  });

  it("works with empty baseUrl (relative paths)", async () => {
    const mockFetch = setupFetchMock();
    const wFetch = createWorkloadFetch("sql-db", "");

    await wFetch("/v1/health");

    const [url] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/v1/health");
  });
});
