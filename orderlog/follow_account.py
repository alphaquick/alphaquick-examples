"""One account through a day: its order events, its fills and its position after each fill.

    python orderlog/follow_account.py [FILE] [--account 0x...]

Without --account it follows the account with the most fills.
Without FILE it uses Order-Log Replay's ZEC sample (5 MB).
"""

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

from alphaquick import frames, samples


def main() -> None:
    parser = argparse.ArgumentParser(description="One account through a day.")
    parser.add_argument("file", nargs="?", help="an order-log .bin.lz4 file (default: a free sample)")
    parser.add_argument("--account", help="the address to follow (default: the account with the most fills)")
    args = parser.parse_args()
    path = Path(args.file) if args.file else samples.fetch("orderlog-zec-30min", quiet=False)

    trades = frames.orderlog_trades(path)
    if "kind" in trades.columns:
        # Positions there are in the token of each order's own book, while sides are
        # in the first side's terms: this script's position arithmetic does not apply.
        raise SystemExit(f"{path.name} is a HIP-4 outcome market; see orderlog/hip4_outcome.py")
    if trades.empty:
        raise SystemExit(f"{path.name} holds no order-log trades (is it an order-log file?)")
    account = (args.account or pd.concat([trades["maker"], trades["taker"]]).value_counts().index[0]).lower()

    # Its fills, from either side of the trade, with the position after each.
    as_maker = trades[trades["maker"] == account].assign(role="maker", position_before=lambda t: t["maker_position"])
    as_taker = trades[trades["taker"] == account].assign(role="taker", position_before=lambda t: t["taker_position"])
    fills = pd.concat([as_maker, as_taker]).sort_index()  # file order
    bought = ((fills["role"] == "taker") & (fills["taker_side"] == "buy")) | ((fills["role"] == "maker") & (fills["taker_side"] == "sell"))
    fills["side"] = bought.map({True: "buy", False: "sell"})
    fills["position_after"] = fills["position_before"] + fills["size"].where(bought, -fills["size"])

    orders = frames.orderlog_orders(path)
    own = orders[orders["account"] == account]

    print(f"account {account}")
    print(f"order events: {len(own):,}  " + ", ".join(f"{name} {n:,}" for name, n in Counter(own["status"]).most_common(5)))
    print(f"fills: {len(fills):,} ({(fills['role'] == 'maker').sum():,} as maker), "
          f"bought {fills.loc[bought, 'size'].sum():,.3f}, sold {fills.loc[~bought, 'size'].sum():,.3f}")
    pd.set_option("display.width", 160)
    print(fills[["time", "role", "side", "price", "size", "position_after"]].head(15).to_string(index=False))
    if len(fills):
        print(f"position: {fills['position_before'].iloc[0]:+,.3f} before the first fill, "
              f"{fills['position_after'].iloc[-1]:+,.3f} after the last")


if __name__ == "__main__":
    main()
