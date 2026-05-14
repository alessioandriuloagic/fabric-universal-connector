import React from "react";
import { useTranslation } from "react-i18next";
import { Field, Input, Radio, RadioGroup, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardScheduleStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { schedule } = wizardState;
  const update = (patch: Partial<typeof schedule>) => onUpdate({ schedule: { ...schedule, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Schedule_Title", "Configure ingestion schedule")}
      </Text>

      <RadioGroup
        value={schedule.scheduleType ?? "cron"}
        onChange={(_, d) => update({ scheduleType: d.value as any })}
      >
        <Radio value="cron" label={t("Wizard_Schedule_Cron", "Cron expression")} />
        <Radio value="interval" label={t("Wizard_Schedule_Interval", "Fixed interval")} />
      </RadioGroup>

      {schedule.scheduleType === "cron" && (
        <Field label={t("Wizard_Schedule_CronExpr", "Cron Expression")}
               hint={t("Wizard_Schedule_CronHint", "e.g. 0 2 * * * (daily at 02:00 UTC)")}
               validationMessage={validationErrors.cronExpression} required>
          <Input
            value={schedule.cronExpression ?? "0 2 * * *"}
            onChange={(_, d) => update({ cronExpression: d.value })}
          />
        </Field>
      )}

      {schedule.scheduleType === "interval" && (
        <Field label={t("Wizard_Schedule_IntervalMinutes", "Interval (minutes)")}
               hint={t("Wizard_Schedule_IntervalHint", "Minimum 15 minutes")}
               validationMessage={validationErrors.intervalMinutes} required>
          <Input
            type="number"
            value={String(schedule.intervalMinutes ?? 60)}
            onChange={(_, d) => update({ intervalMinutes: parseInt(d.value, 10) })}
          />
        </Field>
      )}

      <Field label={t("Wizard_Schedule_Timezone", "Timezone")}>
        <Input
          value={schedule.timezone ?? "UTC"}
          onChange={(_, d) => update({ timezone: d.value })}
        />
      </Field>
    </div>
  );
}
