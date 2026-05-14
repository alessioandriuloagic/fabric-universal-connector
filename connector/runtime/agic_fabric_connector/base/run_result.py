from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EntityResult:
    entity_name: str
    status: str
    records_ingested: int
    records_failed: int
    duration_seconds: float
    new_watermark: Optional[str]
    error_message: Optional[str]


@dataclass
class RunResult:
    run_id: str
    status: str
    entity_results: List[EntityResult] = field(default_factory=list)
