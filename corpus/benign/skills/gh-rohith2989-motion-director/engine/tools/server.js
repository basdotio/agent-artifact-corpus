// Tiny static file server for the composition (ES modules and fonts need http, not file://). Serves the project
// root, so /node_modules/... (fonts, icons) and /comp/... resolve.
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".webp": "image/webp",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".gif": "image/gif",
  ".mp3": "audio/mpeg",
  ".wav": "audio/wav",
  ".mp4": "video/mp4",
};

function start(port = 0) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = decodeURIComponent(req.url.split("?")[0]);
      let file = path.join(ROOT, url);
      if (!file.startsWith(ROOT)) {
        res.writeHead(403);
        return res.end();
      }
      if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
      fs.readFile(file, (err, data) => {
        if (err) {
          res.writeHead(404);
          return res.end("404 " + url);
        }
        res.writeHead(200, {
          "Content-Type": TYPES[path.extname(file).toLowerCase()] || "application/octet-stream",
          "Cache-Control": "no-store",
          "Access-Control-Allow-Origin": "*",
        });
        res.end(data);
      });
    });
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

module.exports = { start, ROOT };

if (require.main === module) {
  const port = Number(process.argv[2] || 5177);
  start(port).then((s) => console.log(`serving ${ROOT} at http://127.0.0.1:${s.address().port}/comp/`));
}
