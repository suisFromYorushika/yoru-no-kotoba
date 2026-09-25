# 给 GitHub Pages 版开启登录和云端同步（Supabase）

GitHub Pages 是纯静态网站，自己存不了数据。这里用 [Supabase](https://supabase.com)：它提供账号登录和数据库，网页直接连它，不需要自己的服务器。

网页这边的代码已经写好（`web/template.html` 的「Supabase 账号」一节）。只要在 `data/site.json` 里填上项目地址和公开密钥，Pages 版的「我的」面板里就会出现登录框；不填就还是本机模式。

claude.ai 版不受影响，继续用 claude.ai 账号同步（claude.ai 不允许页面连外部服务器，所以那边用不了 Supabase）。两个版本的进度是分开存的，可以用「我的 → 备份进度」互相搬。

## 两种做法

**A. 让 Claude 帮你建（推荐）**：在 claude.ai 的「设置 → 连接器」里连上 **Supabase** 连接器，然后告诉 Claude。Claude 可以直接建项目、运行下面的建表 SQL、取回项目地址和公开密钥，并填好 `data/site.json`。下面第 4、5 步（登录方式和网址设置）连接器可能改不了，需要你在控制台里点几下。

**B. 自己在控制台操作**：按下面的步骤做，最后把第 6 步的两个值发给 Claude，或者自己填进 `data/site.json`。

## 步骤

1. **注册**：打开 https://supabase.com ，点 Start your project。可以直接用 GitHub 账号登录。
2. **建项目**：New project。
   - Name：`yoru-no-kotoba`（随意）
   - Database Password：随便设一个强密码记下来（网页用不到它）
   - Region：离你近的，例如 **Northeast Asia (Tokyo)** 或 **Southeast Asia (Singapore)**
   - 选免费的 Free plan
3. **建表**：左侧 **SQL Editor** → New query → 把仓库里 [`db/supabase.sql`](../db/supabase.sql) 的全部内容粘贴进去 → **Run**。
   它会建一张 `progress` 表（每个账号一行），并打开行级安全：每个人只能读写自己的那一行，没登录的人什么都读不到。重复运行也没关系。
4. **登录方式**：左侧 **Authentication → Sign In / Providers → Email**。
   - Email 保持开启。
   - 建议**关掉 Confirm email**：这样注册后直接就能登录，不用等确认邮件。免费版自带的发信服务只发给项目成员（也就是你自己）的邮箱，而且每小时只能发很少几封。
5. **网址设置**：左侧 **Authentication → URL Configuration**。
   - Site URL：`https://suisfromyorushika.github.io/yoru-no-kotoba/`
   - Redirect URLs：加上同一个地址。重设密码邮件、GitHub 登录完成后，会跳回这个地址。
6. **复制两个值**：左侧 **Project Settings → API Keys**（旧版控制台叫 API）。
   - **Project URL**：形如 `https://abcdefgh.supabase.co`
   - **Publishable key**：`sb_publishable_` 开头（旧项目叫 anon key，是一长串 `eyJ` 开头的字符）

   这两个值本来就是公开的，写进网页没有问题，数据靠第 3 步的行级安全保护。
   **不要**把 secret key / service_role key 发给任何人，也不要写进网页。
7. **填进网站**：把两个值填进 `data/site.json`：

   ```json
   "supabase_url": "https://abcdefgh.supabase.co",
   "supabase_key": "sb_publishable_xxxxxxxx",
   ```

   然后 `make build`，提交并合并到 main。GitHub Pages 会自动更新，打开网页 →「我的」→ 注册 → 登录。

### 可选：用 GitHub 账号登录

1. GitHub → Settings → Developer settings → **OAuth Apps** → New OAuth App
   - Homepage URL：`https://suisfromyorushika.github.io/yoru-no-kotoba/`
   - Authorization callback URL：`https://<你的项目>.supabase.co/auth/v1/callback`（在 Supabase 的 GitHub 登录设置页里也能看到这个地址）
2. 建好后复制 Client ID，再生成一个 Client secret。
3. Supabase → Authentication → Sign In / Providers → **GitHub**：打开，填入 Client ID 和 Client secret，保存。
4. 把 `data/site.json` 里的 `"supabase_github"` 改成 `true`，重新 `make build`，提交。登录框下面会出现「用 GitHub 账号登录」。

## 需要知道的限制

- **免费项目一周没人访问会被暂停**。数据不会丢，到 Supabase 控制台点一下 Restore 就恢复。只要每周至少打开一次网页，就不会暂停。
- 免费额度：数据库 500 MB、每月 5 万个活跃用户。一个人学习用，一年的进度也只有几十 KB。
- **忘记密码**：登录框里点「忘记密码」会发一封重设邮件（受上面的发信限制）。也可以在 Supabase 控制台 → Authentication → Users 里直接处理。

## 数据格式

`progress` 表每个账号一行：`user_id`（账号 id）、`data`（进度 JSON）、`updated_at`。`data` 的格式和 claude.ai 版相同，见 [data-model.md](data-model.md#云端进度claudeai-版)。

同步规则：

- 这台设备第一次登录：本机原有的进度和云端**合并**，不会丢。
- 以后：每次改动 0.8 秒后自动保存到云端。切回这个页面时，会从云端拉取别的设备的改动。
- 退出登录后，本机的进度还在；下次登录时再合并上去。
