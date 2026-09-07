const http = require('http');

const LISTEN_PORT = process.env.PORT || 8080;
const TARGET_PORT = 8000;
const TARGET_HOST = '127.0.0.1';

const server = http.createServer((req, res) => {
  const options = {
    hostname: TARGET_HOST,
    port: TARGET_PORT,
    path: req.url,
    method: req.method,
    headers: {
      ...req.headers,
      host: `${TARGET_HOST}:${TARGET_PORT}`
    }
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on('error', (err) => {
    console.error(`[Proxy Error] ${err.message}`);
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Backend unreachable via proxy', details: err.message }));
  });

  req.pipe(proxyReq, { end: true });
});

server.listen(LISTEN_PORT, '0.0.0.0', () => {
  console.log(`[HealthWatch LAN Proxy] Listening on 0.0.0.0:${LISTEN_PORT} -> forwarding to ${TARGET_HOST}:${TARGET_PORT}`);
});
