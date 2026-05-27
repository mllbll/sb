const http = require('http');
const crypto = require('crypto');

const PORT = 3001;
const AUTH_USER = process.env.AUTH_USER || 'admin';
const AUTH_PASSWORD = process.env.AUTH_PASSWORD || 'changeme';

http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method === 'POST' && req.url === '/api/auth/login') {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      try {
        const { login, password } = JSON.parse(body);
        if (login === AUTH_USER && password === AUTH_PASSWORD) {
          const token = crypto.randomBytes(32).toString('hex');
          res.writeHead(200);
          res.end(JSON.stringify({ token, user: { login, role: 'operator' } }));
        } else {
          res.writeHead(401);
          res.end(JSON.stringify({ error: 'invalid_credentials' }));
        }
      } catch {
        res.writeHead(400);
        res.end(JSON.stringify({ error: 'bad_request' }));
      }
    });
  } else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'not_found' }));
  }
}).listen(PORT, () => {
  console.log(`[auth] Listening on :${PORT}`);
  console.log(`[auth] User: ${AUTH_USER}`);
});
