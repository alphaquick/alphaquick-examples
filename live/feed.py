"""feed.py: stream one book from the AlphaQuick relay and keep it up to date.
pip install -r live/requirements.txt, then: AQ_API_KEY=aqk_live_v1_… python live/feed.py"""
import asyncio
import json
import os
import random
import time

from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus, WebSocketException

# Pick the instrument and channel here; AQ_FEED_URL overrides the whole address.
URL = os.environ.get("AQ_FEED_URL", "wss://feed.alphaquick.io/ws?symbol=BTC&channel=tob100")
KEY = os.environ.get("AQ_API_KEY") or exit("Set AQ_API_KEY to your API key (Settings -> API Keys on alphaquick.io).")
HEADERS = {"Authorization": f"Bearer {KEY}"}
GIVE_UP_AFTER = 300  # seconds: a 401 or 403 lasting this long is final


async def main():
    failures, refused_since = 0, None
    while True:
        bids, asks, fresh = {}, {}, False   # price -> volume, both kept as strings
        try:
            # max_size=None: a full-book snapshot can be larger than the 1 MiB default.
            async with connect(URL, additional_headers=HEADERS, max_size=None) as ws:
                async for raw in ws:
                    msg = json.loads(raw)
                    kind = msg.get("type")
                    if kind in ("snapshot", "delta"):
                        if kind == "snapshot":
                            bids.clear(); asks.clear()
                            fresh, failures, refused_since = True, 0, None
                        for row in msg["rows"]:
                            side = bids if row["dir"] == 0 else asks
                            if float(row["volume"]) == 0:
                                side.pop(row["price"], None)
                            else:
                                side[row["price"]] = row["volume"]
                        if fresh and bids and asks:
                            print(f"best bid {max(map(float, bids))}  best ask {min(map(float, asks))}")
                    elif kind == "gap" or (kind == "relay_status" and msg.get("event") == "source_disconnected"):
                        fresh = False   # stale until the next snapshot: do not act on it
                    # ignore every other type
        except InvalidStatus as error:      # the handshake was refused
            status = error.response.status_code
            print(f"feed: refused with HTTP {status}")
            if status in (401, 403):
                refused_since = refused_since or time.monotonic()
                if time.monotonic() - refused_since > GIVE_UP_AFTER:
                    raise SystemExit("feed: refused for 5 minutes; check the key and the subscription")
        except (OSError, asyncio.TimeoutError, WebSocketException, ValueError) as error:
            # Network errors, a broken handshake, a closed connection, a bad frame: reconnect.
            print(f"feed: connection lost ({error or type(error).__name__})")
        # Exponential backoff with full jitter: up to 1 s, 2 s, 4 s … 30 s.
        await asyncio.sleep(random.uniform(0, min(30, 2 ** failures)))
        failures += 1


asyncio.run(main())
