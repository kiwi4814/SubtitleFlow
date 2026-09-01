from __future__ import annotations


class SubtitleFlowError(Exception):
    """Base exception for user-facing workflow failures."""


class ValidationError(SubtitleFlowError):
    """Raised when external or persisted data is invalid."""


class GateError(SubtitleFlowError):
    """Raised when a workflow gate blocks an operation."""


class SourceIntegrityError(GateError):
    """Raised when an immutable source changed after import."""
