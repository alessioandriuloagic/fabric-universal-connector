import React from "react";
import { PageProps } from "../../../App";
import {
  Ribbon,
  RibbonAction,
  createSettingsAction,
} from "../../../components/ItemEditor";
import { ViewContext } from "../../../components/ItemEditor";
import { ConnectorState } from "../ConnectorItemDefinition";
import { VIEWS } from "../ConnectorItemEditor";
import {
  createRunNowAction,
  createPauseAction,
  createReconfigureAction,
} from "./ribbonActionFactory";

export interface ConnectorItemRibbonProps extends PageProps {
  viewContext: ViewContext;
  connectorState: ConnectorState;
  isRunning: boolean;
  isSchedulePaused: boolean;
  onRunNow: () => Promise<void>;
  onPauseToggle: () => Promise<void>;
  onReconfigure: () => void;
  onOpenSettings: () => Promise<void>;
}

export function ConnectorItemRibbon({
  viewContext,
  connectorState,
  isRunning,
  isSchedulePaused,
  onRunNow,
  onPauseToggle,
  onReconfigure,
  onOpenSettings,
}: ConnectorItemRibbonProps) {
  const { currentView } = viewContext;
  const isDashboard = currentView === VIEWS.DASHBOARD;

  const homeActions: RibbonAction[] = isDashboard
    ? [
        createRunNowAction(onRunNow, isRunning),
        createPauseAction(onPauseToggle, isSchedulePaused),
        createReconfigureAction(onReconfigure),
        createSettingsAction(onOpenSettings),
      ]
    : [createSettingsAction(onOpenSettings)];

  return (
    <Ribbon
      homeToolbarActions={homeActions}
      additionalToolbars={[]}
      rightActionButtons={[]}
      viewContext={viewContext}
    />
  );
}
