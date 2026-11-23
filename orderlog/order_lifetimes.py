"""How long resting orders (GTC and post-only) stay in the book before they are canceled or filled.

    python orderlog/order_lifetimes.py [FILE]

Times come from the block clock (consensus time). Without FILE it uses
Order-Log Replay's ZEC sample (5 MB).
"""

import argparse
from pathlib import Path

import pandas as pd

import alphaquick as aq
from alphaquick import orderlog as ol, samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Order lifetimes: placed to canceled or filled.")
    parser.add_argument("file", nargs="?", help="an order-log .bin.lz4 file (default: a free sample)")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("orderlog-zec-30min", quiet=False)

    placed = {}  # oid -> block time (ns) it was placed
    ended = []   # (lifetime in ms, how it ended)
    replay = aq.Replay(path)
    for record in replay:
        if type(record) is not ol.Order:
            continue
        # Only orders placed to rest: IOC and market orders fill or go at once.
        if record.status == ol.Status.OPEN and record.tif in (ol.Tif.GTC, ol.Tif.ALO):
            placed[record.oid] = replay.block.time_ns
        elif record.status in ol.REMOVING_STATUSES and record.oid in placed:
            lifetime_ms = (replay.block.time_ns - placed.pop(record.oid)) / 1e6
            ended.append((lifetime_ms, "filled" if record.status == ol.Status.FILLED else "canceled"))

    if replay.meta is None:
        raise SystemExit(f"{path.name} is not an order-log file")
    frame = pd.DataFrame(ended, columns=["lifetime_ms", "end"])
    if frame.empty:
        raise SystemExit("no resting order was both placed and ended during this file")
    print(f"{len(frame):,} orders placed and ended during the file; {len(placed):,} still resting at its end")
    summary = frame.groupby("end")["lifetime_ms"].describe(percentiles=[0.1, 0.5, 0.9])
    pd.set_option("display.width", 160)
    print("lifetime in milliseconds:")
    print(summary[["count", "10%", "50%", "90%", "max"]].round(0).to_string())
    canceled = frame[frame["end"] == "canceled"]["lifetime_ms"]
    if len(canceled):
        print(f"canceled within 1 s: {(canceled < 1000).mean():.1%}, within 10 s: {(canceled < 10_000).mean():.1%}")


if __name__ == "__main__":
    main()
