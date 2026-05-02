"""Typed errors raised by external API boundary clients."""

from __future__ import annotations


class ExternalAPIError(Exception):
    """Base class for safe upstream failures."""


class MissingCredentialError(ExternalAPIError):
    """Required provider credential is not configured."""


class UpstreamTimeoutError(ExternalAPIError):
    """Provider did not respond within the configured timeout."""


class UpstreamServiceError(ExternalAPIError):
    """Provider returned an error or malformed response."""


class RegionNotFoundError(ExternalAPIError):
    """Geocoding provider could not resolve the requested region."""
