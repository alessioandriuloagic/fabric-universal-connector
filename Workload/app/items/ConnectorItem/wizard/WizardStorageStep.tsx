import React from "react";
import { useTranslation } from "react-i18next";
import { Field, Input, Switch, Radio, RadioGroup, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardStorageStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { storage } = wizardState;
  const update = (patch: Partial<typeof storage>) => onUpdate({ storage: { ...storage, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Storage_Title", "Configure Bronze Lakehouse")}
      </Text>

      <Switch
        label={t("Wizard_Storage_UseExisting", "Use an existing Lakehouse")}
        checked={storage.useExistingLakehouse ?? false}
        onChange={(_, d) => update({ useExistingLakehouse: d.checked })}
      />

      <Field label={t("Wizard_Storage_LakehouseName", "Lakehouse Name")}
             validationMessage={validationErrors.bronzeLakeHouseName} required>
        <Input
          value={storage.bronzeLakeHouseName ?? "FabricUniversalConnector-Bronze"}
          onChange={(_, d) => update({ bronzeLakeHouseName: d.value })}
          disabled={storage.useExistingLakehouse}
        />
      </Field>

      <Field label={t("Wizard_Storage_SchemaPolicy", "Schema Evolution Policy")}>
        <RadioGroup
          value={storage.schemaEvolutionPolicy ?? "merge"}
          onChange={(_, d) => update({ schemaEvolutionPolicy: d.value as any })}
        >
          <Radio value="merge"
                 label={t("Wizard_Storage_Policy_Merge", "Merge (Recommended — adds new columns)")} />
          <Radio value="strict"
                 label={t("Wizard_Storage_Policy_Strict", "Strict (Fail on any schema change)")} />
        </RadioGroup>
      </Field>
    </div>
  );
}
