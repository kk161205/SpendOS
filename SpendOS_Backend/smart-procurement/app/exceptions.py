"""
Custom exceptions for SpendOS.
"""

class VendorDiscoveryError(Exception):
    """Raised when vendor discovery permanently fails after retries."""
    pass
