# 数据结构

## 总览

```
~/Documents/Gemini Spark/Lyrics      （本地歌词库，原始来源）
        │ scripts/ingest.py    复制 .ja/.zh.lrc，NFC 文件名，更新 catalog.json
        ▼
lyrics/**.lrc  +  data/catalog.json
        │ scripts/analyze.py   解析 LRC → 按时间戳对齐中日行 → fugashi+UniDic 分词 → 匹配 grammar.json
        ▼
data/songs/sN.json                    （每首歌完整拆分，入库，便于 git diff）
        │ scripts/export.py    + lemmas.json / grammar.json，只取 done 专辑
        ▼
data/data.json  ──scripts/build.py──▶  web/index.html（GitHub Pages）+ web/artifact.html（claude.ai）
        │
        └ scripts/make_db.py ──▶ local/kotoba.sqlite （查询用，不入库）
```

**JSON 是数据的真身，SQLite 只是查询用的副本。** JSON 是文本文件，改了什么在 git 里一眼能看出来；SQLite 方便做组合查询。两者的内容完全一样，SQLite 随时可以删掉，再从 JSON 重新生成。

## data/catalog.json

```jsonc
{
  "bands":  [{"id": "yorushika", "ja": "ヨルシカ", "zh": "夜鹿"}],
  "albums": [{"id": "dakara", "band": "yorushika", "ja": "…", "zh": "…", "year": "2019.04",
              "type": "1st 全长专辑", "note": "一句背景介绍", "done": true, "dir": "yorushika/dakara"}],
  "songs":  [{"id": "s0", "album": "dakara", "ja": "藍二乗", "zh": "蓝二乘", "track": 2,
              "file": "yorushika/dakara/02.藍二乗",          // + .ja.lrc / .zh.lrc
              "dup_of": "s26"}]                               // 可选：同一首歌的另一个版本
}
```

- 歌曲 id：s0–s19 沿用 v1，其余按乐队 → 发行时间顺序编号（s20–s156）。
- 新专辑的 `note` 是从 `_album.md` 自动截取的第一句，整理这张专辑时再改写。
- `zh`（歌名、专辑名的中文）优先用 QQ 音乐上的译名，没有再用网易云音乐的；平台上只有英文或版本说明的保留自译。
- 专辑的 `short` 只给很长的名字（例：音辞）；`cover` 是 `web/covers/` 里的封面。
- 歌曲的 `links`：`{"qq": QQ 音乐 songmid, "ne": 网易云歌曲 id}`，网页据此直接跳到那首歌；没有的就用搜索链接。

## data/songs/sN.json

```jsonc
{"id": "s14", "album": "elma", "ja": "雨晴るる", "zh": "雨过天晴", "lines": [
  {"t": 21828, "ja": "日文行", "zh": "中文行",
   "tok": [{"s": "忘れ", "l": "忘れる", "k": "わすれ", "lk": "わすれる",
            "p": "動詞", "p2": "一般", "f": "連用形-一般", "i": [3, 5]}],
   "gram": [["mama", 6, 8]]}
]}
```

| 键 | 含义 |
|---|---|
| s | 原文写法 |
| l | 原形（UniDic lemma）。写法会被归一：想い出→思い出、わかる→分かる、辞める→止める |
| k / lk | 这个词的读音 / 原形的读音（平假名） |
| p / p2 | 词性大类 / 细类 |
| f | 活用形（只有会变形的词才有） |
| i | 在这一行日文里的字符位置 [起, 止) |

## data/readings.json（读音修正）

UniDic 有些读音在歌词里不对（何も 读成 なんも、君 读成 くん、明日 读成 あす…）。网页会在汉字上显示这些读音，所以分词时按这张表修正 `k`（只改读音，不改原形，不影响计数）：

```jsonc
{"tok": {"s": "何", "next": {"s": "[もかがを]"}}, "k": "なに", "note": "何も/何か/何が/何を 读 なに"}
```

`tok` 的写法和 match 条件相同（可以用 prev/next）；加 `"line": 正则` 表示只在这一行日文包含它时才改（例：`溜息を吐く` 的 吐く 读 つく，`息を吐く` 读 はく）。整理新专辑时用 `make audit` 看到可疑读音，就往这里加一条。

## data/data.json（网页用，自动生成）

- `albums` / `pending`：已整理 / 待整理的专辑，含简称 `short`（例：音辞）和封面 `cover`
- `vocab` / `grammar`：每项有 `occ`（每首歌的次数）、`loc`（每处出现的 [行号, 起, 止]）、`x`（自动挑的歌词例句 [歌曲id, 行号]）
- `lines[歌曲id]`：每行 `[日文, 中文, 分段, 时间戳毫秒]`。分段按"词 + 后面粘着的助动词/后缀/て"切开，每段是词的列表；
  词是 `[写法, 读音, 词性, 原形, 原形读音]`（末尾空项省略；读音只在含汉字或助词 は/へ 时给出），标点是字符串。
  网页据此注假名、生成罗马音、点词时显示原形和词性

## 云端进度

进度 JSON：`{"v": 2, "learned": [词…], "srs": [[词, 盒子, 到期日]…], "log": [[日, 复习, 新掌握, 新词, 测验]…]}`。
日期是本地时间的"自 1970 年起第几天"。两个版本存的格式相同，只有账号本人能读写：

