"""Abstract base crypto client definition."""

from abc import ABC, abstractmethod
from typing import Optional


class CryptoClientError(Exception):
    """Base exception for cryptocurrency client errors."""
    pass


class DeribitAPIError(CryptoClientError):
    """Exception raised when Deribit API returns an error response."""

    def __init__(self, message: str, status_code: Optional[int] = None, error_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class DeribitConnectionError(CryptoClientError):
    """Exception raised when network or connection issues occur."""
    pass


class DeribitInvalidResponseError(CryptoClientError):
    """Exception raised when response format is invalid or missing required fields."""
    pass


class BaseCryptoClient(ABC):
    """Abstract interface for external cryptocurrency exchange clients."""

    @abstractmethod
    async def get_index_price(self, ticker: str) -> float:
        """Fetch the current index price for the specified ticker.

        Args:
            ticker: The currency pair ticker symbol (e.g. 'btc_usd', 'eth_usd').

        Returns:
            Current index price as a float.

        Raises:
            CryptoClientError: If request fails or response is invalid.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Gracefully close HTTP session and any active network connections."""
        pass
