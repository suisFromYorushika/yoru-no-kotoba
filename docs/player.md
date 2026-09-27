# 网页内置播放器（接家里 NAS 上的网易云 API）

GitHub Pages 是纯静态网站，拿不到网易云的播放地址。播放器的做法是：在家里的 NAS 上跑一个网易云 API 服务 [api-enhanced](https://github.com/NeteaseCloudMusicApiEnhanced/api-enhanced)（npm 包 `@neteasecloudmusicapienhanced/api`，旧名 `@neteaseapireborn/api`；Docker 镜像 `moefurina/ncm-api`），网页通过它登录网易云、取播放地址。

NAS 在国内家庭宽带上，网易云会正常给播放地址；海外服务器常常只能拿到试听或者拿不到。

```
浏览器（GitHub Pages 上的网页）
  │  https://music.<域名>:8443/…?k=<访问密码>
  ▼
Nginx Proxy Manager（检查 k，不对就返回 403）
  ▼
ncm-api 容器 :3000  ──→  网易云
```

歌曲本身由浏览器直接从网易云的 CDN（`*.music.126.net`）下载，不经过 NAS。

网页这边已经做好（`web/template.html` 的「播放器」一节）：没填服务器时一切照旧，只有「去听」链接。

## 1. 容器

在 Unraid 里添加容器：

- 镜像：`moefurina/ncm-api:latest`
- 端口：容器的 `3000`，映射到 NAS 的一个内网端口就行，不要直接开到公网（公网只走下面的反向代理）
- 环境变量：

| 变量 | 值 | 作用 |
|---|---|---|
| `CORS_ALLOW_ORIGIN` | `https://suisfromyorushika.github.io` | 只允许这个网页跨域读取结果 |
| `ENABLE_GENERAL_UNBLOCK` | `false` | 有会员，只用网易云官方的播放地址，不去第三方音源找 |

`NETEASE_COOKIE` 可以不设，也可以设，二选一：

- **不设**：网易云登录在网页里做，登录凭证只存在各自的浏览器里，每台设备各登录一次。
- **设了**：每台设备只要填一次服务器地址和访问密码，不用再登录网易云。做法：
  1. 在家里网络下用电脑浏览器打开 `http://<NAS 内网 IP>:<上面映射的端口>/qrlogin.html`（api-enhanced 自带的扫码页），用手机网易云 App 扫码确认。这样专门给 NAS 开一份登录，和手机、电脑自己的登录互不影响。
  2. 开发者工具 → Application → Local Storage → 这个地址 → `cookie`，在值里找到 `MUSIC_U=` 开头的一段，复制到分号前为止。
  3. Unraid → Docker → ncm-api → Edit → Add another Path, Port, Variable… → Variable，Key 填 `NETEASE_COOKIE`，Value 填 `MUSIC_U=<那一长串>`。**开头的 `MUSIC_U=` 不能少**，只填那一长串是不生效的。Apply 后容器会重建。

  自己填，不要发给别人，也不要提交到仓库。本机没登录网易云的设备，网页会在请求里带 `cookie: null`，播放服务器就用这份；某台设备在网页里另外登录了，就用那台设备自己的。「我的」里会显示「用的是播放服务器上的网易云账号」。代价是：知道访问密码的人都能用这个会员账号；以后别对这份登录点「退出」或在网易云 App 里「下线其他设备」，否则它会失效；过期（一般几个月）后照上面再做一次。

  为什么要带 `null`：api-enhanced 会先把请求头里的 Cookie 当成登录凭证，没有也会塞一个空的，空的也算「给了」，于是不会去用 `NETEASE_COOKIE`（`server.js` 里 `Object.assign({}, { cookie: req.cookies }, req.query, req.body)`，`util/option.js` 里 `query.cookie || process.env.NETEASE_COOKIE`）。只有请求体里明确是 `null` 才会用它，而表单发不了 `null`，所以这种请求改用 JSON 发。

## 2. 反向代理和访问密码

在 Nginx Proxy Manager 里加一个 Proxy Host：

- Domain：`music.<域名>`，转发到 `http://<NAS 内网 IP>:<上面映射的端口>`
- SSL：用 DNS Challenge 申请的证书，打开 Force SSL
- Advanced → Custom Nginx Configuration：

```nginx
if ($arg_k != "换成你的访问密码") {
    return 403;
}
```

访问密码用一串随机字符（例如 `openssl rand -hex 16` 生成的）。它只填在网页的「我的 → 播放器」里，不要发给任何人，也不要提交到仓库。

## 3. 测试

在浏览器里打开：

- `https://music.<域名>:8443/login/status?k=<访问密码>` → 应该显示 `{"data":{"code":200,"account":null,"profile":null}}`
- 去掉 `?k=…` → 应该是 403
- 设了 `NETEASE_COOKIE` 的话，在 NAS 上直接请求容器（不经过反向代理，不用访问密码），`profile` 里应该是你的昵称。直接打开网址或者不带请求体的 `curl` 会显示没登录，这是正常的，原因见上面第 1 节：

  ```bash
  curl -s -X POST -H 'Content-Type: application/json' -d '{"cookie":null}' "http://localhost:<端口>/login/status?timestamp=$(date +%s)"
  ```

## 4. 在网页里用

1. 打开网页 →「我的」→「播放器（网易云音乐）」，填服务器地址（`https://music.<域名>:8443`）和访问密码 →「保存并测试」，看到「✓ 已连上」就好了。每台设备、每个浏览器各填一次。
2. 登录网易云：电脑上用「扫码登录网易云」，用手机上的网易云音乐 App 扫一扫；只有一台手机时用「手机验证码登录」。不登录也能播，但会员歌只有 30 秒试听。NAS 上设了 `NETEASE_COOKIE` 的话，这一步不用做。
3. 歌曲页：
   - 专辑页的「▶ 播放整张专辑」，每首歌展开后的「▶ 播放这首」；
   - 歌词对照里每句前面的「▶ 00:46」从这句开始播，正在唱的那句会高亮，并自动滚到屏幕中间（「我的」里可以关）；
   - 每句后面朗读按钮左边的「♪」只听这一句原唱：放到下一句开始（最长 12 秒）就停，停在这句开头，再点再听一遍；中途点了别的播放按钮就照常往下播。
4. 底部播放条：
   - 显示正在唱的那句（带注音）和中文，点句子里的词会弹出词卡；
   - 按钮：再听这句（这句刚开始时点，回到上一句）、下一句、单句循环、进度条、下一首、关闭；
   - 点歌名或封面，回到这首歌的歌词对照；
   - 切到闪卡、词表、语法、关系图时音乐不停；
   - 手机锁屏界面和耳机按钮也能暂停、切歌。
5. 音质：标准 / 极高（默认）/ 无损。无损是 FLAC，流量大。

## 数据和安全

- **存在哪**：设了 `NETEASE_COOKIE` 的话，那份网易云凭证在 NAS 的容器设置里。其余都在本机 `localStorage` 的 `yoru_player_v1`：服务器地址、访问密码、网易云登录凭证、音质设置、按歌名搜到的网易云歌曲 id。不进 Supabase 云同步，也不进「复制我的进度」。
- **怎么发**：请求都是 POST。平时发表单（跨域「简单请求」，不会触发预检）；本机没登录网易云时，查登录状态和拿播放地址这两种请求改发 JSON（`cookie: null`，让服务器用 `NETEASE_COOKIE`），浏览器会先发一个 OPTIONS 预检，网址里同样带着 `k`，反向代理照常检查。访问密码放在网址参数 `k` 里，给反向代理检查；网易云凭证、手机号、验证码放在请求体里，不会出现在服务器的访问日志里。
- **缓存**：api-enhanced 会按「网址 + Cookie 头」把结果缓存 2 分钟，不看请求体，所以和登录状态有关的请求都在网址里带了 `timestamp`。
- **清除**：「退出网易云」会让这份登录凭证在网易云那边也失效；「修改 → 清除这台设备上的播放器设置」会删掉这台设备上的地址、密码和凭证。
- `suisfromyorushika.github.io` 下的所有 Pages 网站共用同一份 `localStorage`。以后如果在这个账号下放别人写的网页，要记得这一点。

## 常见问题

| 现象 | 原因和办法 |
|---|---|
| 连不上播放服务器 | 地址少了 `https://` 或端口；访问密码不对（反向代理返回 403，浏览器只会报「连不上」）；容器没在运行；`CORS_ALLOW_ORIGIN` 填错 |
| 提示服务器地址要用 https | 网页是 https 的，浏览器不允许它去请求 http 地址 |
| 只能试听 30 秒 | 没登录、登录过期，或者账号不是会员。在「我的」里重新登录；用的是服务器上的账号时，换 NAS 上的 `NETEASE_COOKIE` |
| 设了 `NETEASE_COOKIE` 还是显示没登录 | Value 开头少了 `MUSIC_U=`；这份登录被退出或过期了；这台设备自己有一份过期的登录（「修改 → 清除这台设备上的播放器设置」后重新填地址和密码） |
| 拿不到播放地址 | 网易云没有这首歌的版权 |
| 扫码后提示要安全验证（8821 等） | 网易云的风控，过一会儿再试，或者换另一种登录方式 |
| 暂停很久后播放出错 | 播放地址 20 分钟后失效。网页会自动重新拿一次；还不行就点 ▶ |

## 本地测试

不用 NAS 也能在电脑上试：

```bash
docker run --rm -p 3000:3000 -e CORS_ALLOW_ORIGIN=http://localhost:8000 moefurina/ncm-api
cd web && python3 -m http.server 8000
```

打开 `http://localhost:8000`，播放器地址填 `http://localhost:3000`，访问密码留空。网页是 http 时，播放地址不会改成 https。
