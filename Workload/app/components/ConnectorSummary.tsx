import React from 'react';
import { Label } from '@fluentui/react-components';

export const ConnectorSummary: React.FC<{ summary: any }> = ({ summary }) => {
  return (
    <div style={{ padding: 16 }}>
      <h3>Connector Summary</h3>
      <pre style={{ background: '#f4f4f4', padding: 12 }}>{JSON.stringify(summary, null, 2)}</pre>
      <Label>Use this summary to validate what will be saved to the workload item.</Label>
    </div>
  );
};

export default ConnectorSummary;