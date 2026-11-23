"""Where the recording of an L2 file started or restarted, from its .continuity.jsonl sidecar.

    python l2/continuity.py [FILE.continuity.jsonl]

One line means the day was recorded as one stream. Each further line is a point
where the book was seeded again: continuity across it is not guaranteed.
Without FILE it uses the sidecar of the free sample of Hyperliquid BTC.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from alphaquick import samples


def when(ms):
    return "-" if ms is None else datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-seed points of an L2 file.")
    parser.add_argument("file", nargs="?", help="a .continuity.jsonl file (default: a free sample's)")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("l2-btc-hyperliquid-continuity", quiet=False)

    if not path.name.endswith(".continuity.jsonl"):
        raise SystemExit(f"{path.name} is not a .continuity.jsonl file (it sits next to the .bin.lz4 of the same name)")
    lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    print(f"{path.name}: {len(lines)} line{'s' if len(lines) != 1 else ''}")
    for entry in lines:
        # The set of fields may grow: read the ones you need, ignore the rest.
        print(f"  {entry.get('ordinal', '?'):>3}  {entry.get('kind', '?'):<8} {entry.get('reason', ''):<16} "
              f"{entry.get('symbol', '')}  received {when(entry.get('received_at_ms'))} UTC")
    if len(lines) <= 1:
        print("recorded as one stream: no re-seed during the day")
    else:
        print(f"{len(lines) - 1} re-seed(s): treat the book as discontinuous at those times")


if __name__ == "__main__":
    main()
