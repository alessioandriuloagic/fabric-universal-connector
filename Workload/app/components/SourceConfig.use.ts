// Lightweight hook file for SourceConfig - kept for future logic split.
import { useState } from 'react';

export function useSourceConfigState() {
  const [source, setSource] = useState<string>('business_central');
  const [baseUrl, setBaseUrl] = useState<string>('');
  const [company, setCompany] = useState<string>('');
  const [entities, setEntities] = useState<string>('');
  const [secrets, setSecrets] = useState<string>('');

  return {
    source, setSource,
    baseUrl, setBaseUrl,
    company, setCompany,
    entities, setEntities,
    secrets, setSecrets,
  };
}
