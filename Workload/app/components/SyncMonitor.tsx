import React, { useEffect, useState } from 'react';
import { Label, Spinner } from '@fluentui/react-components';

// SyncMonitor component
// - Displays lightweight status of recent syncs. For dev it polls a local endpoint
//   or shows static placeholder data.

export const SyncMonitor: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [lastRun, setLastRun] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('Idle');

  useEffect(() => {
    // For now show a placeholder recent run timestamp
    setLoading(true);
    const t = setTimeout(() => {
      setLastRun(new Date().toISOString());
      setStatus('OK');
      setLoading(false);
    }, 500);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{ padding: 16 }}>
      <h3>Sync Monitor</h3>
      {loading ? <Spinner label="Loading sync status..." /> : (
        <div>
          <Label>Last run</Label>
          <div>{lastRun}</div>
          <Label>Status</Label>
          <div>{status}</div>
        </div>
      )}
    </div>
  );
};

export default SyncMonitor;