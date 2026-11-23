"""The L2 book at a moment of the day: the top levels on each side, with cumulative size.

    python l2/book_at.py [FILE] [--at 12:00] [--levels 10]

Without FILE it uses the free sample of Hyperliquid BTC for 1 November 2026.
"""

import argparse
from datetime import datetime, time, timezone
from pathlib import Path

import alphaquick as aq
from alphaquick import l2, samples


def main() -> None:
    parser = argparse.ArgumentParser(description="The L2 book at a moment of the day.")
    parser.add_argument("file", nargs="?", help="an L2 .bin.lz4 file (default: a free sample)")
    parser.add_argument("--at", default="12:00", help="a UTC time of day, HH:MM or HH:MM:SS (default 12:00)")
    parser.add_argument("--levels", type=int, default=10)
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("l2-btc-hyperliquid", quiet=False)

    # The file's day: from its first record (its name says it too).
    first = next(iter(aq.read_l2(path)), None)
    if first is None:
        raise SystemExit(f"{path.name} holds no L2 records")
    moment = datetime.combine(first.datetime.date(), time.fromisoformat(args.at), timezone.utc)

    book = l2.book_at(path, aq.datetime_to_ticks(moment))
    bids, asks = book.depth(args.levels)
    if not bids and not asks:
        raise SystemExit(f"the book is empty at {moment:%H:%M:%S} UTC: the file starts at {first.datetime:%H:%M:%S}")
    print(f"{path.name}: book at {moment:%Y-%m-%d %H:%M:%S} UTC"
          + ("" if book.consistent else " (in the middle of a batch of updates)"))
    print(f"{'cum. size':>14} {'size':>12} {'bid':>12} | {'ask':<12} {'size':<12} {'cum. size':<14}")
    cum_bid = cum_ask = 0
    for i in range(max(len(bids), len(asks))):
        left = right = ""
        if i < len(bids):
            price, size = bids[i]
            cum_bid += size
            left = f"{cum_bid / aq.SCALE:>14,.4f} {size / aq.SCALE:>12,.4f} {price / aq.SCALE:>12,.2f}"
        else:
            left = " " * 40
        if i < len(asks):
            price, size = asks[i]
            cum_ask += size
            right = f"{price / aq.SCALE:<12,.2f} {size / aq.SCALE:<12,.4f} {cum_ask / aq.SCALE:<14,.4f}"
        print(f"{left} | {right}")
    if bids and asks:
        mid = (bids[0][0] + asks[0][0]) / 2 / aq.SCALE
        spread = (asks[0][0] - bids[0][0]) / aq.SCALE
        print(f"mid {mid:,.2f}, spread {spread:g} ({spread / mid * 1e4:.2f} bps)")


if __name__ == "__main__":
    main()
