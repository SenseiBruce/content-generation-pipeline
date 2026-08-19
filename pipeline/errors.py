"""Typed errors for pipeline stages."""


class PipelineError(Exception):
    """Base error for pipeline failures."""


class PipelineValidationError(PipelineError):
    """Raised when generated content fails schema validation."""