- claude.ai 版：claude.ai 的数据库，文档 `data/users/<账号>/progress`
- GitHub Pages 版：Supabase 的 `progress` 表（`user_id`、`data`、`updated_at`），建表和权限见 [`db/supabase.sql`](../db/supabase.sql)，开启步骤见 [supabase.md](supabase.md)

## data/site.json

| 键 | 含义 |
|---|---|
| repo_url / pages_url / cloud_url | GitHub 仓库、Pages 网址、claude.ai 版网址 |
| supabase_url / supabase_key | Supabase 项目地址和 publishable key（公开的）；都填了 Pages 版才会显示登录 |
| supabase_github | `true` 时显示「用 GitHub 账号登录」（需要先在 Supabase 里配置 GitHub 登录） |
| supabase_google | `true` 时显示「用 Google 账号登录」（需要先在 Supabase 里配置 Google 登录） |

## data/lemmas.json（整理过的词条）

```jsonc
{"w": "思い出 / 想い出", "k": "おもいで", "r": "omoide", "m": "回忆",
 "ex": ["旅行はいい思い出になった。", "ryokou wa ii omoide ni natta", "旅行成了美好的回忆。"],
 "match": ["思い出"]}
```

`match` 写的是怎么在分词结果里找到这个词，可以列多条，满足任意一条就算：
- `"忘れる"`：原形等于它的词
- `[{"l": "神"}, {"l": "様"}]`：连续几个词依次满足条件（多词组成的词，例如 神様、このまま）
- `[{"l": "居る", "!prev": {"l": "て", "p": "助詞"}}]`：带前后文条件（见下），用来修正分词或排除语法用法
- `{"re": "仕方(が)?ない"}`：对整行日文用正则（兜底用）

常见的修正写法：

| 问题 | 写法 |
|---|---|
| 「知っている」的 いる 是语法（〜ている），不是「在」 | `{"l": "居る", "!prev": {"l": "て", "p": "助詞"}}`（行く/来る/見る/しまう/置く 同理） |
| 「相変わらず」被拆成 相 + 変わる + ず | 変わる 加 `"!prev": {"s": "相"}`，另建词条 `[{"s": "相"}, {"l": "変わる"}, {"l": "ず"}]` |
| 「頬を伝え花緑青」其实是 伝う 的命令形，被判成 伝える | 伝う 加 `[{"l": "伝える", "next": {"p": "名詞"}}]`，伝える 加 `"!next"` 同样条件 |
| 「八月」被拆成 八 + 月 | `[{"p2": "数詞"}, {"s": "月"}]` |
| 「こんな風に」的 風 读 ふう（…的样子），不是「风」 | `{"l": "風", "!prev": {"s": "[こそあど]んな"}}` |

整理新专辑时，用 `make cand ALBUM=<专辑id>` 看候选词和原句，用 `make audit ALBUM=<专辑id>` 核对每个词条命中的实际读音（读音对不上的往往是分词或匹配错了）。

## data/grammar.json

```jsonc
{"id": "tai", "g": "〜たい / 〜たくない", "r": "tai", "m": "想做…", "ex": ["海へ行きたい。", "umi e ikitai", "想去海边。"],
 "rule": {"tok": [{"l": "たい", "p": "助動詞"}]}}
```

`rule` 有三种写法：`{"re": 正则}`、`{"tok": [条件…]}`、`{"any": [rule…]}`（取并集）。
条件的键：`s` 写法正则、`k` 读音正则（平假名，已按 readings.json 修正）、`l` 原形（字符串或列表）、`p`/`p2` 词性（`"!x"` 表示排除）、`f` 活用形正则；
`prev`/`next` 前一个/后一个词必须满足的条件，`!prev`/`!next` 前一个/后一个词不能满足的条件。lemmas.json 的 `match` 用的是同一套条件。

词表里只放实词；「こと」「もの」「よう」「まま」「みたい」以及 〜ている / 〜ていく / 〜てしまう / 〜てくれる / 〜てみる / 〜きる 里的辅助动词都作为语法点统计。

## v1 → v2 的计数变化（前两张专辑）

v1 是用正则按字面匹配的，v2 改为按分词结果匹配。124 个词里有 87 个的计数和 v1 完全相同。差异主要是 v1 的误判被去掉了：

| 项目 | v1 | v2 | 原因 |
|---|---|---|---|
| 人 | 10 首 | 4 首 | v1 把「大人」「一人」「二人」也算进去了 |
| 見る | 13 首 | 10 首 | v1 把「見える」也算进去了 |
| 青 | 7 首 | 5 首 | v1 把「群青」「青々」「緑青」也算进去了 |
| 朝 | 2 首 | 0 首（移出词表） | v1 统计到的其实是「朝日」「朝焼け」 |
| 〜って | 125 次 | 31 次 | v1 把「言って」「待って」（动词变形）也算进去了 |
| 〜んだ | 96 次 | 76 次 | v1 把「読んだ」「選んだ」（过去式）也算进去了 |
| 〜なら | 16 首 | 13 首 | v1 把「さよなら」「ならない」也算进去了 |
| 〜たい | 18 首 | 14 首 | v1 把「みたい」也算进去了 |

## SQLite（local/kotoba.sqlite）

表结构见 [`db/schema.sql`](../db/schema.sql)，示例查询见 [`queries.sql`](queries.sql)：
- 全部歌曲里出现在最多首歌里的实词（包括还没整理成词条的）
- 某张专辑里出现 ≥3 首、还没整理成词条的候选词
- 两个词出现在同一句
- 每首歌的已掌握覆盖率
