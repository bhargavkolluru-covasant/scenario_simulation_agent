"""
OBSOLETE / DEPRECATED:
dependency_client is obsolete and no longer used in the enterprise simulation agent architecture.
Do NOT use or import this client in the workflow.
"""
import warnings


class DependencyClient:
    """
    Deprecated DependencyClient maintained strictly for backward compatibility.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "DependencyClient is obsolete and deprecated. Do not use in workflow.",
            DeprecationWarning,
            stacklevel=2,
        )

    async def resolve(self, *args, **kwargs):
        raise NotImplementedError("DependencyClient is obsolete and deprecated.")
