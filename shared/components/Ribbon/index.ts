/**
 * shared/components/Ribbon/index.ts
 *
 * Re-exports all Ribbon and Toolbar-related components and factory functions
 * from the canonical Workload implementation.
 *
 * Usage in workload code:
 *   import { Ribbon, createSaveAction, createSettingsAction } from "shared/components/Ribbon";
 *
 * This provides a stable import path decoupled from the physical file location.
 * Future: when Ribbon is published as a standalone shared package, only this
 * barrel needs to change — consumers are unaffected.
 */

// Ribbon container (tabs + toolbar)
export { Ribbon } from "../../../Workload/app/components/ItemEditor/Ribbon";
export type {
  RibbonProps,
  RibbonTab,
} from "../../../Workload/app/components/ItemEditor/Ribbon";

// Toolbar (renders the action buttons inside a ribbon tab)
export { RibbonToolbar } from "../../../Workload/app/components/ItemEditor/RibbonToolbar";
export type {
  RibbonToolbarProps,
  RibbonAction,
  RibbonDropdownAction,
  RibbonActionType,
} from "../../../Workload/app/components/ItemEditor/RibbonToolbar";

// Individual toolbar action (button + tooltip wrapper)
export { RibbonToolbarAction } from "../../../Workload/app/components/ItemEditor/RibbonToolbarAction";
export type {
  RibbonToolbarActionProps,
  FluentIconComponent,
} from "../../../Workload/app/components/ItemEditor/RibbonToolbarAction";

// Action button implementation (supports regular + dropdown variants)
export { RibbonActionButtonImpl } from "../../../Workload/app/components/ItemEditor/RibbonActionButton";
export type {
  RibbonActionButtonImplProps,
  RibbonActionButton,
  DropdownMenuItem,
} from "../../../Workload/app/components/ItemEditor/RibbonActionButton";

// Standard action factories — ready-made Save, Settings, About actions
export {
  createSaveAction,
  createSettingsAction,
  createAboutAction,
} from "../../../Workload/app/components/ItemEditor/RibbonStandardActions";
