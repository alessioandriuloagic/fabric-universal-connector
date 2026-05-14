---
applyTo: "frontend/**"
---

# Frontend Instructions — React + Fluent UI v9

## Stack
React 18, TypeScript strict, Fluent UI v9 (`@fluentui/react-components`), Vite,
Workload Client SDK (`@microsoft/fabric-workload-client`)

## Absolute Rules
- Never use HTML `<form>` tags. Use `<div>` with button `onClick` handlers.
- Never use `localStorage` or `sessionStorage`. The iFrame sandbox blocks them.
- Never call `fetch()` or `axios` directly from components. Use `useBackendApi` hook only.
- Never call `window.parent.postMessage` directly. Use the Workload Client SDK via `useFabricHost` hook.
- Never import from another wizard step's folder. Steps are isolated components.

## Component Structure
Every component folder contains: `index.tsx`, `{Name}.tsx`, `{Name}.types.ts`, `use{Name}.ts` (hook).
Keep rendering and logic separated — component file renders, hook file manages state and async calls.

## Fluent UI Patterns
Use `Field` wrapper for all form inputs — it handles label, required indicator, and validation message.
Use `Spinner` inside buttons during loading states, not separate loading overlays.
Use `MessageBar` for success/error feedback after async operations.
```tsx
// CORRECT
<Field label="Client ID" required validationMessage={errors.clientId}>
  <Input value={clientId} onChange={(_, d) => setClientId(d.value)} />
</Field>
<Button appearance="primary" onClick={handleSave} disabled={isSaving}>
  {isSaving ? <Spinner size="tiny" label="Saving..." /> : "Save & Start Sync"}
</Button>

// Success/error feedback
{saveResult === "success" && (
  <MessageBar intent="success">Connector saved. Initial sync starting...</MessageBar>
)}
```

## Async State Pattern
Every async operation needs three states: loading, success, error. No exceptions.
```tsx
const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
const [errorMessage, setErrorMessage] = useState<string>("");

const handleTestConnection = async () => {
  setStatus("loading");
  try {
    await api.testConnection(config);
    setStatus("success");
  } catch (err) {
    setStatus("error");
    setErrorMessage(err instanceof Error ? err.message : "Connection failed");
  }
};
```

## TypeScript
Enable strict mode. No `any` types — use `unknown` and narrow with type guards.
API response types are defined in `src/types/api.ts` — always use them, never inline interface definitions.
