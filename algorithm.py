"""Simple moving-average crossover algorithm for quilt-trader smoke testing.

When the fast SMA (default: 10-bar) crosses above the slow SMA (default: 30-bar)
on the configured symbol, emit a BUY signal. When it crosses back below and a
position is open, emit a SELL signal. Position is tracked in persisted state so
the algorithm survives restarts.
"""
from __future__ import annotations

from typing import Optional

from sdk.algorithm import QuiltAlgorithm
from sdk.signals import OrderType, Signal, SignalLeg, SignalType


class MaCrossoverAlgorithm(QuiltAlgorithm):
    def on_start(self, config: dict, restored_state: Optional[dict]) -> None:
        self.symbol: str = config.get("symbol", "SPY")
        self.fast_window: int = int(config.get("fast_window", 10))
        self.slow_window: int = int(config.get("slow_window", 30))
        self.quantity: float = float(config.get("quantity", 10))

        if self.fast_window >= self.slow_window:
            raise ValueError(
                f"fast_window ({self.fast_window}) must be less than "
                f"slow_window ({self.slow_window})"
            )

        state = restored_state or {}
        self.position_open: bool = bool(state.get("position_open", False))

    def on_tick(self, ctx) -> list[Signal]:
        bars = ctx.market_data(
            self.symbol,
            timeframe="1day",
            bars=self.slow_window + 1,
        )
        if bars is None or len(bars) < self.slow_window:
            return []

        closes = bars["close"]
        fast_sma = closes.tail(self.fast_window).mean()
        slow_sma = closes.tail(self.slow_window).mean()

        if fast_sma > slow_sma and not self.position_open:
            self.position_open = True
            self.notify(
                event_name="entry",
                message=f"{self.symbol} fast SMA crossed above slow SMA — buying {self.quantity}",
                data={"fast_sma": float(fast_sma), "slow_sma": float(slow_sma)},
            )
            return [Signal(
                legs=[SignalLeg(
                    symbol=self.symbol,
                    signal_type=SignalType.BUY,
                    quantity=self.quantity,
                    order_type=OrderType.MARKET,
                )],
            )]

        if fast_sma < slow_sma and self.position_open:
            self.position_open = False
            self.notify(
                event_name="exit",
                message=f"{self.symbol} fast SMA crossed below slow SMA — selling {self.quantity}",
                data={"fast_sma": float(fast_sma), "slow_sma": float(slow_sma)},
            )
            return [Signal(
                legs=[SignalLeg(
                    symbol=self.symbol,
                    signal_type=SignalType.SELL,
                    quantity=self.quantity,
                    order_type=OrderType.MARKET,
                )],
            )]

        return []

    def on_stop(self) -> dict:
        return self.save_state()

    def save_state(self) -> dict:
        return {"position_open": self.position_open}
