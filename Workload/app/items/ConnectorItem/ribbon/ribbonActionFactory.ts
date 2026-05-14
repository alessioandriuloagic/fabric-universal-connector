import {
  Play24Regular,
  Pause24Regular,
  Settings24Regular,
  ArrowReset24Regular,
} from "@fluentui/react-icons";
import { RibbonAction } from "../../../components/ItemEditor";

export function createRunNowAction(onClick: () => Promise<void>, disabled: boolean): RibbonAction {
  return {
    key: "run-now",
    icon: Play24Regular,
    label: "Run Now",
    onClick,
    testId: "ribbon-run-now-btn",
    tooltip: "Trigger an immediate ingestion run",
    disabled,
  };
}

export function createPauseAction(onClick: () => Promise<void>, isPaused: boolean): RibbonAction {
  return {
    key: "pause-schedule",
    icon: Pause24Regular,
    label: isPaused ? "Resume" : "Pause",
    onClick,
    testId: "ribbon-pause-btn",
    tooltip: isPaused ? "Resume scheduled runs" : "Pause scheduled runs",
  };
}

export function createReconfigureAction(onClick: () => void): RibbonAction {
  return {
    key: "reconfigure",
    icon: Settings24Regular,
    label: "Reconfigure",
    onClick: async () => onClick(),
    testId: "ribbon-reconfigure-btn",
    tooltip: "Edit connector configuration",
  };
}

export function createResetWatermarkAction(onClick: () => Promise<void>): RibbonAction {
  return {
    key: "reset-watermark",
    icon: ArrowReset24Regular,
    label: "Reset Watermark",
    onClick,
    testId: "ribbon-reset-watermark-btn",
    tooltip: "Reset the change-tracking watermark — next run will perform a full extract",
  };
}
