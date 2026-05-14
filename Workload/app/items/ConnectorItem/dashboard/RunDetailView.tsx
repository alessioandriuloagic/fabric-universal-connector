import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Table, TableRow, TableCell, TableBody, TableHeader, TableHeaderCell } from "@fluentui/react-components";
import { ConnectorRun } from "../ConnectorItemDefinition";

interface RunDetailViewProps {
  runs: ConnectorRun[];
  runId: string | null;
}

export function RunDetailView({ runs, runId }: RunDetailViewProps) {
  const { t } = useTranslation();
  const run = runs.find((r) => r.runId === runId);

  if (!run) return <Text>{t("RunDetail_NotFound", "Run not found.")}</Text>;

  return (
    <div style={{ padding: 16 }}>
      <Text size={600} weight="semibold" block>
        {t("RunDetail_Title", "Run Details")} — {run.status}
      </Text>
      <Text block>{t("RunDetail_Started", "Started")}: {new Date(run.runStartUtc).toLocaleString()}</Text>
      {run.errorMessage && (
        <Text block style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {t("RunDetail_Error", "Error")}: {run.errorMessage}
        </Text>
      )}

      <Table style={{ marginTop: 16 }}>
        <TableHeader>
          <TableRow>
            <TableHeaderCell>{t("RunDetail_Entity", "Entity")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Status", "Status")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Records", "Records")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Duration", "Duration")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Error", "Error")}</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {run.entityResults.map((er) => (
            <TableRow key={er.entityName}>
              <TableCell>{er.entityName}</TableCell>
              <TableCell>{er.status}</TableCell>
              <TableCell>{er.recordsIngested.toLocaleString()}</TableCell>
              <TableCell>{er.durationSeconds}s</TableCell>
              <TableCell>{er.errorMessage ?? "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
