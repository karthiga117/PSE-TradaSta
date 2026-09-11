"""CoinGecko-backed market-data provider implementation."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

import httpx

from app.application.interfaces import IMarketDataProvider
from app.domain.market_data import Candle, MarketPrice


class CoinGeckoMarketDataProvider(IMarketDataProvider):
    """Public CoinGecko adapter for crypto market data."""

    _symbol_aliases: dict[str, str] = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "ADA": "cardano",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "LINK": "chainlink",
        "DOT": "polkadot",
    }

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        base_url: str = "https://api.coingecko.com/api/v3",
        timeout: float = 10.0,
    ) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._base_url = base_url.rstrip("/")

    async def __aenter__(self) -> CoinGeckoMarketDataProvider:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        del exc_type, exc, tb
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client when it is owned by the provider."""
        if self._client.is_closed:
            return
        await self._client.aclose()

    def _normalise_symbol(self, symbol: str) -> str:
        """Convert ticker-style input to a CoinGecko coin ID."""
        cleaned = symbol.strip().upper().replace("-", "").replace("_", "")
        if cleaned.endswith("USD"):
            cleaned = cleaned[:-3]
        coin_id = self._symbol_aliases.get(cleaned, cleaned.lower())
        if not coin_id:
            raise ValueError("A valid crypto symbol is required")
        return coin_id

    def _parse_decimal(self, value: object, field_name: str) -> Decimal:
        """Convert API values to Decimal while preserving value semantics."""
        if value is None:
            raise ValueError(f"{field_name} is required")

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be numeric") from exc

    @staticmethod
    def _timestamp_from_ms(value: object) -> datetime:
        """Convert a millisecond timestamp from the provider to a UTC datetime."""
        timestamp_ms = int(str(value))
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)

    async def _get_json(
        self,
        path: str,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        **kwargs: str | int | float | bool | None,
    ) -> object:
        """Fetch JSON from the upstream provider with a request timeout."""
        query_params: dict[str, str | int | float | bool | None] = {
            **(dict(params or {})),
            **kwargs,
        }
        response = await self._client.get(
            f"{self._base_url}{path}",
            params=query_params,
        )
        response.raise_for_status()
        return response.json()

    async def get_current_price(
        self,
        symbol: str,
        *,
        cancellation_token: object | None = None,
    ) -> MarketPrice:
        """Return the current price for a crypto asset."""
        del cancellation_token
        coin_id = self._normalise_symbol(symbol)
        payload = await self._get_json(
            "/simple/price",
            ids=coin_id,
            vs_currencies="usd",
            include_24hr_vol="true",
        )
        payload_map = cast(dict[str, object], payload)
        if coin_id not in payload_map:
            raise ValueError(f"No market data found for symbol {symbol!r}")

        price_entry = cast(dict[str, object], payload_map[coin_id])
        price_value = price_entry.get("usd")
        price = self._parse_decimal(price_value, "price")
        return MarketPrice(
            symbol=coin_id.upper(),
            price=price,
            currency="USD",
            timestamp=datetime.now(UTC),
            source="coingecko",
        )

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
        *,
        cancellation_token: object | None = None,
    ) -> list[Candle]:
        """Return candles using CoinGecko's market-chart endpoint."""
        del cancellation_token
        coin_id = self._normalise_symbol(symbol)
        days = self._resolve_days(timeframe, limit)
        interval = self._resolve_interval(timeframe)
        payload = await self._get_json(
            f"/coins/{coin_id}/market_chart",
            vs_currency="usd",
            days=str(days),
            interval=interval,
        )
        payload_map = cast(dict[str, object], payload)
        prices = cast(Sequence[object], payload_map.get("prices", []))
        volumes = cast(Sequence[object], payload_map.get("total_volumes", []))

        candles: list[Candle] = []
        previous_close = Decimal("0")
        for idx, entry in enumerate(prices):
            if not isinstance(entry, Sequence) or len(entry) < 2:
                continue
            timestamp_ms, price_value = entry
            price = self._parse_decimal(price_value, "price")

            if idx == 0:
                previous_close = price
            open_value = previous_close
            close_value = price
            high_value = max(open_value, close_value)
            low_value = min(open_value, close_value)
            volume_value = Decimal("0")
            if idx < len(volumes):
                volume_entry = cast(Sequence[object], volumes[idx])
                if len(volume_entry) >= 2:
                    volume_value = self._parse_decimal(volume_entry[1], "volume")

            candles.append(
                Candle(
                    symbol=coin_id.upper(),
                    timestamp=self._timestamp_from_ms(timestamp_ms),
                    open=open_value,
                    high=high_value,
                    low=low_value,
                    close=close_value,
                    volume=volume_value,
                )
            )
            previous_close = close_value

        return candles[-limit:] if limit and candles else candles

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = "1h",
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        *,
        cancellation_token: object | None = None,
    ) -> list[Candle]:
        """Return historical candles between start and end timestamps."""
        del cancellation_token
        coin_id = self._normalise_symbol(symbol)

        payload_map: dict[str, object]
        if start is not None and end is not None:
            start_ts = int(start.timestamp())
            end_ts = int(end.timestamp())
            payload = await self._get_json(
                f"/coins/{coin_id}/market_chart/range",
                params={"vs_currency": "usd", "from": start_ts, "to": end_ts},
            )
            payload_map = cast(dict[str, object], payload)
            values = cast(Sequence[object], payload_map.get("prices", []))
            volumes: Sequence[object] = []
        else:
            days = self._resolve_days(timeframe, limit or 24)
            payload = await self._get_json(
                f"/coins/{coin_id}/market_chart",
                vs_currency="usd",
                days=str(days),
                interval="hourly",
            )
            payload_map = cast(dict[str, object], payload)
            values = cast(Sequence[object], payload_map.get("prices", []))
            volumes = cast(Sequence[object], payload_map.get("total_volumes", []))
        candles: list[Candle] = []
        for idx, entry in enumerate(values):
            if not isinstance(entry, Sequence) or len(entry) < 2:
                continue
            timestamp_ms, price_value = entry
            volume_value = Decimal("0")
            if idx < len(volumes):
                volume_entry = cast(Sequence[object], volumes[idx])
                if len(volume_entry) >= 2:
                    volume_value = self._parse_decimal(volume_entry[1], "volume")
            candles.append(
                Candle(
                    symbol=coin_id.upper(),
                    timestamp=self._timestamp_from_ms(timestamp_ms),
                    open=self._parse_decimal(price_value, "price"),
                    high=self._parse_decimal(price_value, "price"),
                    low=self._parse_decimal(price_value, "price"),
                    close=self._parse_decimal(price_value, "price"),
                    volume=volume_value,
                )
            )

        if limit is not None and limit > 0:
            return candles[-limit:]
        return candles

    @staticmethod
    def _resolve_interval(timeframe: str) -> str:
        """Map the requested timeframe to a CoinGecko chart interval."""
        mapping = {
            "1m": "minutely",
            "5m": "5m",
            "15m": "15m",
            "1h": "hourly",
            "4h": "4h",
            "1d": "daily",
            "1w": "daily",
            "1M": "daily",
        }
        return mapping.get(timeframe.strip(), "hourly")

    @staticmethod
    def _resolve_days(timeframe: str, limit: int) -> int:
        """Translate a requested candle count into a stable CoinGecko day window."""
        normalized = timeframe.strip()
        timeframe_key = normalized.lower()

        if timeframe_key in {"1m", "5m", "15m", "1h", "4h"}:
            candles_per_day = {
                "1m": 1440,
                "5m": 288,
                "15m": 96,
                "1h": 24,
                "4h": 6,
            }
            days_required = max(1, math.ceil(limit / candles_per_day[timeframe_key]))
            return min(days_required, 90)

        if timeframe_key == "1d":
            return max(1, min(limit, 90))

        if timeframe_key == "1w":
            return max(1, min(math.ceil(limit / 7), 90))

        if normalized == "1M" or timeframe_key in {"1mth", "1month", "1mo"}:
            return max(1, min(limit, 3650))

        return max(1, min(limit, 90))


CoinMarketDataProvider = CoinGeckoMarketDataProvider
CoinbaseMarketDataProvider = CoinGeckoMarketDataProvider

__all__ = [
    "CoinGeckoMarketDataProvider",
    "CoinMarketDataProvider",
    "CoinbaseMarketDataProvider",
]
