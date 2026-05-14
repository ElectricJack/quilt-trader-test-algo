# simple-ma-crossover

A trivial moving-average crossover algorithm for [quilt-trader](https://github.com/) smoke testing.

## Behavior

- Buys the configured symbol (default: `SPY`) when the fast SMA crosses above the slow SMA.
- Sells when the fast SMA crosses back below (only if a position is open).
- Tracks position state across restarts via `save_state` / `restored_state`.

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `symbol` | `SPY` | Underlying to trade |
| `fast_window` | `10` | Fast SMA window (bars) |
| `slow_window` | `30` | Slow SMA window (bars). Must exceed `fast_window`. |
| `quantity` | `10` | Share quantity per signal |

## Install

Install via the quilt-trader dashboard:

1. Open **Algorithms** → **Install from GitHub**.
2. Paste this repo's URL: `https://github.com/ElectricJack/quilt-trader-test-algo`.
3. Submit.

The coordinator fetches `quilt.yaml` from the repo, verifies `type: algorithm`, and clones + installs.

## Caveats

This is intended for end-to-end smoke testing of the quilt-trader install / run / fill / sync paths. **Don't run it with real money** — moving-average crossovers are a textbook example, not a strategy.
