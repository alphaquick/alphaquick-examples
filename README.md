# AlphaQuick examples

Ready-to-run scripts for [AlphaQuick](https://alphaquick.io) market data: the
recorded L2 depth & trades and Hyperliquid order log files, and the live feed.
Each script is short, commented and stands on its own.

Run with no arguments, a script downloads a free sample once and works on
it, so you can try everything before you subscribe. Give it a file of your own
to work on that instead.

```bash
git clone https://github.com/alphaquick/alphaquick-examples
cd alphaquick-examples
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt          # the alphaquick package, with pandas

python orderlog/book_at.py --at 00:15     # the order book of ZEC at 00:15 UTC, with its queues
```

Python 3.10 or later. The scripts use the
[alphaquick](https://github.com/alphaquick/alphaquick-python) package.

## L2 depth & trades

| Script | What it shows |
|---|---|
| [`l2/bars.py`](l2/bars.py) | One-second bars (or any length): best bid and ask, spread, volume by aggressor, VWAP and cumulative volume delta, saved as Parquet |
| [`l2/book_at.py`](l2/book_at.py) | The book at a moment of the day, with cumulative size and the spread in basis points |
| [`l2/continuity.py`](l2/continuity.py) | Where the recording started or restarted, from the file's `.continuity.jsonl` |

Default sample: Hyperliquid BTC, 1 November 2026, the whole day (9.1 MB).

## Hyperliquid order log

| Script | What it shows |
|---|---|
| [`orderlog/book_at.py`](orderlog/book_at.py) | The order-level book at a moment: each level's order count, who is at the front of the best queues, which accounts rest the most orders |
| [`orderlog/queue_position.py`](orderlog/queue_position.py) | One order's place in its queue, step by step, until it is filled or canceled |
| [`orderlog/follow_account.py`](orderlog/follow_account.py) | One account through the day: its order events, its fills as maker and taker, its position after each fill |
| [`orderlog/maker_taker.py`](orderlog/maker_taker.py) | The notional each account traded as maker and as taker, and its share of the day |
| [`orderlog/order_lifetimes.py`](orderlog/order_lifetimes.py) | How long orders rest before they are canceled or filled |
| [`orderlog/hip4_outcome.py`](orderlog/hip4_outcome.py) | A HIP-4 prediction market hour by hour: the market's probability of "Yes" and the mints and merges |

Default samples: Order-Log Replay's ZEC sample (the first 30 minutes of 14
October 2026, 4.8 MB), and for `hip4_outcome.py` the Fed's October 2026 rate
decision, "No change", both books, the whole of 23 October 2026 (0.8 MB).

Some output, from `python orderlog/queue_position.py`:

```
order 573619868440: bid 6.46 at 1220.3, account 0xf9109ada2f73c62e9889b45453065f0d99260a2d
  00:05:00.032311  7 orders ahead, 28.100 in size
  00:05:00.640776  6 orders ahead, 25.470 in size
  00:05:02.390101  5 orders ahead, 24.350 in size
  00:05:02.390101  4 orders ahead, 23.450 in size
  00:05:02.390101  3 orders ahead, 16.500 in size
  00:05:02.390101  2 orders ahead, 13.510 in size
  00:05:02.461857  canceled; filled 0 in all
```

## Live feed

[`live/feed.py`](live/feed.py) and [`live/feed.mjs`](live/feed.mjs) stream one
book from the AlphaQuick relay and keep it up to date. They connect with your
API key, rebuild the book from the snapshot and the deltas, stop trusting it
when the relay says it is stale, and reconnect with backoff. They also keep
retrying a `401` for a few minutes, because one follows each renewal of your
subscription.

```bash
pip install -r live/requirements.txt
AQ_API_KEY=aqk_live_v1_… python live/feed.py

cd live && npm install
AQ_API_KEY=aqk_live_v1_… node feed.mjs
```

The live feed needs a
[Fast Hyperliquid Live Connector](https://docs.alphaquick.io/guides/subscriptions)
subscription and an [API key](https://docs.alphaquick.io/guides/api-keys).
Change the instrument and channel in the `URL` line, or set `AQ_FEED_URL`.
[`tests/check_live.sh`](tests/check_live.sh) runs both clients against a stand-in
relay ([`tests/mock_relay.mjs`](tests/mock_relay.mjs)), with no key needed.

## Your own files

Pick instruments and dates in the [catalogue](https://alphaquick.io/data) and
download them with the script it gives you (see
[Downloading files](https://docs.alphaquick.io/data/downloading)). Then pass a
file to any script:

```bash
python orderlog/maker_taker.py data/20261101/BTC_HLC_20261101.bin.lz4
python l2/bars.py data/20261101/BTCUSDT_BINANCE_USDM_20261101.bin.lz4 --every 5s
```

## More

- [The alphaquick package](https://github.com/alphaquick/alphaquick-python):
  readers, books, pandas, and the `alphaquick` command line.
- [alphaquick-rust](https://github.com/alphaquick/alphaquick-rust): the same in Rust.
- [Documentation](https://docs.alphaquick.io/data/libraries) and the file
  formats: [L2](https://docs.alphaquick.io/data/l2-depth-trades),
  [order log](https://docs.alphaquick.io/data/hyperliquid-order-log).
- See a file without code: [Depth Replay](https://alphaquick.io/replay) and
  [Order-Log Replay](https://alphaquick.io/orderlog) run in your browser.

MIT licence.
