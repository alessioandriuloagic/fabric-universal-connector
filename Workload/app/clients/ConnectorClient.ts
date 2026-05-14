/* ConnectorClient
 * Lightweight client used by frontend components to call backend connector APIs.
 * This module intentionally uses the browser Fetch API to call the backend routes
 * exposed by the workload dev gateway (relative URLs). Calls are JSON-based.
 *
 * Methods:
 * - testConnection(body)
 * - discoverEntities(body)
 * - subscribe(body)
 */

export async function _postJson(path: string, body: any) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: 'same-origin'
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

export async function testConnection(body: any) {
  return _postJson("/workload/connectors/test-connection", body);
}

export async function discoverEntities(body: any) {
  return _postJson("/workload/connectors/discover-entities", body);
}

export async function subscribe(body: any) {
  return _postJson("/workload/connectors/subscribe", body);
}

// Create a workload item (saves config and secrets via backend API)
export async function createItem(body: any) {
  return _postJson("/workload/item/create", body);
}