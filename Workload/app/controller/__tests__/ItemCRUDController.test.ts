/**
 * app/controller/__tests__/ItemCRUDController.test.ts
 *
 * Unit tests for ItemCRUDController.
 * All WorkloadClientAPI calls are mocked so no Fabric SDK is required.
 */
import {
  callGetItem,
  saveItemDefinition,
} from "../ItemCRUDController";

// ── Mock WorkloadClientAPI ────────────────────────────────────────────────────

function makeClient(overrides: Record<string, unknown> = {}) {
  return {
    itemCrud: {
      getItem: jest.fn().mockResolvedValue({ id: "item-123", displayName: "Test Item" }),
      updateItemDefinition: jest.fn().mockResolvedValue({ success: true }),
      getItemDefinition: jest.fn().mockResolvedValue({
        definition: { parts: [] },
      }),
      ...overrides,
    },
  } as unknown as import("@ms-fabric/workload-client").WorkloadClientAPI;
}

// ── callGetItem ───────────────────────────────────────────────────────────────

describe("callGetItem", () => {
  it("returns the item when the SDK call succeeds", async () => {
    const client = makeClient();
    const result = await callGetItem(client, "item-123");
    expect(result).toMatchObject({ id: "item-123" });
    expect(client.itemCrud.getItem).toHaveBeenCalledWith({ itemId: "item-123" });
  });

  it("returns undefined (not throws) when the SDK call fails", async () => {
    const client = makeClient({
      getItem: jest.fn().mockRejectedValue(new Error("404 Not Found")),
    });
    const result = await callGetItem(client, "missing-id");
    expect(result).toBeUndefined();
  });

  it("passes the correct itemId to the SDK", async () => {
    const client = makeClient();
    await callGetItem(client, "abc-999");
    expect(client.itemCrud.getItem).toHaveBeenCalledTimes(1);
    expect(client.itemCrud.getItem).toHaveBeenCalledWith({ itemId: "abc-999" });
  });
});

// ── saveItemDefinition ────────────────────────────────────────────────────────

describe("saveItemDefinition", () => {
  it("calls updateItemDefinition with a properly shaped payload", async () => {
    const client = makeClient();
    const definition = { connectorType: "crm", version: 2 };

    await saveItemDefinition(client, "item-456", definition);

    expect(client.itemCrud.updateItemDefinition).toHaveBeenCalledTimes(1);
    const [callArgs] = (client.itemCrud.updateItemDefinition as jest.Mock).mock.calls;
    expect(callArgs[0]).toMatchObject({
      itemId: "item-456",
      updateMetadata: false,
    });
  });

  it("returns the SDK result on success", async () => {
    const client = makeClient({
      updateItemDefinition: jest.fn().mockResolvedValue({ success: true }),
    });
    const result = await saveItemDefinition(client, "item-456", { v: 1 });
    expect(result).toEqual({ success: true });
  });

  it("returns undefined (not throws) when the SDK call fails", async () => {
    const client = makeClient({
      updateItemDefinition: jest.fn().mockRejectedValue(new Error("403 Forbidden")),
    });
    const result = await saveItemDefinition(client, "item-456", { v: 1 });
    expect(result).toBeUndefined();
  });

  it("serialises the definition payload as base64 JSON in the part", async () => {
    const client = makeClient();
    const definition = { key: "value" };

    await saveItemDefinition(client, "item-789", definition);

    const [callArgs] = (client.itemCrud.updateItemDefinition as jest.Mock).mock.calls;
    const parts: unknown[] = callArgs[0].payload.definition.parts;
    expect(parts).toHaveLength(1);

    // The part payload should be a base64-encoded JSON string
    const part = parts[0] as { payload: string };
    const decoded = JSON.parse(atob(part.payload));
    expect(decoded).toEqual(definition);
  });
});
