// A stand-in for the relay, to test the live clients without a key: it refuses
// the first handshake with 401 (as right after a renewal), then streams a
// snapshot, deltas, a frame type the clients must ignore, a source_disconnected
// status and a fresh snapshot, and drops the second connection without a close.
import http from 'node:http';
import { createRequire } from 'node:module';

const require = createRequire(new URL('../live/', import.meta.url));
const { WebSocketServer } = require('ws');

const server = http.createServer();
const wss = new WebSocketServer({ noServer: true });
let handshakes = 0;
server.on('upgrade', (req, socket, head) => {
  handshakes += 1;
  if (req.headers.authorization !== 'Bearer aqk_test' || handshakes === 1) {
    socket.end('HTTP/1.1 401 Unauthorized\r\nContent-Length: 0\r\n\r\n');
    return;
  }
  wss.handleUpgrade(req, socket, head, (ws) => {
    const send = (frame) => ws.send(JSON.stringify(frame));
    send({ type: 'snapshot', symbol: 'BTC', rows: [{ dir: 0, price: '100.0', volume: '1' }, { dir: 0, price: '99.0', volume: '2' }, { dir: 1, price: '101.0', volume: '3' }], ts: Date.now() });
    send({ type: 'delta', symbol: 'BTC', rows: [{ dir: 0, price: '100.0', volume: '0' }, { dir: 1, price: '100.5', volume: '5' }], ts: Date.now() });
    send({ type: 'something_new', x: 1 });
    send({ type: 'relay_status', symbol: 'BTC', event: 'source_disconnected', detail: { source: 'B' }, ts: Date.now() });
    send({ type: 'delta', symbol: 'BTC', rows: [{ dir: 1, price: '100.6', volume: '1' }], ts: Date.now() }); // stale: not reported
    setTimeout(() => send({ type: 'snapshot', symbol: 'BTC', rows: [{ dir: 0, price: '98.0', volume: '1' }, { dir: 1, price: '103.0', volume: '1' }], ts: Date.now() }), 200);
    if (handshakes === 2) setTimeout(() => ws.terminate(), 500);
  });
});
server.listen(Number(process.env.PORT ?? 18777));
setTimeout(() => process.exit(0), Number(process.env.LIFETIME_MS ?? 6000));
