/**
 * shared/components/ItemEditor/index.ts
 *
 * Stable public interface for ItemEditor components, usable across all workload
 * frontends via `import { ... } from "shared/components/ItemEditor"`.
 *
 * Implementation note
 * -------------------
 * The actual React component source currently lives in
 *   Workload/app/components/ItemEditor/
 * This barrel re-exports everything from that location so new workloads can
 * import from the canonical `shared/` path without duplicating code.
 *
 * Future: when each workload gets its own standalone build, move the component
 * source into this directory and remove the re-export indirection.
 *
 * Build integration
 * -----------------
 * The Workload/ webpack build resolves `shared/*` via the alias
 *   `shared  →  <repo-root>/shared`
 * configured in Workload/webpack.config.js. Jest resolves it via
 * `moduleNameMapper` in Workload/jest.config.js.
 */

// Core ItemEditor component + types
export { ItemEditor } from "../../../Workload/app/components/ItemEditor/ItemEditor";
export type {
  ItemEditorProps,
  RegisteredView,
  RegisteredNotification,
  ViewContext,
} from "../../../Workload/app/components/ItemEditor/ItemEditor";

// Context objects
export {
  ViewNavigationContext,
  DetailViewActionsContext,
} from "../../../Workload/app/components/ItemEditor/ItemEditor";

// Default view (two-panel layout with optional left panel)
export {
  ItemEditorDefaultView,
  useViewNavigation,
} from "../../../Workload/app/components/ItemEditor/ItemEditorDefaultView";
export type {
  ItemEditorDefaultViewProps,
  LeftPanelConfig,
  CentralPanelConfig,
} from "../../../Workload/app/components/ItemEditor/ItemEditorDefaultView";

// Empty view (first-run / no-definition state)
export { ItemEditorEmptyView } from "../../../Workload/app/components/ItemEditor/ItemEditorEmptyView";
export type {
  ItemEditorEmptyViewProps,
  EmptyStateTask,
} from "../../../Workload/app/components/ItemEditor/ItemEditorEmptyView";

// Detail view (L2 drill-down with automatic back navigation)
export { ItemEditorDetailView } from "../../../Workload/app/components/ItemEditor/ItemEditorDetailView";
export type {
  ItemEditorDetailViewProps,
  DetailViewAction,
} from "../../../Workload/app/components/ItemEditor/ItemEditorDetailView";

// Ribbon components
export { Ribbon } from "../../../Workload/app/components/ItemEditor/Ribbon";
export type {
  RibbonProps,
  RibbonTab,
} from "../../../Workload/app/components/ItemEditor/Ribbon";

export { RibbonToolbar } from "../../../Workload/app/components/ItemEditor/RibbonToolbar";
export type {
  RibbonToolbarProps,
  RibbonAction,
  RibbonDropdownAction,
} from "../../../Workload/app/components/ItemEditor/RibbonToolbar";

export { RibbonToolbarAction } from "../../../Workload/app/components/ItemEditor/RibbonToolbarAction";
export type {
  RibbonToolbarActionProps,
  FluentIconComponent,
} from "../../../Workload/app/components/ItemEditor/RibbonToolbarAction";

export { RibbonActionButtonImpl } from "../../../Workload/app/components/ItemEditor/RibbonActionButton";
export type {
  RibbonActionButtonImplProps,
  RibbonActionButton,
  DropdownMenuItem,
} from "../../../Workload/app/components/ItemEditor/RibbonActionButton";

// Standard action factories
export {
  createSaveAction,
  createSettingsAction,
  createAboutAction,
} from "../../../Workload/app/components/ItemEditor/RibbonStandardActions";

// Re-exported for consumers that need the action type union
export type { RibbonActionType } from "../../../Workload/app/components/ItemEditor/RibbonStandardActions";
