# CLAUDE.md

这是通过 ヨルシカ / あたらよ 的歌词学日语的项目。先读 README.md 和 docs/（data-model.md、player.md、supabase.md）。

## 工作方式

- 在给这个会话指定的开发分支上改，改完开 PR 合并到 main，再把分支重置到最新的 main。main 更新后 GitHub Pages 自动发布。
- 改了 data/ 或 web/template.html 以后跑 `make all`（分词 → data.json → web/index.html），生成的文件一起提交。第一次先 `make setup`。

## 不能动的东西

- `data/lemmas.json` 的 `w` 字段不要改：学习进度（已掌握、复习记录、Supabase 云同步、备份）都以 `w` 为键，改了用户的进度就对不上了。
- localStorage 的 `yorushika_learned_v1` 不要改名、不要改格式。其它 `yoru_*_v1` 的键同样要兼容旧数据。

## 数据约定

- 歌名、专辑名的中文（catalog.json 的 `zh`）先用 QQ 音乐的译名，没有再用网易云音乐的；平台上只有英文或版本说明的才自己翻译。
- 仓库里修过的歌词只改 `lyrics/`，不要用歌词库覆盖（`make ingest` 默认不覆盖）。

## 密钥和密码

- 任何密钥、密码、token、登录凭证都不要写进仓库，也不要在对话里发给用户或让用户发过来。
- 播放器的访问密码、网易云登录凭证只存在用户浏览器的 `yoru_player_v1` 里；DNSPod、Supabase 后台的密钥由用户自己填在对应后台。`data/site.json` 里的 Supabase publishable key 是公开的，可以提交。

## 待办

- NAS 播放器的部署（issue #7）：按 docs/player.md 在用户家的 Unraid 上配置，云端会话连不到 NAS，只能由用户在本地操作；用户确认测试通过后关闭 issue。
