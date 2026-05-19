import { DatahubCompactViewConfig, DatahubCompactViewPageConfig, DatahubHeaderDialogConfig, DatahubSelectorDialogConfig, 
    DatahubSelectorDialogResult, 
    DatahubWizardDialogConfig, 
    DatahubWizardDialogResult, 
    ExtendedItemTypeV2, 
    OnelakeExplorerConfig, 
    OneLakeExplorerPageConfig, 
    OnelakeExplorerType, 
    WorkloadClientAPI } from "@ms-fabric/workload-client";
import { Item } from "../clients/FabricPlatformTypes";

export interface ItemAndPath extends Item {
    selectedPath: string;
}

export async function callDatahubWizardOpen(
    workloadClient: WorkloadClientAPI,
    supportedTypes: ExtendedItemTypeV2[],
    dialogSubmittButtonName: string,
    dialogDescription: string,
    multiSelectionEnabled: boolean = false,
    showFilesFolder: boolean = true,
    workspaceNavigationEnabled: boolean = true): Promise<ItemAndPath | null> {

   const datahubWizardConfig: DatahubWizardDialogConfig = {
        datahubCompactViewPageConfig: {
            datahubCompactViewConfig: {
                supportedTypes: supportedTypes,
                multiSelectionEnabled: multiSelectionEnabled,
                workspaceNavigationEnabled: workspaceNavigationEnabled,
                hostDetails: {
                    experience: 'sample experience 3rd party',
                    scenario: 'sample scenario 3rd party',
                }
            } as DatahubCompactViewConfig
        } as DatahubCompactViewPageConfig,
        oneLakeExplorerPageConfig: {
            headerDialogConfig: {
                dialogTitle: 'Select Item',
                dialogDescription: dialogDescription,
            } as DatahubHeaderDialogConfig,
            onelakeExplorerConfig: {
                onelakeExplorerTypes: Object.values(OnelakeExplorerType),
                showFilesFolder: showFilesFolder,
            } as OnelakeExplorerConfig,
        } as OneLakeExplorerPageConfig,
        submitButtonName: dialogSubmittButtonName,
    }

    const result: DatahubWizardDialogResult = await workloadClient.datahub.openDatahubWizardDialog(datahubWizardConfig);
    if (!result.onelakeExplorerResult) {
        return null;
    }

    const selectedItem = result.onelakeExplorerResult;
    const { itemObjectId, workspaceObjectId } = selectedItem;
    // itemType is not yet available on the OneLake Explorer result — tracked in Fabric WDK backlog.
    // Using empty string as a safe placeholder; update once the SDK exposes it.
    return {
        id: itemObjectId,
        workspaceId: workspaceObjectId,
        type: "",
        displayName: "",
        description: "",
        selectedPath: selectedItem.selectedPath.split('/').slice(2).join('/'),
    };
}


export async function callDatahubOpen(
    workloadClient: WorkloadClientAPI,
    supportedTypes: ExtendedItemTypeV2[],
    dialogDescription: string,
    multiSelectionEnabled: boolean,
    workspaceNavigationEnabled: boolean = true): Promise<Item | null> {

    const datahubConfig: DatahubSelectorDialogConfig = {
        supportedTypes: supportedTypes,
        multiSelectionEnabled: multiSelectionEnabled,
        dialogDescription: dialogDescription,
        workspaceNavigationEnabled: workspaceNavigationEnabled,
        // required to be non-empty for SDK validation; not surfaced to the user
        hostDetails: {
            experience: 'sample experience 3rd party',
            scenario: 'sample scenario 3rd party',
        }
    };

    const result: DatahubSelectorDialogResult = await workloadClient.datahub.openDialog(datahubConfig);
    if (!result.selectedDatahubItem) {
        return null;
    }

    const selectedItem = result.selectedDatahubItem[0];
    const { itemObjectId, workspaceObjectId } = selectedItem;
    const { displayName, description } = selectedItem.datahubItemUI;
    return {
        id: itemObjectId,
        workspaceId: workspaceObjectId,
        type: selectedItem.datahubItemUI.itemType,
        displayName,
        description,
    };
}