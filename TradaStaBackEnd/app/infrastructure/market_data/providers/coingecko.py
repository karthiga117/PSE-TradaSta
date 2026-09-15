"""CoinGecko-backed market-data provider implementation."""

from __future__ import annotations

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

    @staticmethod
    def _canonical_symbol(symbol: str) -> str:
        """Normalise a user-facing symbol for API responses."""
        cleaned = symbol.strip().upper().replace("-", "").replace("_", "")
        if cleaned.endswith("USDT"):
            cleaned = cleaned[: -len("USDT")]
        elif cleaned.endswith("USD"):
            cleaned = cleaned[: -len("USD")]
        if not cleaned:
            raise ValueError("A valid crypto symbol is required")
        return cleaned

    def _normalise_symbol(self, symbol: str) -> str:
        """Convert ticker-style input to a CoinGecko coin ID."""
        cleaned = self._canonical_symbol(symbol)
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

    @staticmethod
    def _binance_interval_for(timeframe: str) -> str:
        """Map frontend timeframe values to Binance market intervals."""
        mapping = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1w",
        }
        return mapping.get(timeframe.lower(), "1h")

    async def _get_binance_json(
        self,
        path: str,
        params: Mapping[str, str | int | float | bool | None] | None = None,
        **kwargs: str | int | float | bool | None,
    ) -> object:
        """Fetch JSON from Binance if the primary CoinGecko source is rate-limited."""
        query_params: dict[str, str | int | float | bool | None] = {
            **(dict(params or {})),
            **kwargs,
        }
        async with httpx.AsyncClient(base_url="https://api.binance.com/api/v3", timeout=15.0) as client:
            response = await client.get(f"{path}", params=query_params)
            response.raise_for_status()
            return response.json()

    async def _get_binance_current_price(self, symbol: str) -> MarketPrice:
        """Fetch current price from Binance as a safe fallback when CoinGecko is rate-limited."""
        requested_symbol = self._canonical_symbol(symbol)
        base_symbol = f"{requested_symbol}USDT" if not requested_symbol.endswith("USDT") else requested_symbol
        payload = await self._get_binance_json("/ticker/price", symbol=base_symbol)
        payload_map = cast(dict[str, object], payload)
        price_value = payload_map.get("price")
        if price_value is None:
            raise ValueError(f"No market data found for symbol {symbol!r}")
        return MarketPrice(
            symbol=requested_symbol,
            price=self._parse_decimal(price_value, "price"),
            currency="USD",
            timestamp=datetime.now(UTC),
            source="binance",
        )

    async def _get_binance_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
    ) -> list[Candle]:
        """Fetch OHLCV data from Binance when CoinGecko is unavailable."""
        requested_symbol = self._canonical_symbol(symbol)
        base_symbol = f"{requested_symbol}USDT" if not requested_symbol.endswith("USDT") else requested_symbol
        payload = await self._get_binance_json(
            "/klines",
            symbol=base_symbol,
            interval=self._binance_interval_for(timeframe),
            limit=max(1, min(limit, 1000)),
        )
        entries = cast(Sequence[object], payload)

        candles: list[Candle] = []
        for entry in entries:
            if not isinstance(entry, Sequence) or len(entry) < 6:
                continue
            timestamp_ms, open_value, high_value, low_value, close_value, volume_value = entry[:6]
            candles.append(
                Candle(
                    symbol=requested_symbol,
                    timestamp=self._timestamp_from_ms(timestamp_ms),
                    open=self._parse_decimal(open_value, "open"),
                    high=self._parse_decimal(high_value, "high"),
                    low=self._parse_decimal(low_value, "low"),
                    close=self._parse_decimal(close_value, "close"),
                    volume=self._parse_decimal(volume_value, "volume"),
                )
            )

        return candles[-limit:] if limit and candles else candles

    async def get_current_price(
        self,
        symbol: str,
        *,
        cancellation_token: object | None = None,
    ) -> MarketPrice:
        """Return the current price for a crypto asset."""
        del cancellation_token
        requested_symbol = self._canonical_symbol(symbol)
        coin_id = self._normalise_symbol(symbol)
        try:
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
                symbol=requested_symbol,
                price=price,
                currency="USD",
                timestamp=datetime.now(UTC),
                source="coingecko",
            )
        except Exception:
            return await self._get_binance_current_price(symbol)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 24,
        *,
        cancellation_token: object | None = None,
    ) -> list[Candle]:
        """Return candles using CoinGecko's OHLC endpoint."""
        del cancellation_token
        coin_id = self._normalise_symbol(symbol)
        try:
            days = self._resolve_days(timeframe, limit)
            payload = await self._get_json(
                f"/coins/{coin_id}/ohlc",
                vs_currency="usd",
                days=str(days),
            )
            entries = cast(Sequence[object], payload)

            candles: list[Candle] = []
            for entry in entries:
                if not isinstance(entry, Sequence) or len(entry) < 5:
                    continue
                timestamp_ms, open_value, high_value, low_value, close_value = entry
                candles.append(
                    Candle(
                        symbol=self._canonical_symbol(symbol),
                        timestamp=self._timestamp_from_ms(timestamp_ms),
                        open=self._parse_decimal(open_value, "open"),
                        high=self._parse_decimal(high_value, "high"),
                        low=self._parse_decimal(low_value, "low"),
                        close=self._parse_decimal(close_value, "close"),
                        volume=Decimal("0"),
                    )
                )

            return candles[-limit:] if limit and candles else candles
        except Exception:
            return await self._get_binance_ohlcv(symbol, timeframe=timeframe, limit=limit)

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

        try:
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
        except Exception:
            return await self._get_binance_ohlcv(symbol, timeframe=timeframe, limit=limit or 24)

    @staticmethod
    def _resolve_days(timeframe: str, limit: int) -> int:
        """Translate timeframe and limit into a valid CoinGecko OHLC day window."""
        valid_days = [1, 7, 14, 30, 90, 180, 365, 730, 1095, max(1, min(limit, 3650))]
        mapping = {
            "1m": 1,
            "5m": 1,
            "15m": 1,
            "1h": 30,
            "4h": 30,
            "1d": 30,
            "1w": 365,
            "1M": 3650,
        }
        candidate = mapping.get(timeframe.lower(), max(1, min(limit, 30)))
        if candidate not in valid_days:
            candidate = min(valid_days, key=lambda value: abs(value - candidate))
        return max(1, candidate)


CoinMarketDataProvider = CoinGeckoMarketDataProvider
CoinbaseMarketDataProvider = CoinGeckoMarketDataProvider

__all__ = [
    "CoinGeckoMarketDataProvider",
    "CoinMarketDataProvider",
    "CoinbaseMarketDataProvider",
]
