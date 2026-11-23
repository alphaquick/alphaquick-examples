"""Follow one resting order through its queue: how its place improves until it is filled or canceled.

    python orderlog/queue_position.py [FILE] [--at 00:05] [--oid OID]

Without --oid it picks the order at the back of the best bid's queue at --at.
Without FILE it uses Order-Log Replay's ZEC sample (5 MB).
"""

import argparse
from datetime import datetime, time, timezone
from pathlib import Path

import alphaquick as aq
from alphaquick import orderlog as ol, samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Follow one order through its queue.")
    parser.add_argument("file", nargs="?", help="an order-log .bin.lz4 file (default: a free sample)")
    parser.add_argument("--at", default="00:05", help="when to pick the order, UTC HH:MM[:SS] (default 00:05)")
    parser.add_argument("--oid", type=int, help="the order id to follow (default: the back of the best bid queue)")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("orderlog-zec-30min", quiet=False)

    replay = aq.Replay(path)
    replay.run(until=0)  # the file's first block: META and the book at 00:00 UTC
    if replay.meta is None:
        raise SystemExit(f"{path.name} is not an order-log file")
    day = datetime.strptime(str(replay.meta.day), "%Y%m%d").date()
    replay.run(until=aq.datetime_to_ticks(datetime.combine(day, time.fromisoformat(args.at), timezone.utc)))
    book = replay.book

    if args.oid is None:
        if book.best_bid() is None:
            raise SystemExit(f"no bids rest at {args.at}: pick another time, or an order with --oid")
        oid = book.queue(ol.BID, book.best_bid())[-1].oid
    else:
        oid = args.oid
    order = book.orders.get(oid)
    if order is None:
        raise SystemExit(f"order {oid} is not resting at {args.at}")
    side = "bid" if order.side == ol.BID else "ask"
    print(f"order {oid}: {side} {order.size / aq.SCALE:g} at {order.price / aq.SCALE:g}, "
          f"account {replay.address(order.user_id)}")

    last = None
    filled = 0
    for record in replay:  # carries on from --at, applying each record
        if type(record) is ol.Trade and oid in (record.maker_oid, record.taker_oid):
            filled += record.size
            print(f"  {replay.datetime:%H:%M:%S.%f}  filled {record.size / aq.SCALE:g} at {record.price / aq.SCALE:g}")
        elif type(record) is ol.Order and record.oid == oid and record.status in ol.REMOVING_STATUSES:
            print(f"  {replay.datetime:%H:%M:%S.%f}  {record.status_name}; filled {filled / aq.SCALE:g} in all")
            return
        position = book.queue_position(oid)
        if position is not None and position != last:
            ahead, size = position
            print(f"  {replay.datetime:%H:%M:%S.%f}  {ahead} orders ahead, {size / aq.SCALE:,.3f} in size")
            last = position
    print(f"still resting at the end of the file; filled {filled / aq.SCALE:g}")


if __name__ == "__main__":
    main()
