"""Simple moving-average crossover algorithm for quilt-trader smoke testing.

When the fast SMA (default: 10-bar) crosses above the slow SMA (default: 30-bar)
on the configured symbol, emit a BUY signal sized by available buying power.
When it crosses back below and a position is open, emit a SELL signal that
closes the actual held quantity. Position state tracked across restarts.
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
        # `target_allocation_pct` (default 0.95): fraction of buying power to
        # deploy per entry. Leaves a small buffer for slippage and fees so the
        # framework's buying-power check doesn't reject the order.
        self.target_allocation_pct: float = float(config.get("target_allocation_pct", 0.95))

        if self.fast_window >= self.slow_window:
            raise ValueError(
                f"fast_window ({self.fast_window}) must be less than "
                f"slow_window ({self.slow_window})"
            )

        state = restored_state or {}
        self.position_open: bool = bool(state.get("position_open", False))
        # Quantity is computed at entry time from buying power; remember what
        # we bought so the exit closes exactly that amount.
        self.held_quantity: float = float(state.get("held_quantity", 0.0))

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
        last_close = float(closes.iloc[-1])

        if fast_sma > slow_sma and not self.position_open:
            # Size from buying power so we never trigger the framework's
            # insufficient-buying-power rejection on a market fill (which fills
            # at the NEXT bar's open + slippage — so we under-deploy slightly).
            max_shares = int((ctx.buying_power * self.target_allocation_pct) // last_close)
            if max_shares <= 0:
                return []
            self.position_open = True
            self.held_quantity = float(max_shares)
            self.notify(
                event_name="entry",
                message=(
                    f"{self.symbol} fast SMA crossed above slow SMA — "
                    f"buying {max_shares} (buying_power=${ctx.buying_power:,.2f}, "
                    f"last_close=${last_close:.2f})"
                ),
                data={"fast_sma": float(fast_sma), "slow_sma": float(slow_sma),
                      "quantity": max_shares, "last_close": last_close},
            )
            return [Signal(
                legs=[SignalLeg(
                    symbol=self.symbol,
                    signal_type=SignalType.BUY,
                    quantity=float(max_shares),
                    order_type=OrderType.MARKET,
                )],
            )]

        if fast_sma < slow_sma and self.position_open and self.held_quantity > 0:
            qty = self.held_quantity
            self.position_open = False
            self.held_quantity = 0.0
            self.notify(
                event_name="exit",
                message=f"{self.symbol} fast SMA crossed below slow SMA — selling {qty}",
                data={"fast_sma": float(fast_sma), "slow_sma": float(slow_sma),
                      "quantity": qty},
            )
            return [Signal(
                legs=[SignalLeg(
                    symbol=self.symbol,
                    signal_type=SignalType.SELL,
                    quantity=qty,
                    order_type=OrderType.MARKET,
                )],
            )]

        return []

    def on_stop(self) -> dict:
        return self.save_state()

    def save_state(self) -> dict:
        return {
            "position_open": self.position_open,
            "held_quantity": self.held_quantity,
        }
