# yoru-no-kotoba · 夜の言葉

通过 ヨルシカ（夜鹿）和 あたらよ（可惜夜）的歌学日语：把每首歌拆成词，统计高频词和语法，生成闪卡网页。

## 使用

直接双击打开 `web/index.html`，不需要联网，也不需要启动服务。一共四个视图：闪卡、词表、语法、歌曲。展开「出现在哪些歌」可以看到这个词所在的歌词原句（高亮）和中文翻译。已掌握状态保存在浏览器的 `localStorage["yorushika_learned_v1"]` 里。

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
data/lemmas.json       整理过的词条：写法/假名/罗马音/中文/自编例句 + match（在分词结果里怎么找它）
data/grammar.json      语法点 + rule（正则或按分词匹配）
data/songs/sN.json     每首歌拆好的词：每行歌词含时间戳、中日文、词列表、语法命中位置
data/data.json         给网页用的汇总（脚本生成）
data/legacy/           v1 的数据，留作对照
web/template.html      网页模板；web/index.html 为生成的成品
db/schema.sql          SQLite 表结构；docs/queries.sql 为示例查询
scripts/               ingest → analyze → export → build，以及 make_db
```

## 流程

```bash
make setup     # 第一次：创建 .venv，安装 fugashi + unidic-lite
make ingest    # 从 ~/Documents/Gemini Spark/Lyrics 导入新歌（可用 LYRICS=路径 指定）
make all       # 分词 → 导出 data.json → 生成 web/index.html
make db        # 生成 local/kotoba.sqlite，用来做 SQL 组合查询
make cand ALBUM=tousaku    # 这张专辑还没收录的候选词（附原句），需先 make db
make audit ALBUM=tousaku   # 核对词条在这张专辑里命中的读音，抽查分词
```

## 词表规则

- 按「出现在几首歌里」排序，再按总次数排序；只收出现在 2 首及以上歌里的词。同一首歌的不同版本（`dup_of`）只算一次。
- 分档：核心 ≥10 首 / 高频 6–9 / 中频 3–5 / 基础 2。
- 每个词包含：写法、假名、罗马音、中文意思、自编例句（附罗马音和中文）、每首歌的出现次数和位置。
- 收词范围：出现在 ≥2 首歌里的实词（名词/动词/形容词/形容动词/副词/代词）都收，人名、地名也收；「こと」「もの」「よう」这类放进语法。
- 语法点单独统计，方法相同。

数据结构的详细说明见 [docs/data-model.md](docs/data-model.md)。
