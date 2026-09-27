// 云同步不能弄丢进度：在真浏览器里跑网页，用假的 Supabase 检查几种容易出错的情况。
//   npm test        （需要 npm install 和 npx playwright install chromium）
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { startServer, fakeCloud, newDevice, openTab, waitSynced, waitCloud, learnedIn, learn, syncNow, launch, WORDS } from "./helpers.mjs";

let server, browser;
before(async () => { server = await startServer(); browser = await launch(); });
after(async () => { await browser?.close(); await server?.close(); });

const [W1, W2, W3] = WORDS;

test("同一个浏览器开两个标签页：一个标签页学的词，另一个标签页同步时不会把它删掉", async () => {
  const cloud = fakeCloud();
  const dev = await newDevice(browser, cloud);
  const a = await openTab(dev, server.url);
  const b = await openTab(dev, server.url);

  await learn(a, W1);
  await waitCloud(cloud, r => r && r.learned.includes(W1), W1);
  await waitSynced(a);
  // 另一个标签页要能看到这个词（不用刷新）
  assert.ok((await learnedIn(b)).includes(W1), "标签页 B 没有看到标签页 A 学的词");
  // 另一个标签页同步（切回页面时会自动做）不能把它从云端删掉
  await syncNow(b);
  await waitSynced(b);
  assert.ok(cloud.row.learned.includes(W1), "标签页 B 同步后，A 学的词从云端消失了");
  assert.ok((await learnedIn(a)).includes(W1));
  assert.ok((await learnedIn(b)).includes(W1));

  // 在 B 里取消掌握，A 和云端都要跟着去掉
  await learn(b, W1, false);
  await waitCloud(cloud, r => r && !r.learned.includes(W1), "取消 " + W1);
  await waitSynced(b);
  assert.ok(!(await learnedIn(a)).includes(W1), "标签页 A 还留着 B 已取消的词");
  await syncNow(a);
  await waitSynced(a);
  assert.ok(!cloud.row.learned.includes(W1), "标签页 A 同步后，把 B 已取消的词又加回了云端");
  await dev.close();
});

test("两台设备交替学：各自学的词都留在云端，取消掌握也能传到另一台", async () => {
  const cloud = fakeCloud();
  const d1 = await newDevice(browser, cloud), d2 = await newDevice(browser, cloud);
  const p1 = await openTab(d1, server.url), p2 = await openTab(d2, server.url);

  await learn(p1, W1);
  await waitCloud(cloud, r => r && r.learned.includes(W1), W1);
  await learn(p2, W2);
  await waitCloud(cloud, r => r && r.learned.includes(W2), W2);
  await waitSynced(p1); await waitSynced(p2);
  assert.deepEqual(cloud.row.learned.filter(w => [W1, W2].includes(w)).sort(), [W1, W2].sort(), "两台设备的词没有都留在云端");

  await syncNow(p1); await waitSynced(p1);
  assert.ok((await learnedIn(p1)).includes(W2), "设备 1 没拿到设备 2 学的词");

  await learn(p1, W1, false);
  await waitCloud(cloud, r => r && !r.learned.includes(W1), "取消 " + W1);
  await waitSynced(p1);
  assert.ok(cloud.row.learned.includes(W2));
  await syncNow(p2); await waitSynced(p2);
  const l2 = await learnedIn(p2);
  assert.ok(!l2.includes(W1) && l2.includes(W2), "设备 2 没跟上：应该只剩 " + W2 + "，现在是 " + l2);
  await d1.close(); await d2.close();
});

test("云端已有进度、本机也有没登录时学的词：第一次同步是合并，两边都不丢", async () => {
  const cloud = fakeCloud();
  cloud.row = { v: 2, learned: [W1], srs: [], log: [] };
  const dev = await newDevice(browser, cloud);
  // 先把本机进度写好再打开网页（模拟没登录时学过的词）
  await dev.addInitScript(([k, w]) => { if (!localStorage.getItem(k)) localStorage.setItem(k, JSON.stringify({ [w]: true })); }, ["yorushika_learned_v1", W3]);
  const p = await openTab(dev, server.url);
  const l = await learnedIn(p);
  assert.ok(l.includes(W1) && l.includes(W3), "第一次同步没有合并：" + l);
  assert.ok(cloud.row.learned.includes(W1) && cloud.row.learned.includes(W3), "云端没有合并：" + cloud.row.learned);
  await dev.close();
});
