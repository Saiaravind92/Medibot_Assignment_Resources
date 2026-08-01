const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');

// Set NODE_ENV to development
const dev = process.env.NODE_ENV !== 'production';
const app = next({ dev, dir: '.' });
const handle = app.getRequestHandler();

console.log("Initializing Custom Next.js Server (Babel fallback enabled)...");
console.log("Preparing Next.js application...");

app.prepare().then(() => {
  createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  }).listen(3000, '0.0.0.0', (err) => {
    if (err) {
      console.error("Failed to start HTTP server:", err);
      process.exit(1);
    }
    console.log('> MediBot Frontend successfully running on http://localhost:3000');
  });
}).catch(err => {
  console.error("Next.js preparation crashed:", err);
  process.exit(1);
});
