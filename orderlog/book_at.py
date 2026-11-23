"""The order-level book at a moment: levels with their order counts, and who is at the front of each queue.

    python orderlog/book_at.py [FILE] [--at 00:15] [--levels 10] [--queue 5]

Without FILE it uses Order-Log Replay's sample: the first 30 minutes of ZEC on
14 October 2026 (5 MB, downloaded once).
"""

import argparse
from collections import Counter
from datetime import datetime, time, timezone
from pathlib import Path

import alphaquick as aq
from alphaquick import orderlog as ol, samples


def px(value: int) -> str:
    return f"{value / aq.SCALE:g}"


def main() -> None:
    parser = argparse.ArgumentParser(description="The order-level book at a moment.")
    parser.add_argument("file", nargs="?", help="an order-log .bin.lz4 file (default: a free sample)")
    parser.add_argument("--at", default="00:15", help="a UTC time of day, HH:MM or HH:MM:SS (default 00:15)")
    parser.add_argument("--levels", type=int, default=10)
    parser.add_argument("--queue", type=int, default=5, help="orders to list at each best price")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("orderlog-zec-30min", quiet=False)

    replay = aq.Replay(path)
    replay.run(until=0)  # the file's first block: META and the book at 00:00 UTC
    if replay.meta is None:
        raise SystemExit(f"{path.name} is not an order-log file")
    day = datetime.strptime(str(replay.meta.day), "%Y%m%d").date()
    moment = datetime.combine(day, time.fromisoformat(args.at), timezone.utc)
    replay.run(until=aq.datetime_to_ticks(moment))  # carries on to the moment
    book = replay.book

    print(f"{replay.meta.coin} at {moment:%Y-%m-%d %H:%M:%S} UTC (block {replay.block.number:,}): "
          f"{len(book):,} resting orders")
    print(f"{'orders':>7} {'size':>14} {'bid':>10} | {'ask':<10} {'size':<14} {'orders':<7}")
    bids, asks = book.depth(ol.BID, args.levels), book.depth(ol.ASK, args.levels)
    for i in range(max(len(bids), len(asks))):
        left = f"{bids[i][2]:>7} {bids[i][1] / aq.SCALE:>14,.3f} {px(bids[i][0]):>10}" if i < len(bids) else " " * 33
        right = f"{px(asks[i][0]):<10} {asks[i][1] / aq.SCALE:<14,.3f} {asks[i][2]:<7}" if i < len(asks) else ""
        print(f"{left} | {right}")

    for side, best in ((ol.BID, book.best_bid()), (ol.ASK, book.best_ask())):
        if best is None:
            continue
        queue = book.queue(side, best)
        print(f"\nqueue at the best {'bid' if side == ol.BID else 'ask'} {px(best)}: {len(queue)} orders, front first")
        for place, order in enumerate(queue[: args.queue], 1):
            print(f"  {place:>2}. {order.size / aq.SCALE:>12,.3f}  {replay.address(order.user_id)}  oid {order.oid}")

    busiest = Counter(order.user_id for order in book.orders.values()).most_common(3)
    print("\naccounts with the most resting orders:")
    for user_id, count in busiest:
        print(f"  {count:>5}  {replay.address(user_id)}")


if __name__ == "__main__":
    main()
