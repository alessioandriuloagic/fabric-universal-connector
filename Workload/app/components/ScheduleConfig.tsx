import React, { useState } from 'react';
import { Label, Input, Select, Option, Button } from '@fluentui/react-components';

// ScheduleConfig component
// - Allows the user to choose sync mode and frequency

export const ScheduleConfig: React.FC<{ onChange?: (cfg:any) => void }> = ({ onChange }) => {
  const [mode, setMode] = useState<'webhook'|'poll'>('webhook');
  const [frequency, setFrequency] = useState<number>(60); // minutes
  const [error, setError] = useState<string | null>(null);
  const [showError, setShowError] = useState<boolean>(false);

  const apply = () => {
    if (mode === 'poll' && (!frequency || frequency <= 0)) {
      setError('Frequency must be a positive number');
      setShowError(true);
      return;
    }
    setError(null);
    setShowError(false);
    const cfg = { mode, frequency };
    onChange && onChange(cfg);
  };

  return (
    <div style={{ padding: 16 }}>
      <h3>Schedule & Sync</h3>
      <Label>Sync mode</Label>
      <Select value={mode} onChange={(_, d) => setMode(d.value as any)} style={{ minWidth: 240 }}>
        <Option value={'webhook'}>Webhook (push)</Option>
        <Option value={'poll'}>Polling (pull)</Option>
      </Select>

      <div style={{ marginTop: 12 }}>
        <Label>Frequency (minutes) — used for polling</Label>
        <Input type="number" value={String(frequency)} onChange={(_, ev) => setFrequency(Number(ev?.value || 60))} />
      </div>

      {showError && error && (
        <div style={{ marginTop: 12, padding: 8, backgroundColor: '#fde7e7', color: '#c50f1f', borderRadius: 4 }}>
          {error}
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <Button onClick={apply}>Apply</Button>
      </div>
    </div>
  );
};

export default ScheduleConfig;