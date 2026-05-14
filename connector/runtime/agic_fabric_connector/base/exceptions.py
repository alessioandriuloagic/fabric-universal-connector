from typing import Optional


class ConnectorError(Exception):
    error_code: str = "UNKNOWN_ERROR"


class ConnectorFatalError(ConnectorError):
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class AuthenticationError(ConnectorError):
    error_code = "AUTH_ERROR"


class ThrottlingError(ConnectorError):
    error_code = "THROTTLING_ERROR"

    def __init__(self, message: str, retry_after_seconds: Optional[float] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TransientError(ConnectorError):
    error_code = "TRANSIENT_ERROR"


class EntityExtractionError(ConnectorError):
    error_code = "EXTRACTION_ERROR"


class BronzeWriteError(ConnectorError):
    error_code = "BRONZE_WRITE_ERROR"


class SchemaConflictError(ConnectorError):
    error_code = "SCHEMA_CONFLICT_ERROR"


class ConfigValidationError(ConnectorError):
    error_code = "CONFIG_VALIDATION_ERROR"


class ConfigLoadError(ConnectorError):
    error_code = "CONFIG_LOAD_ERROR"
