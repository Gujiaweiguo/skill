class ProductContextError(RuntimeError):
    """Base error for invalid or unavailable product context."""


class ResolutionError(ProductContextError):
    """Raised when a company or product cannot be resolved unambiguously."""
