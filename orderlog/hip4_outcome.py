"""A HIP-4 prediction market through a day: the price of "Yes", and the mints and merges hour by hour.

    python orderlog/hip4_outcome.py [FILE]

The file must hold both books of an outcome market (META flag 1). Prices are
the first side's, as shares of 1, so the mid is the market's probability of it.
Without FILE it uses the free sample of the Fed's October 2026 rate decision.
"""

import argparse
from collections import Counter
from pathlib import Path

import alphaquick as aq
from alphaquick import orderlog as ol, samples


def main() -> None:
    parser = argparse.ArgumentParser(description="A HIP-4 prediction market through a day.")
    parser.add_argument("file", nargs="?", help="an outcome-market order-log file (default: a free sample)")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("orderlog-hip4", quiet=False)

    replay = aq.Replay(path)
    kinds = {}  # hour -> Counter of trade kinds, and the size traded
    mids = {}   # hour -> the mid after the hour's last trade
    for record in replay:
        if type(record) is ol.Meta and not record.is_outcome:
            raise SystemExit(f"{path.name} is not an outcome market with both books")
        if type(record) is not ol.Trade:
            continue
        hour = replay.datetime.hour
        row = kinds.setdefault(hour, Counter())
        row[replay.last_trade_kind.name.lower()] += 1
        row["size"] += record.size
        bid, ask = replay.book.best_bid(), replay.book.best_ask()
        if bid is not None and ask is not None:
            mids[hour] = (bid + ask) / 2 / aq.SCALE

    if replay.meta is None or replay.outcome is None:
        raise SystemExit(f"{path.name} is not an outcome market with both books (is it an order-log file?)")
    info = replay.outcome
    yes, no = info.sides
    print(f"{info.title} (outcome {info.outcome})")
    if info.question:
        print(f"question: {info.question}")
    print(f"sides: {yes} / {no}; the mid is the market's probability of {yes}")
    if info.settled is not None:
        print(f"settled: {yes} paid {info.settled}")
    print(f"\n{'hour':>5} {'mid':>8} {'trades':>7} {'mints':>6} {'merges':>7} {'one book':>9} {'size':>12}")
    for hour in sorted(kinds):
        row = kinds[hour]
        one_book = row["first_book"] + row["second_book"]
        trades = one_book + row["mint"] + row["merge"] + row["unknown"]
        mid = f"{mids[hour]:.4f}" if hour in mids else "-"
        print(f"{hour:>4}h {mid:>8} {trades:>7} {row['mint']:>6} {row['merge']:>7} {one_book:>9} {row['size'] / aq.SCALE:>12,.0f}")
    print("\nA mint creates a pair of tokens (a buy on each book); a merge redeems one (a sell on each).")


if __name__ == "__main__":
    main()
