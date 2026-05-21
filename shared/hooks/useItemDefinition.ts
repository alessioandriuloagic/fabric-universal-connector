/**
 * shared/hooks/useItemDefinition.ts
 *
 * Generic state management hook for Fabric item definitions.
 *
 * Wraps React `useState` with a stable typed setter that accepts either a
 * new value directly or an updater function (same API as `useState`).
 *
 * Usage:
 *   const [definition, setDefinition] = useItemDefinition<MyItemDef>(initialDef);
 *
 *   // Direct set
 *   setDefinition({ ...definition, name: "New name" });
 *
 *   // Functional update (safe with stale closures)
 *   setDefinition(prev => ({ ...prev, enabled: !prev.enabled }));
 *
 * Why a custom hook instead of plain useState?
 *   - Stable API that can be extended later (e.g., dirty-tracking, undo/redo)
 *   - Consistent import path across all workloads (shared/hooks)
 *   - Makes testing easier — mock `useItemDefinition` at the shared layer
 */
import { useState, useCallback } from "react";

export type ItemDefinitionSetter<T> = (
  value: T | ((prev: T) => T),
) => void;

/**
 * Manages the local state of a Fabric item definition.
 *
 * @param initialValue - The initial definition value (may be undefined for
 *   items that haven't loaded yet).
 * @returns A tuple of [current definition, setter function].
 */
export function useItemDefinition<T>(
  initialValue: T,
): [T, ItemDefinitionSetter<T>] {
  const [definition, setDefinition] = useState<T>(initialValue);

  const updateDefinition = useCallback<ItemDefinitionSetter<T>>(
    (valueOrUpdater) => {
      setDefinition(valueOrUpdater);
    },
    [],
  );

  return [definition, updateDefinition];
}
