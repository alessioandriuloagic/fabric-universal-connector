from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ConnectorRunRecord:
    run_id: str
    connector_id: str
    module_type: str
    run_start_utc: str
    run_end_utc: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str = "running"
    triggered_by: str = "on_demand"
    entities_succeeded: int = 0
    entities_failed: int = 0
    records_ingested: int = 0
    error_message: Optional[str] = None
    wheel_version: str = "1.0.0"
