import React, { useState } from 'react';
import { Label, Input, Button } from '@fluentui/react-components';

// TableMapping component
// - Simple UI to allow user to map source entity names to target table names
// - For now stores a comma-separated list of mappings in the form "source:target"
//   e.g. "ItemLedgerEntries:Items, Customer:Customers"

export const TableMapping: React.FC<{ onChange?: (mappings: Record<string,string>) => void }> = ({ onChange }) => {
  const [mappingsText, setMappingsText] = useState('');

  const parseMappings = () => {
    const map: Record<string,string> = {};
    mappingsText.split(',').map(s => s.trim()).filter(Boolean).forEach(pair => {
      const [src, dst] = pair.split(':').map(p=>p.trim());
      if (src) map[src] = dst || src;
    });
    return map;
  };

  const handleBlur = () => {
    const map = parseMappings();
    onChange && onChange(map);
  };

  return (
    <div style={{ padding: 16 }}>
      <h3>Table Mapping</h3>
      <Label>Mappings (source:target, comma separated)</Label>
      <Input placeholder="ItemLedgerEntries:Items, Customer:Customers" value={mappingsText} onChange={(_, ev) => setMappingsText(ev?.value || '')} onBlur={handleBlur} style={{ width: '100%' }} />
      <div style={{ marginTop: 12 }}>
        <Button onClick={() => { onChange && onChange(parseMappings()); }}>Apply</Button>
      </div>
    </div>
  );
};

export default TableMapping;