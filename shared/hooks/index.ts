/**
 * shared/hooks/index.ts
 *
 * Barrel export for all shared React hooks.
 *
 * Import hooks from this path:
 *   import { useWorkload, useItemDefinition, useNotification } from "shared/hooks";
 */

export { useWorkload, getWorkloadConfig } from "./useWorkload";

export { useItemDefinition } from "./useItemDefinition";
export type { ItemDefinitionSetter } from "./useItemDefinition";

export { useNotification } from "./useNotification";
export type {
  NotificationType,
  NotificationMessage,
  UseNotificationReturn,
} from "./useNotification";
