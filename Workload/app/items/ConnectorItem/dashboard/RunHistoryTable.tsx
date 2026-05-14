import React from "react";
import { useTranslation } from "react-i18next";
import {
  DataGrid,
  DataGridHeader,
  DataGridHeaderCell,
  DataGridBody,
  DataGridRow,
  DataGridCell,
  TableColumnDefinition,
  createTableColumn,
  TableCellLayout,
  Badge,
} from "@fluentui/react-components";
import { ConnectorRun, ConnectorRunStatus } from "../ConnectorItemDefinition";

interface RunHistoryTableProps {
  runs: ConnectorRun[];
  onRunClick: (runId: string) => void;
}

function statusBadgeColor(status: ConnectorRunStatus) {
  switch (status) {
    case "success":         return "success";
    case "partial_success": return "warning";
    case "failed":          return "danger";
    case "running":         return "informative";
    default:                return "subtle";
  }
}

export function RunHistoryTable({ runs, onRunClick }: RunHistoryTableProps) {
  const { t } = useTranslation();

  const columns: TableColumnDefinition<ConnectorRun>[] = [
    createTableColumn<ConnectorRun>({
      columnId: "status",
      renderHeaderCell: () => t("RunHistory_Status", "Status"),
      renderCell: (run) => (
        <TableCellLayout>
          <Badge color={statusBadgeColor(run.status) as any} appearance="filled">
            {run.status}
          </Badge>
        </TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "startTime",
      renderHeaderCell: () => t("RunHistory_Started", "Started"),
      renderCell: (run) => (
        <TableCellLayout>
          {new Date(run.runStartUtc).toLocaleString()}
        </TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "duration",
      renderHeaderCell: () => t("RunHistory_Duration", "Duration"),
      renderCell: (run) => (
        <TableCellLayout>
          {run.durationSeconds != null ? `${run.durationSeconds}s` : "—"}
        </TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "records",
      renderHeaderCell: () => t("RunHistory_Records", "Records"),
      renderCell: (run) => (
        <TableCellLayout>{run.recordsIngested.toLocaleString()}</TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "triggeredBy",
      renderHeaderCell: () => t("RunHistory_TriggeredBy", "Triggered By"),
      renderCell: (run) => <TableCellLayout>{run.triggeredBy}</TableCellLayout>,
    }),
  ];

  return (
    <DataGrid
      items={runs}
      columns={columns}
      getRowId={(run) => run.runId}
      onSelectionChange={(_, data) => {
        const selected = Array.from(data.selectedItems)[0];
        if (selected) onRunClick(String(selected));
      }}
      className="run-history-table"
    >
      <DataGridHeader>
        <DataGridRow>
          {({ renderHeaderCell }) => (
            <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>
          )}
        </DataGridRow>
      </DataGridHeader>
      <DataGridBody<ConnectorRun>>
        {({ item, rowId }) => (
          <DataGridRow<ConnectorRun> key={rowId} style={{ cursor: "pointer" }}>
            {({ renderCell }) => <DataGridCell>{renderCell(item)}</DataGridCell>}
          </DataGridRow>
        )}
      </DataGridBody>
    </DataGrid>
  );
}
