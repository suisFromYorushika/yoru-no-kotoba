-- yoru-no-kotoba 查询用数据库（SQLite）
-- 由 scripts/make_db.py 从 data/*.json 生成到 local/kotoba.sqlite，随时可删可重建，不入库。
-- 数据的"真身"是 JSON（便于 git 查看改动），这里只是为了方便用 SQL 做组合查询。

CREATE TABLE bands (
  id   TEXT PRIMARY KEY,           -- yorushika / atarayo
  ja   TEXT NOT NULL,
  zh   TEXT NOT NULL
);

CREATE TABLE albums (
  id    TEXT PRIMARY KEY,          -- dakara / elma / ...
  band  TEXT NOT NULL REFERENCES bands(id),
  ja    TEXT NOT NULL,
  zh    TEXT NOT NULL,
  year  TEXT,
  type  TEXT,
  note  TEXT,
  done  INTEGER NOT NULL DEFAULT 0 -- 1 = 已整理进网页
);

CREATE TABLE songs (
  id      TEXT PRIMARY KEY,        -- s0 …
  album   TEXT NOT NULL REFERENCES albums(id),
  track   INTEGER,
  ja      TEXT NOT NULL,
  zh      TEXT NOT NULL,
  dup_of  TEXT REFERENCES songs(id) -- 同一首歌的其他版本（统计时跳过）
);

CREATE TABLE lines (
  song_id TEXT NOT NULL REFERENCES songs(id),
  idx     INTEGER NOT NULL,        -- 行号（从 0 开始）
  t_ms    INTEGER,                 -- LRC 时间戳
  ja      TEXT NOT NULL,
  zh      TEXT,
  PRIMARY KEY (song_id, idx)
);

-- 分词结果：每个词一行
CREATE TABLE tokens (
  song_id  TEXT NOT NULL,
  line_idx INTEGER NOT NULL,
  pos      INTEGER NOT NULL,       -- 行内第几个词
  surface  TEXT NOT NULL,          -- 原文写法：忘れ
  lemma    TEXT NOT NULL,          -- 原形：忘れる
  kana     TEXT,                   -- 读音（平假名）
  lemma_kana TEXT,                 -- 原形读音
  pos1     TEXT,                   -- 词性大类：名詞/動詞/助詞…
  pos2     TEXT,
  cform    TEXT,                   -- 活用形
  c_start  INTEGER, c_end INTEGER, -- 行内字符位置
  PRIMARY KEY (song_id, line_idx, pos),
  FOREIGN KEY (song_id, line_idx) REFERENCES lines(song_id, idx)
);

-- 整理过的词条（有中文、例句），来自 data/lemmas.json
CREATE TABLE entries (
  w   TEXT PRIMARY KEY,            -- 写法（也是网页"已掌握"的键）
  kana TEXT, romaji TEXT, meaning TEXT,
  ex_ja TEXT, ex_romaji TEXT, ex_zh TEXT
);

-- 词条在歌词里的每一次出现（按 lemmas.json 的 match 规则算出）
CREATE TABLE entry_hits (
  w        TEXT NOT NULL REFERENCES entries(w),
  song_id  TEXT NOT NULL,
  line_idx INTEGER NOT NULL,
  c_start  INTEGER, c_end INTEGER
);

CREATE TABLE grammar (
  id TEXT PRIMARY KEY, pattern TEXT, romaji TEXT, meaning TEXT, ex_ja TEXT, ex_zh TEXT
);

CREATE TABLE grammar_hits (
  grammar_id TEXT NOT NULL REFERENCES grammar(id),
  song_id    TEXT NOT NULL,
  line_idx   INTEGER NOT NULL,
  c_start    INTEGER, c_end INTEGER
);

-- 已掌握的词（可从网页导出后导入，用来算覆盖率）
CREATE TABLE known (w TEXT PRIMARY KEY);

CREATE INDEX idx_tokens_lemma ON tokens(lemma);
CREATE INDEX idx_entry_hits_w ON entry_hits(w);
CREATE INDEX idx_entry_hits_song ON entry_hits(song_id);

-- 常用视图：参与统计的歌（排除重复版本）
CREATE VIEW counted_songs AS SELECT * FROM songs WHERE dup_of IS NULL;

-- 每个原形在各首歌的出现次数（全部词，不限于整理过的词条）
CREATE VIEW lemma_song_counts AS
  SELECT t.lemma, t.pos1, t.song_id, COUNT(*) AS n
  FROM tokens t JOIN counted_songs s ON s.id = t.song_id
  GROUP BY t.lemma, t.pos1, t.song_id;
