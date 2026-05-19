from typing import Optional


class ConnectorError(Exception):
    error_code: str = "UNKNOWN_ERROR"


class ConnectorFatalError(ConnectorError):
    """Non-recoverable. Aborts the entire run."""
    def __init__(self, message: str, error_code: str = "FATAL_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class AuthenticationError(ConnectorError):
    """Token acquisition failed — retryable."""
    error_code = "AUTH_ERROR"


class ThrottlingError(ConnectorError):
    """HTTP 429 from source — retryable with Retry-After."""
    error_code = "THROTTLING_ERROR"

    def __init__(self, message: str, retry_after_seconds: Optional[float] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TransientError(ConnectorError):
    """Network / 5xx error — retryable."""
    error_code = "TRANSIENT_ERROR"


class EntityExtractionError(ConnectorError):
    """Logic error during extraction — not retryable, stops this entity."""
    error_code = "EXTRACTION_ERROR"


class BronzeWriteError(ConnectorError):
    """Delta Lake / ABFS write failure — not retryable."""
    error_code = "BRONZE_WRITE_ERROR"


class SchemaConflictError(ConnectorError):
    """Schema changed under 'strict' policy — not retryable."""
    error_code = "SCHEMA_CONFLICT_ERROR"


class ConfigValidationError(ConnectorError):
    """Item definition is invalid or incomplete."""
    error_code = "CONFIG_VALIDATION_ERROR"


class ConfigLoadError(ConnectorError):
    """Failed to load item definition from Fabric Items API."""
    error_code = "CONFIG_LOAD_ERROR"
