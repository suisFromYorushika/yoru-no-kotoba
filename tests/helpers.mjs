// 同步测试的公用部分：起一个本地静态服务器（Supabase 地址换成假的），
// 用 Playwright 拦截所有发往假 Supabase 的请求，在内存里模拟「云端那一行」。
// 真正的 supabase-js 照常加载，登录状态靠预先写进 localStorage 的假凭证。
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WEB = path.join(ROOT, "web");
export const FAKE_URL = "https://fake.supabase.test";   // 不能是真项目：测试绝不碰真数据
const USER_ID = "00000000-0000-4000-8000-000000000001";
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json" };

// 和 scripts/build.py 一样：模板 + data.json + site.json → 网页；只是 Supabase 地址换成假的
function buildIndex() {
  const data = fs.readFileSync(path.join(ROOT, "data/data.json"), "utf8").trim().replace(/<\//g, "<\\/");
  const site = JSON.parse(fs.readFileSync(path.join(ROOT, "data/site.json"), "utf8"));
  site.supabase_url = FAKE_URL;
  site.supabase_key = "sb_publishable_test";
  const tpl = fs.readFileSync(path.join(WEB, "template.html"), "utf8");
  return tpl.replace("__DATA__", data).replace("__SITE__", JSON.stringify(site).replace(/<\//g, "<\\/"));
}

export async function startServer() {
  const index = buildIndex();
  const server = http.createServer((req, res) => {
    const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p === "/" || p === "/index.html") { res.writeHead(200, { "content-type": MIME[".html"] }); return res.end(index); }
    if (p === "/sw.js") { res.writeHead(404); return res.end(); }   // 测试里不要离线缓存
    const f = path.join(WEB, p);
    if (!f.startsWith(WEB) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "content-type": MIME[path.extname(f)] || "application/octet-stream" });
    fs.createReadStream(f).pipe(res);
  });
  await new Promise(ok => server.listen(0, "127.0.0.1", ok));
  return { url: `http://127.0.0.1:${server.address().port}/`, close: () => new Promise(ok => server.close(ok)) };
}

// 假 Supabase：cloud 就是 progress 表里这个账号的那一行（null = 还没有）
export function fakeCloud() {
  const cloud = { row: null, writes: 0 };
  cloud.route = async route => {
    const req = route.request(), u = new URL(req.url());
    if (u.pathname.startsWith("/rest/v1/progress")) {
      if (req.method() === "GET") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(cloud.row ? [{ data: cloud.row }] : []) });
      if (req.method() === "POST") {
        const body = JSON.parse(req.postData());
        cloud.row = (Array.isArray(body) ? body[0] : body).data;
        cloud.writes++;
        return route.fulfill({ status: 201, body: "" });
      }
    }
    if (u.pathname === "/auth/v1/user") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fakeUser()) });
    return route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
  };
  return cloud;
}

function fakeUser() { return { id: USER_ID, aud: "authenticated", role: "authenticated", email: "test@example.com", app_metadata: {}, user_metadata: {} }; }
function b64url(o) { return Buffer.from(JSON.stringify(o)).toString("base64url"); }
function fakeSession() {
  const exp = Math.floor(Date.now() / 1000) + 3600;
  const jwt = `${b64url({ alg: "HS256", typ: "JWT" })}.${b64url({ sub: USER_ID, aud: "authenticated", role: "authenticated", exp, iat: exp - 3600, email: "test@example.com" })}.${b64url("sig")}`;
  return { access_token: jwt, refresh_token: "fake-refresh", token_type: "bearer", expires_in: 3600, expires_at: exp, user: fakeUser() };
}

// 一个「设备」= 一个浏览器上下文（有自己的 localStorage），里面可以开多个标签页
export async function newDevice(browser, cloud) {
  const ctx = await browser.newContext();
  await ctx.route(FAKE_URL + "/**", cloud.route);
  const key = "sb-" + new URL(FAKE_URL).hostname.split(".")[0] + "-auth-token";
  const session = JSON.stringify(fakeSession());
  await ctx.addInitScript(([k, s]) => { if (!localStorage.getItem(k)) localStorage.setItem(k, s); }, [key, session]);
  return ctx;
}

export async function openTab(ctx, url) {
  const page = await ctx.newPage();
  page.on("pageerror", e => { throw e; });
  await page.goto(url);
  await waitSynced(page);
  return page;
}

export async function waitSynced(page) {
  await page.waitForFunction(() => syncState === "synced" && !dirty, null, { timeout: 15000 });
}

// 等到云端满足条件（比如某个词已经写上去了）
export async function waitCloud(cloud, pred, what) {
  const t0 = Date.now();
  while (!pred(cloud.row)) {
    if (Date.now() - t0 > 10000) throw new Error("云端一直没有：" + what + "，现在是 " + JSON.stringify(cloud.row));
    await new Promise(r => setTimeout(r, 100));
  }
}

export const learnedIn = page => page.evaluate(() => learnedWords());
export const learn = (page, w, v = true) => page.evaluate(([w, v]) => toggleLearned(w, v), [w, v]);
export const syncNow = page => page.evaluate(() => runSync());

export async function launch() {
  return chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined });
}
export const WORDS = (() => {
  const d = JSON.parse(fs.readFileSync(path.join(ROOT, "data/data.json"), "utf8"));
  return d.vocab.slice(0, 6).map(v => v.w);
})();
