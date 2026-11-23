"""Who traded: the notional each account traded as maker and as taker, and its share of the day.

    python orderlog/maker_taker.py [FILE] [--top 10]

Without FILE it uses Order-Log Replay's ZEC sample (5 MB).
"""

import argparse
from pathlib import Path

import pandas as pd

from alphaquick import frames, samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Maker and taker volume per account.")
    parser.add_argument("file", nargs="?", help="an order-log .bin.lz4 file (default: a free sample)")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("orderlog-zec-30min", quiet=False)

    trades = frames.orderlog_trades(path)
    if trades.empty:
        raise SystemExit(f"{path.name} holds no order-log trades (is it an order-log file?)")
    trades["notional"] = trades["price"] * trades["size"]
    table = pd.DataFrame({
        "as_maker": trades.groupby("maker")["notional"].sum(),
        "as_taker": trades.groupby("taker")["notional"].sum(),
        "fills": trades["maker"].value_counts().add(trades["taker"].value_counts(), fill_value=0),
    }).fillna(0)
    table["total"] = table["as_maker"] + table["as_taker"]
    table["share_%"] = 100 * table["total"] / (2 * trades["notional"].sum())  # each trade has two sides
    table["maker_%"] = 100 * table["as_maker"] / table["total"]
    table = table.sort_values("total", ascending=False)

    print(f"{len(trades):,} trades, {trades['notional'].sum():,.0f} notional, {len(table):,} accounts")
    pd.set_option("display.width", 160)
    print(table.head(args.top).round({"as_maker": 0, "as_taker": 0, "total": 0, "share_%": 2, "maker_%": 1})
          .astype({"fills": int}).to_string())
    print(f"the top {args.top} accounts took part in {table['share_%'].head(args.top).sum():.1f}% of the traded notional")


if __name__ == "__main__":
    main()
