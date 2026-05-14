import React from "react";
import { PageProps } from "../App";
import ConnectorWizard from "../components/ConnectorWizard";
import "./ConnectorItem.scss";

export function ConnectorItemEditor(props: PageProps) {
  return (
    <div className="connector-item-view" style={{ height: '100%' }}>
      <ConnectorWizard workloadClient={props.workloadClient} />
    </div>
  );
}

export default ConnectorItemEditor;
