# yoru-no-kotoba · 夜の言葉

通过 ヨルシカ（夜鹿）和 あたらよ（可惜夜）的歌学日语：把每首歌拆成词，统计高频词和语法，生成闪卡网页。

## 使用

有两个网址，内容一样：

| 版本 | 网址 | 进度保存在哪 |
|---|---|---|
| GitHub Pages | https://suisfromyorushika.github.io/yoru-no-kotoba/ （main 分支更新后自动发布） | 本机浏览器；配置 Supabase 后可以注册登录、云端同步（见 [docs/supabase.md](docs/supabase.md)） |
| claude.ai | https://claude.ai/artifact/52Y32vb5QvrzcKwEekrmNK | 登录 claude.ai 后自动存到账号，换设备也能接着学 |

也可以直接双击打开 `web/index.html`，离线可用。

- **闪卡**有三种模式：
  - **浏览**：按频率一张张看，手机上左右滑动换词。
  - **复习**：间隔重复。每张卡选「忘了 / 模糊 / 记得」，记得的词隔 1、2、4、7、15… 天再出现，到 15 天间隔自动算已掌握；每天的新词数量可以在「我的」里调。
  - **测验**：看中文选日文、看日文选中文、歌词填空；答错的词自动加入当天的复习。
- **词表 / 语法**：按出现在几首歌里排序，展开能看歌词例句和全部原句。搜索框支持汉字、假名、罗马音和中文，也会列出包含这个词的歌词。
- **歌曲**：顶部推荐「下一首听什么」（按你已认识的词算覆盖率）；专辑可折叠、带封面；每首歌有 QQ 音乐 / 网易云 / Spotify / Apple Music / YouTube 链接和完整歌词对照。
- 所有歌词都在汉字上注假名、按词分段、每段下标罗马音，附中文翻译和 LRC 时间；**点任意一个词**会弹出词卡（词表词显示意思，助词助动词显示用法说明，还有原形、词性和相关语法点）。
- 词、例句和每行歌词都有朗读按钮（用设备自带的日语语音，不需要联网服务）。
- 「我的」面板：账号同步状态、学习记录（今天复习数、新掌握、连续天数、最近 14 天）、显示和朗读设置、进度备份。
- 进度保存在本机 `localStorage`（`yorushika_learned_v1` 已掌握、`yoru_srs_v1` 复习记录、`yoru_log_v1` 每日记录）；claude.ai 版登录后存到 claude.ai 账号，GitHub Pages 版登录后存到 Supabase。两边分开存，「我的 → 备份进度」可以在两个版本或设备之间搬运进度。
- 歌名和专辑名的中文译名取自 QQ 音乐（优先）和网易云音乐。

## 进度

| 乐队 | 专辑 | 词表/网页 |
|---|---|---|
| ヨルシカ | 全部 8 张专辑 + 单曲与合作曲 | ✅ |
| あたらよ | 全部 7 张 | ✅ |

157 首歌全部整理完：词表 1141 个词（核心 213 / 高频 160 / 中频 373 / 基础 395），语法点 43 个。整理完的专辑在 `data/catalog.json` 里标 `"done": true`。

歌词都和网易云音乐上的版本逐首比对过（`盗作`、单曲与合作曲、`優しいエイプリルフール (demo)` 原来的歌词文件有误，已换成正确歌词）。

## 目录

```
lyrics/<乐队>/<专辑>/NN.曲名.ja.lrc / .zh.lrc   歌词原文（NFC 文件名）；_album.md 为专辑背景
data/catalog.json      乐队、专辑、歌曲元数据（id、中日文名、年份、类型、介绍、done）
data/lemmas.json       整理过的词条：写法/假名/罗马音/中文 + match（在分词结果里怎么找它）
data/readings.json     读音修正表（UniDic 读错的地方，例如 何も→なにも、詩→うた）
data/site.json         网址配置（GitHub 仓库、Pages、claude.ai 版）
data/grammar.json      语法点 + rule（正则或按分词匹配）
data/songs/sN.json     每首歌拆好的词：每行歌词含时间戳、中日文、词列表、语法命中位置
data/data.json         给网页用的汇总（脚本生成）
data/legacy/           v1 的数据，留作对照
web/template.html      网页模板；web/index.html 为生成的成品，web/artifact.html 是发布到 claude.ai 的版本（不入库）
web/covers/            专辑封面缩略图
db/schema.sql          SQLite 表结构；docs/queries.sql 为示例查询
db/supabase.sql        Supabase 建表和权限（GitHub Pages 版的云端进度）
web/vendor/            第三方文件（supabase-js）
scripts/               ingest → analyze → export → build，以及 make_db
```

## 流程

```bash
make setup     # 第一次：创建 .venv，安装 fugashi + unidic-lite
make ingest    # 从 ~/Documents/Gemini Spark/Lyrics 导入新歌（可用 LYRICS=路径 指定）
               # 仓库里改过的歌词默认不覆盖；要用歌词库的版本覆盖：make ingest FORCE=1
make all       # 分词 → 导出 data.json → 生成 web/index.html 和 web/artifact.html
make db        # 生成 local/kotoba.sqlite，用来做 SQL 组合查询
make cand ALBUM=tousaku    # 这张专辑还没收录的候选词（附原句），需先 make db
make audit ALBUM=tousaku   # 核对词条在这张专辑里命中的读音，抽查分词
```

## 词表规则

- 按「出现在几首歌里」排序，再按总次数排序；只收出现在 2 首及以上歌里的词。同一首歌的不同版本（`dup_of`）只算一次。
- 分档：核心 ≥10 首 / 高频 6–9 / 中频 3–5 / 基础 2。
- 每个词包含：写法、假名、罗马音、中文意思、每首歌的出现次数和位置。例句直接取自歌词（导出时自动挑一句有中文翻译、长度适中的），不再自编；lemmas.json 里旧的自编例句 `ex` 保留但网页不显示。
- 收词范围：出现在 ≥2 首歌里的实词（名词/动词/形容词/形容动词/副词/代词）都收，人名、地名也收；「こと」「もの」「よう」这类放进语法。
- 语法点单独统计，方法相同。

数据结构的详细说明见 [docs/data-model.md](docs/data-model.md)。
