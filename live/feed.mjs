// feed.mjs: stream one book from the AlphaQuick relay and keep it up to date.
// npm install, then: AQ_API_KEY=aqk_live_v1_… node feed.mjs (Node.js 18 or later)
import WebSocket from 'ws';

if (!process.env.AQ_API_KEY) {
  console.error('Set AQ_API_KEY to your API key (Settings -> API Keys on alphaquick.io).');
  process.exit(1);
}

// Pick the instrument and channel here; AQ_FEED_URL overrides the whole address.
const URL = process.env.AQ_FEED_URL ?? 'wss://feed.alphaquick.io/ws?symbol=BTC&channel=tob100';
const GIVE_UP_AFTER_MS = 5 * 60_000; // a 401 or 403 lasting this long is final
let failures = 0;
let refusedSince = null;

function connect() {
  const ws = new WebSocket(URL, { headers: { Authorization: `Bearer ${process.env.AQ_API_KEY}` } });
  const bids = new Map(); // price -> volume, both kept as strings
  const asks = new Map();
  let fresh = false; // true from a snapshot until the book can no longer be trusted

  ws.on('message', (data) => {
    const msg = JSON.parse(data);
    if (msg.type === 'snapshot' || msg.type === 'delta') {
      if (msg.type === 'snapshot') {
        bids.clear(); asks.clear();
        fresh = true; failures = 0; refusedSince = null;
      }
      for (const { dir, price, volume } of msg.rows) {
        const side = dir === 0 ? bids : asks;
        if (Number(volume) === 0) side.delete(price); else side.set(price, volume);
      }
      if (fresh && bids.size && asks.size) {
        const bestBid = Math.max(...[...bids.keys()].map(Number));
        const bestAsk = Math.min(...[...asks.keys()].map(Number));
        console.log(`best bid ${bestBid}  best ask ${bestAsk}`);
      }
    } else if (msg.type === 'gap' || (msg.type === 'relay_status' && msg.event === 'source_disconnected')) {
      fresh = false; // stale until the next snapshot: do not act on it
    }
    // ignore every other type
  });

  // Without an 'error' listener, Node exits when a handshake is refused.
  ws.on('error', (err) => {
    const status = Number(/Unexpected server response: (\d+)/.exec(err.message)?.[1]);
    if (status === 401 || status === 403) refusedSince ??= Date.now();
    console.error(`feed: ${err.message}`);
  });

  ws.on('close', () => {
    if (refusedSince && Date.now() - refusedSince > GIVE_UP_AFTER_MS) {
      console.error('feed: refused for 5 minutes; check the key and the subscription');
      return;
    }
    // Exponential backoff with full jitter: up to 1 s, 2 s, 4 s … 30 s.
    const delay = Math.random() * Math.min(30_000, 1000 * 2 ** failures++);
    setTimeout(connect, delay);
  });
}

connect();
