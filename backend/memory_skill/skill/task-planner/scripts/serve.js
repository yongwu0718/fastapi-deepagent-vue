// 本地服务器：托管 Vue 构建产物（app/dist）+ 数据持久化 API
// 启动：node scripts/serve.js → http://localhost:8734
// 数据读写：scripts/data/task-planner-data.json
// 开发模式：cd scripts/app && npm run dev（vite 5173，/api 代理到本服务）
const http = require('http');
const fs = require('fs');
const path = require('path');

const port = 8734;
const DATA_DIR = path.join(__dirname, 'data');
const DATA_FILE = path.join(DATA_DIR, 'task-planner-data.json');
const DIST_DIR = path.join(__dirname, 'app', 'dist');
const EMPTY = { version: 1, tasks: [], reviews: {}, days: {} };

// 确保数据目录与文件存在
fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(DATA_FILE)) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(EMPTY, null, 2), 'utf-8');
}

const hasDist = fs.existsSync(path.join(DIST_DIR, 'index.html'));

function readData() {
  try {
    const d = JSON.parse(fs.readFileSync(DATA_FILE, 'utf-8'));
    if (d && Array.isArray(d.tasks)) {
      return { version: 1, tasks: d.tasks, reviews: d.reviews || {}, days: d.days || {} };
    }
  } catch (e) {}
  return EMPTY;
}

function writeData(obj) {
  // 先写临时文件再重命名，避免写一半损坏
  const tmp = DATA_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2), 'utf-8');
  fs.renameSync(tmp, DATA_FILE);
}

function send(res, code, body, type) {
  res.writeHead(code, { 'Content-Type': type || 'application/json; charset=utf-8' });
  res.end(body);
}

http.createServer((req, res) => {
  const url = decodeURIComponent((req.url || '/').split('?')[0]);

  // ---- 数据 API ----
  if (url === '/api/data') {
    if (req.method === 'GET') {
      return send(res, 200, JSON.stringify(readData()));
    }
    if (req.method === 'POST') {
      let body = '';
      req.on('data', c => {
        body += c;
        if (body.length > 10 * 1024 * 1024) { // 10MB 上限
          send(res, 413, '{"ok":false,"error":"payload too large"}');
          req.destroy();
        }
      });
      req.on('end', () => {
        try {
          const data = JSON.parse(body);
          if (!data || !Array.isArray(data.tasks)) throw new Error('bad');
          writeData({ version: 1, tasks: data.tasks, reviews: data.reviews || {}, days: data.days || {} });
          console.log(`[${new Date().toLocaleTimeString()}] 已保存 ${data.tasks.length} 条任务 → data/task-planner-data.json`);
          send(res, 200, '{"ok":true}');
        } catch (e) {
          send(res, 400, '{"ok":false,"error":"invalid json"}');
        }
      });
      return;
    }
    return send(res, 405, '{"ok":false,"error":"method not allowed"}');
  }

  // ---- 静态文件（app/dist） ----
  if (!hasDist) {
    return send(res, 503, '前端未构建：请先执行 cd scripts/app && npm install && npm run build\n（或开发模式：npm run dev 后访问 http://localhost:5173）', 'text/plain; charset=utf-8');
  }
  let p = path.normalize(path.join(DIST_DIR, url));
  if (!p.startsWith(DIST_DIR)) return send(res, 403, 'forbidden', 'text/plain'); // 防目录穿越
  if (url === '/' || url.endsWith('/')) p = path.join(p, 'index.html');
  fs.readFile(p, (e, d) => {
    if (e) {
      // SPA 回退：未知路径返回 index.html
      return fs.readFile(path.join(DIST_DIR, 'index.html'), (e2, d2) => {
        if (e2) return send(res, 404, '404', 'text/plain');
        send(res, 200, d2, 'text/html; charset=utf-8');
      });
    }
    const type = p.endsWith('.html') ? 'text/html; charset=utf-8'
      : p.endsWith('.css') ? 'text/css; charset=utf-8'
      : p.endsWith('.js') ? 'text/javascript; charset=utf-8'
      : p.endsWith('.svg') ? 'image/svg+xml'
      : p.endsWith('.json') ? 'application/json; charset=utf-8'
      : 'application/octet-stream';
    send(res, 200, d, type);
  });
}).listen(port, () => console.log(`serving http://localhost:${port} · 静态目录: app/dist · 数据文件: data/task-planner-data.json`));
