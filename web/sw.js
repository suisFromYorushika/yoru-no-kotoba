// 夜の言葉的离线缓存（service worker）：装到手机桌面后，断网也能打开。
// - 网页本身：先联网取最新版；断网或 4 秒没有响应时，用上次缓存的版本。联网时总是最新的，发布新版不用等缓存过期。
// - 本网站的其它文件（封面、supabase-js、星空图和它的数据、图标）：先用缓存，同时在后台更新。
// - Google 字体：缓存下来，断网时也能显示明朝体。
// - 其它跨域请求（Supabase 登录和同步、网易云播放）不经过这里，照常联网。
// 想清空所有人的旧缓存时，改 CACHE 的名字。
const CACHE = "yoru-v1";
const PRECACHE = ["./", "manifest.webmanifest", "icons/icon.svg", "icons/icon-192.png", "icons/icon-512.png"];
const PAGE_TIMEOUT = 4000;
const SCOPE = new URL(self.registration.scope).pathname;

self.addEventListener("install", e => {
  // 单个文件缓存失败不影响安装，用到时再缓存
  e.waitUntil(caches.open(CACHE)
    .then(c => Promise.all(PRECACHE.map(u => c.add(u).catch(() => {}))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || req.headers.has("range")) return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    if (!url.pathname.startsWith(SCOPE)) return;
    e.respondWith(req.mode === "navigate" ? page(req, e) : asset(req, e));
  } else if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    e.respondWith(asset(req, e));
  }
});

// 网页的缓存键：去掉登录回跳带的 ?code= 之类的参数；index.html 和它所在的目录算同一页
function pageKey(req) {
  const u = new URL(req.url);
  u.search = "";
  u.hash = "";
  if (u.pathname.endsWith("/index.html")) u.pathname = u.pathname.slice(0, -"index.html".length);
  return u.href;
}

async function page(req, e) {
  const key = pageKey(req), net = fetch(req);
  // 先复制一份放进缓存（要在浏览器读取正文之前复制），网页本身不等缓存写完
  e.waitUntil(net.then(res => {
    if (!res.ok) return;
    const copy = res.clone();
    return caches.open(CACHE).then(c => c.put(key, copy));
  }).catch(() => {}));
  try {
    return await Promise.race([net, new Promise((_, no) => setTimeout(() => no(new Error("timeout")), PAGE_TIMEOUT))]);
  } catch (err) {
    return (await caches.match(key)) || net;   // 没有缓存：继续等网络
  }
}

async function asset(req, e) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(req);
  const net = fetch(req);
  e.waitUntil(net.then(res => {
    if (res.ok || res.type === "opaque") return cache.put(req, res.clone());
  }).catch(() => {}));
  return hit || net;
}
