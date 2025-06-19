"""Flow Engine custom exceptions for structured error handling."""
from __future__ import annotations


class FlowError(Exception):
    """Base class for all engine errors returned to clients."""


class SectionNotFoundError(FlowError):
    """Raised when a Section node cannot be found."""


class EvaluatorTimeoutError(FlowError, TimeoutError):
    """Raised when a variable/evaluator exceeds its timeout."""


class SecurityError(FlowError):
    """Raised when sandbox violations occur.""" 