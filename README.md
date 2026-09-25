# yoru-no-kotoba · 夜の言葉

通过 ヨルシカ（夜鹿）和 あたらよ（可惜夜）的歌学日语：把每首歌拆成词，统计高频词和语法，生成闪卡网页。

## 使用

有两个网址，内容一样：

| 版本 | 网址 | 进度保存在哪 |
|---|---|---|
| GitHub Pages | https://suisfromyorushika.github.io/yoru-no-kotoba/ （main 分支更新后自动发布） | 本机浏览器 |
| claude.ai | https://claude.ai/artifact/52Y32vb5QvrzcKwEekrmNK | 登录 claude.ai 后自动存到账号，换设备也能接着学 |

也可以直接双击打开 `web/index.html`，离线可用。

- **闪卡**：正面是词、按音节排好的假名和罗马音；点一下翻面看中文意思和一句歌词例句。手机上左右滑动换词，电脑上用 ← → 和空格。
- **词表 / 语法**：按出现在几首歌里排序，展开能看歌词例句和全部原句。
- **歌曲**：按专辑折叠，带封面；每首歌可以展开完整的歌词对照。
- 所有歌词都在汉字上注假名，按词分段，每段下面标罗马音，再附中文翻译；三样都能在「设置」里单独关掉。
- 筛选框默认收起，只显示一行摘要。
- 本机的已掌握状态保存在 `localStorage["yorushika_learned_v1"]`；claude.ai 版登录后存到 `data/users/<账号>/progress`。「设置 → 备份进度」可以把进度复制出来，在另一个版本或设备上导入。

## 进度

| 乐队 | 专辑 | 歌词 | 分词 | 词表/网页 |
|---|---|---|---|---|
| ヨルシカ | だから僕は音楽を辞めた (2019) | ✅ | ✅ | ✅ |
| ヨルシカ | エルマ (2019) | ✅ | ✅ | ✅ |
| ヨルシカ | 其余 7 张 | ✅ | ✅ | ⏳ |
| あたらよ | 全部 7 张 | ✅ | ✅ | ⏳ |

歌词已全部入库（157 首），也都已自动分词。整理完的专辑要在 `data/catalog.json` 里标 `"done": true`。

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
scripts/               ingest → analyze → export → build，以及 make_db
```

## 流程

```bash
make setup     # 第一次：创建 .venv，安装 fugashi + unidic-lite
make ingest    # 从 ~/Documents/Gemini Spark/Lyrics 导入新歌（可用 LYRICS=路径 指定）
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
