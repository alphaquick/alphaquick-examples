"""One-second bars from an L2 file: best bid and ask, spread, volume by aggressor, VWAP and CVD.

    python l2/bars.py [FILE] [--every 1s] [-o bars.parquet]

Without FILE it uses the free sample of Hyperliquid BTC for 1 November 2026
(9.1 MB, downloaded once). The bars are printed and saved as Parquet.
"""

import argparse
from pathlib import Path

import pandas as pd

from alphaquick import frames, samples


def main() -> None:
    parser = argparse.ArgumentParser(description="One-second (or other) bars from an L2 file.")
    parser.add_argument("file", nargs="?", help="an L2 .bin.lz4 file (default: a free sample)")
    parser.add_argument("--every", default="1s", help="bar length as a pandas frequency: 1s, 5s, 1min ... (default 1s)")
    parser.add_argument("-o", "--output", default="bars.parquet")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("l2-btc-hyperliquid", quiet=False)

    # The best bid and ask whenever the book is consistent, and every trade.
    quotes = frames.l2_quotes(path).set_index("time")
    trades = frames.l2_trades(path).set_index("time")
    if quotes.empty:
        raise SystemExit(f"{path.name} has no complete quote (is it an L2 file?)")

    bars = quotes[["bid", "ask"]].resample(args.every).last()
    buys = trades["volume"].where(trades["side"] == "buy", 0.0)
    sells = trades["volume"].where(trades["side"] == "sell", 0.0)
    flow = pd.DataFrame({
        "volume": trades["volume"].resample(args.every).sum(),
        "buy_volume": buys.resample(args.every).sum(),
        "sell_volume": sells.resample(args.every).sum(),
        "trades": trades["volume"].resample(args.every).count(),
        "notional": (trades["price"] * trades["volume"]).resample(args.every).sum(),
    })
    bars = bars.join(flow, how="outer")
    bars[["bid", "ask"]] = bars[["bid", "ask"]].ffill()  # a bar with no update keeps the last quote
    bars[flow.columns] = bars[flow.columns].fillna(0)
    bars["spread"] = bars["ask"] - bars["bid"]
    bars["vwap"] = bars["notional"] / bars["volume"].where(bars["volume"] > 0)
    bars["cvd"] = (bars["buy_volume"] - bars["sell_volume"]).cumsum()  # cumulative volume delta
    bars = bars.drop(columns="notional")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)
    print(bars.dropna(subset=["bid", "ask"]).head(10).round(4))  # from the first full quote
    print(f"\n{len(bars):,} bars of {args.every}, {len(trades):,} trades, "
          f"from {bars.index[0]:%Y-%m-%d %H:%M:%S} to {bars.index[-1]:%H:%M:%S} UTC")
    print(f"median spread {bars['spread'].median():g}, total volume {bars['volume'].sum():,.4f}, "
          f"final CVD {bars['cvd'].iloc[-1]:+,.4f}")
    bars.to_parquet(args.output)
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
