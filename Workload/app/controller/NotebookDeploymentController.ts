import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { ModuleType } from "../items/ConnectorItem/ConnectorItemDefinition";

export const CURRENT_WHEEL_VERSION = "1.0.0";

export interface NotebookDeploymentResult {
  notebookItemId: string;
  deployedAt: string;
  wheelVersion: string;
}

export async function deployConnectorNotebook(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  connectorItemId: string,
  moduleType: ModuleType
): Promise<NotebookDeploymentResult> {
  // Phase 1 placeholder — actual implementation in Phase 5
  // Will: 1) fetch notebook template content from /assets/notebooks/
  //        2) replace %%CONNECTOR_ITEM_ID%%, %%WORKSPACE_ID%%, %%WHEEL_VERSION%%
  //        3) POST to Fabric Items API to create Notebook item
  //        4) return the created notebook's item ID
  throw new Error("NotebookDeploymentController: not yet implemented — Phase 5 target");
}

export function buildNotebookDisplayName(moduleType: ModuleType, connectorItemId: string): string {
  const prefix = {
    crm: "FUC-CRM-Runtime",
    businesscentral: "FUC-BC-Runtime",
    sql: "FUC-SQL-Runtime",
  }[moduleType];
  return `${prefix}-${connectorItemId}`;
}
