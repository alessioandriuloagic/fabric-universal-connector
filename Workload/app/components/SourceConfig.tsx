import React, { useState } from "react";
import { Input, Button, Label, Select, Option, Textarea, MessageBar, MessageBarBody, Spinner } from "@fluentui/react-components";
import { useTranslation } from 'react-i18next';
import { testConnection } from "../clients/ConnectorClient";
import { useFabricAuth } from "./useFabricAuth";
import { WorkloadClientAPI } from "@ms-fabric/workload-client";

interface SourceConfigProps {
  workloadClient?: WorkloadClientAPI;
  onConfigReady?: (config: any) => void;
}

// Component to collect source connection parameters from the user.
// Enhanced to obtain and pass user_assertion (OBO token) to the backend.
export const SourceConfig: React.FC<SourceConfigProps> = ({ workloadClient, onConfigReady }) => {
  const [source, setSource] = useState<string>("business_central");
  const [baseUrl, setBaseUrl] = useState<string>("");
  const [company, setCompany] = useState<string>("");
  const [entities, setEntities] = useState<string>("");
  const [secrets, setSecrets] = useState<string>("");
  const [testing, setTesting] = useState<boolean>(false);
  const [result, setResult] = useState<string>("");
  const [userToken, setUserToken] = useState<string | null>(null);
  const [obtainingToken, setObtainingToken] = useState<boolean>(false);

  const { t } = useTranslation();
  const { getUserToken, isLoading: tokenLoading, error: tokenError } = useFabricAuth(workloadClient);

  const parseSecrets = () => {
    try {
      if (!secrets || secrets.trim() === "") return undefined;
      const parsed = JSON.parse(secrets);
      // If we have a user token, add it as user_assertion for OBO flow
      if (userToken && parsed) {
        return { ...parsed, user_assertion: userToken };
      }
      return parsed;
    } catch (e) {
      setResult(`Invalid secrets JSON: ${e}`);
      return undefined;
    }
  };

  const handleObtainUserToken = async () => {
    setObtainingToken(true);
    try {
      const token = await getUserToken();
      setUserToken(token);
      setResult(t('Connector_UserTokenObtained', 'User token obtained successfully for delegated flow.'));
    } catch (err: any) {
      setResult(`Error obtaining user token: ${err?.message || String(err)}`);
      setUserToken(null);
    } finally {
      setObtainingToken(false);
    }
  };

  const clearUserToken = () => {
    setUserToken(null);
    setResult("");
  };

  const [errors, setErrors] = useState<{ baseUrl?: string; entities?: string }>({});

  const validate = () => {
    const e: any = {};
    if (!baseUrl || baseUrl.trim() === "") e.baseUrl = t('Connector_Validation_Required');
    if (!entities || entities.trim() === "") e.entities = t('Connector_Validation_Required');
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const onTest = async () => {
    if (!validate()) return;
    setTesting(true);
    setResult("");
    const body = {
      source,
      config: {
        base_url: baseUrl,
        company_id: company,
        entities: entities ? entities.split(",").map(s=>s.trim()).filter(Boolean) : []
      },
      secrets: parseSecrets()
    };
    try {
      const r = await testConnection(body);
      setResult(JSON.stringify(r));
      // Notify parent that configuration is ready
      if (onConfigReady) {
        onConfigReady({ source, config: body.config, secrets: body.secrets });
      }
    } catch (err: any) {
      setResult(err?.message || String(err));
    } finally {
      setTesting(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h2>{t('ConnectorWizard_SourceConfig_Title', 'Source Configuration')}</h2>

      <Label>{t('ConnectorWizard_SourceSystem_Label', 'Source system')}</Label>
      <Select value={source} onChange={(_, d) => setSource(d.value as string)} style={{minWidth: 240}}>
        <Option value="business_central">Business Central</Option>
        <Option value="d365">Dynamics 365 / Dataverse</Option>
        <Option value="salesforce">Salesforce</Option>
        <Option value="sap">SAP</Option>
      </Select>

      <div style={{ marginTop: 12 }}>
        <Label>{t('ConnectorWizard_BaseUrl_Label', 'Base URL / Endpoint')}</Label>
        <Input placeholder="https://api.businesscentral.dynamics.com/..." value={baseUrl} onChange={(_, ev) => setBaseUrl(ev?.value || "")} style={{ width: '100%' }} />
        {errors.baseUrl && <div style={{ color: 'var(--colorDanger, #a80000)', marginTop: 6 }}>{errors.baseUrl}</div>}
      </div>

      <div style={{ marginTop: 12 }}>
        <Label>{t('ConnectorWizard_Company_Label', 'Company (if applicable)')}</Label>
        <Input placeholder="CRONUS IT" value={company} onChange={(_, ev) => setCompany(ev?.value || "")} />
      </div>

      <div style={{ marginTop: 12 }}>
        <Label>{t('ConnectorWizard_Entities_Label', 'Entities / Tables (comma separated)')}</Label>
        <Input placeholder="ItemLedgerEntries, Customer" value={entities} onChange={(_, ev) => setEntities(ev?.value || "")} />
        {errors.entities && <div style={{ color: 'var(--colorDanger, #a80000)', marginTop: 6 }}>{errors.entities}</div>}
      </div>

      <div style={{ marginTop: 12 }}>
        <Label>{t('ConnectorWizard_Secrets_Label', 'Secrets (JSON)')}</Label>
        <Textarea 
          placeholder='{"client_id": "...", "client_secret": "..."}' 
          value={secrets} 
          onChange={(_, ev) => setSecrets(ev?.value || "")} 
          rows={6} 
          style={{ width: '100%' }} 
        />
      </div>

      {/* OBO Token Section */}
      <div style={{ marginTop: 20, padding: 12, background: 'var(--colorNeutralBackground2, #f3f2f1)', borderRadius: 4 }}>
        <Label style={{ fontWeight: 600 }}>{t('ConnectorWizard_OBOToken_Label', 'User Token for Delegated Access (Optional)')}</Label>
        <p style={{ fontSize: '12px', marginTop: 8, color: 'var(--colorNeutralForeground3)' }}>
          {t('ConnectorWizard_OBOToken_Description', 
            'Obtain a user access token to enable On-Behalf-Of (OBO) flows. This allows the backend to call source APIs on your behalf without storing your credentials.')}
        </p>
        
        {userToken ? (
          <>
            <MessageBar intent="success" style={{ marginTop: 12 }}>
              <MessageBarBody>
                {t('ConnectorWizard_UserTokenReady', 'User token ready for delegated flow')}
              </MessageBarBody>
            </MessageBar>
            <Button appearance="secondary" onClick={clearUserToken} style={{ marginTop: 12 }}>
              {t('ConnectorWizard_ClearToken_Button', 'Clear Token')}
            </Button>
          </>
        ) : (
          <Button 
            appearance="secondary" 
            onClick={handleObtainUserToken} 
            disabled={obtainingToken || tokenLoading || !workloadClient}
            style={{ marginTop: 12 }}
          >
            {obtainingToken || tokenLoading ? (
              <>
                <Spinner size="tiny" style={{ marginRight: 8 }} />
                {t('ConnectorWizard_ObtainingToken_Button', 'Obtaining Token...')}
              </>
            ) : (
              t('ConnectorWizard_ObtainToken_Button', 'Obtain User Token')
            )}
          </Button>
        )}
        {tokenError && (
          <div style={{ color: 'var(--colorDanger, #a80000)', marginTop: 8, fontSize: '12px' }}>
            {t('ConnectorWizard_TokenError_Message', 'Error obtaining token')}: {tokenError.message}
          </div>
        )}
      </div>

      <div style={{ marginTop: 12 }}>
        <Button 
          appearance="primary" 
          onClick={onTest} 
          disabled={testing || obtainingToken}
        >
          {testing ? (
            <>
              <Spinner size="tiny" style={{ marginRight: 8 }} />
              {t('ConnectorWizard_Testing_Button', 'Testing...')}
            </>
          ) : (
            t('ConnectorWizard_TestConnection_Button', 'Test connection')
          )}
        </Button>
      </div>

      {result && (
        <div style={{ marginTop: 12 }}>
          <Label>{t('ConnectorWizard_Result_Label', 'Result')}</Label>
          <pre style={{ background: '#f4f4f4', padding: 8, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>{result}</pre>
        </div>
      )}
    </div>
  );
};

export default SourceConfig;