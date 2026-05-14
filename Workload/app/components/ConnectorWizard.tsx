import React, { useState } from 'react';
import SourceConfig from './SourceConfig';
import TableMapping from './TableMapping';
import ScheduleConfig from './ScheduleConfig';
import SyncMonitor from './SyncMonitor';
import { createItem } from '../clients/ConnectorClient';
import { Button, Label } from '@fluentui/react-components';
import { WorkloadClientAPI } from '@microsoft/fabric-workload-client';

interface ConnectorWizardProps {
  workloadClient?: WorkloadClientAPI;
}

// ConnectorWizard: multi-step flow that collects configuration and saves an item
export const ConnectorWizard: React.FC<ConnectorWizardProps> = ({ workloadClient }) => {
  const [step, setStep] = useState<number>(1);
  const [sourceConfig, setSourceConfig] = useState<any>({});
  const [tableMapping, setTableMapping] = useState<any>({});
  const [schedule, setSchedule] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const onSourceConfigReady = (config: any) => {
    setSourceConfig(config);
  };

  const onSave = async () => {
    // Basic validation
    if (!sourceConfig || !sourceConfig.source) {
      setMessage('Source configuration is required');
      return;
    }
    setSaving(true);
    setMessage(null);
    const payload = {
      config: {
        source: sourceConfig.source,
        base_url: sourceConfig.config?.base_url,
        company_id: sourceConfig.config?.company_id,
        entities: sourceConfig.config?.entities,
        table_mapping: tableMapping,
        schedule: schedule,
      },
      secrets: sourceConfig.secrets
    };

    try {
      const res = await createItem(payload);
      setMessage(`Saved item: ${res.itemId}`);
    } catch (err: any) {
      setMessage(err?.message || String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h2>Connector Wizard</h2>

      {step === 1 && (
        <div>
          <SourceConfig workloadClient={workloadClient} onConfigReady={onSourceConfigReady} />
          <div style={{ marginTop: 12 }}>
            <Button onClick={() => setStep(2)} appearance="primary">Next: Table Mapping</Button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div>
          <TableMapping onChange={setTableMapping} />
          <div style={{ marginTop: 12 }}>
            <Button onClick={() => setStep(1)}>Back</Button>
            <Button onClick={() => setStep(3)} appearance="primary" style={{ marginLeft: 8 }}>Next: Schedule</Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div>
          <ScheduleConfig onChange={setSchedule} />
          <div style={{ marginTop: 12 }}>
            <Button onClick={() => setStep(2)}>Back</Button>
            <Button onClick={() => setStep(4)} appearance="primary" style={{ marginLeft: 8 }}>Next: Review</Button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div>
          <h3>Review</h3>
          <pre style={{ background: '#f4f4f4', padding: 12 }}>{JSON.stringify({ sourceConfig, tableMapping, schedule }, null, 2)}</pre>
          <div style={{ marginTop: 12 }}>
            <Button onClick={() => setStep(3)}>Back</Button>
            <Button onClick={onSave} appearance="primary" disabled={saving} style={{ marginLeft: 8 }}>{saving ? 'Saving...' : 'Save configuration'}</Button>
          </div>
        </div>
      )}

      {message && (
        <div style={{ marginTop: 12 }}>
          <Label>Message</Label>
          <div>{message}</div>
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <h4>Sync Monitor</h4>
        <SyncMonitor />
      </div>
    </div>
  );
};

export default ConnectorWizard;