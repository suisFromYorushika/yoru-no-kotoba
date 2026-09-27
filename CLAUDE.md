# CLAUDE.md

这是通过 ヨルシカ / あたらよ 的歌词学日语的项目。先读 README.md 和 docs/（data-model.md、player.md、supabase.md）。

## 工作方式

- 在给这个会话指定的开发分支上改，改完开 PR 合并到 main，再把分支重置到最新的 main。main 更新后 GitHub Pages 自动发布。
- 改了 data/ 或 web/template.html 以后跑 `make all`（分词 → data.json → web/index.html），生成的文件一起提交。第一次先 `make setup`。
- PR 上会自动跑检查（.github/workflows/check.yml）：`scripts/check.py` 确认 `w` 一个没少、localStorage 键名还在，再跑 `make all` 确认生成的文件已经提交。本地也可以先跑 `.venv/bin/python scripts/check.py`。
- 改了云同步相关的代码要跑 `npm test`（第一次先 `npm install` 和 `npx playwright install chromium`）：`tests/sync.test.mjs` 在真浏览器里用假的 Supabase 检查两个标签页、两台设备、首次合并这几种情况不丢进度。PR 检查也会跑它。

## 不能动的东西

- `data/lemmas.json` 的 `w` 字段不要改：学习进度（已掌握、复习记录、Supabase 云同步、备份）都以 `w` 为键，改了用户的进度就对不上了。
- localStorage 的 `yorushika_learned_v1` 不要改名、不要改格式。其它 `yoru_*_v1` 的键同样要兼容旧数据。

## 数据约定

- 歌名、专辑名的中文（catalog.json 的 `zh`）先用 QQ 音乐的译名，没有再用网易云音乐的；平台上只有英文或版本说明的才自己翻译。
- 仓库里修过的歌词只改 `lyrics/`，不要用歌词库覆盖（`make ingest` 默认不覆盖）。

## 密钥和密码

- 任何密钥、密码、token、登录凭证都不要写进仓库，也不要在对话里发给用户或让用户发过来。
- 播放器的访问密码、网易云登录凭证只存在用户浏览器的 `yoru_player_v1` 里；DNSPod、Supabase 后台的密钥由用户自己填在对应后台。`data/site.json` 里的 Supabase publishable key 是公开的，可以提交。
