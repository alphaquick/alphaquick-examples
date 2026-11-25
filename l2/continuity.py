"""Where the recording of an L2 file started, broke and was rebuilt, from its .continuity.jsonl sidecar.

    python l2/continuity.py [FILE.continuity.jsonl]

Each `seed` line is a full copy of the book written into the data file (at the
start of the day, after the recorder started, or after a gap). Since
26 November 2026 each `gap` line marks where the venue feed broke: from there to
the next seed the file holds no depth updates and the book is unknown. Files up
to 25 November 2026 have only `legacy_seed` lines (one per recorder start) and,
for node venues, `incident`/`gap`/`no_loss`/`resume_complete` lines.
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
    parser = argparse.ArgumentParser(description="Seeds and gaps of an L2 file.")
    parser.add_argument("file", nargs="?", help="a .continuity.jsonl file (default: a free sample's)")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("l2-btc-hyperliquid-continuity", quiet=False)

    if not path.name.endswith(".continuity.jsonl"):
        raise SystemExit(f"{path.name} is not a .continuity.jsonl file (it sits next to the .bin.lz4 of the same name)")
    lines = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                lines.append(json.loads(line))
            except ValueError:
                pass  # a torn last line after a crash
    notes = {"gap": "book unknown until the next seed", "resume_complete": "no data lost",
             "no_loss": "no data lost", "incident": "break detected; see the line that closes it",
             "writer_failure": "recorder stopped writing"}
    print(f"{path.name}: {len(lines)} line{'s' if len(lines) != 1 else ''}")
    for entry in lines:
        # The set of kinds and fields may grow: read the ones you need, ignore the rest.
        kind = entry.get("kind", "?")
        at = entry.get("received_at_ms") or entry.get("detected_at_ms") or entry.get("recovery_at_ms")
        ordinal = entry.get("ordinal", entry.get("clear_ordinal", "?"))
        print(f"  {ordinal!s:>6}  {kind:<15} {entry.get('reason', ''):<16} received {when(at)} UTC  {notes.get(kind, '')}")
    gaps = sum(e.get("kind") == "gap" for e in lines)
    later_seeds = max(0, sum(e.get("kind") == "seed" for e in lines) - 1)
    if not gaps and not later_seeds:
        print("recorded as one stream")
    else:
        print(f"{gaps} gap(s): the book is unknown from each gap to the next seed; "
              f"{later_seeds} later seed(s) (a resync, a recorder restart, or a snapshot the venue sent)")
        if not gaps:
            print("files up to 25 November 2026 do not mark gaps: treat the book as discontinuous at each later seed")

if __name__ == "__main__":
    main()
