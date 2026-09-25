-- 示例查询：先运行 python scripts/make_db.py，再 sqlite3 local/kotoba.sqlite < docs/queries.sql
.headers on
.mode column

-- 1. 全部 157 首歌里，出现在最多首歌里的实词（名词/动词/形容词…），不限于已整理的词条
SELECT lemma, lemma_kana, pos1, COUNT(DISTINCT song_id) AS songs, SUM(n) AS total
FROM (SELECT t.lemma, MAX(t.lemma_kana) AS lemma_kana, t.pos1, t.song_id, COUNT(*) AS n
      FROM tokens t JOIN counted_songs s ON s.id = t.song_id
      WHERE t.pos1 IN ('名詞','動詞','形容詞','形状詞','副詞','代名詞')
      GROUP BY t.lemma, t.pos1, t.song_id)
GROUP BY lemma, pos1 ORDER BY songs DESC, total DESC LIMIT 20;

-- 2. 某张专辑（例：盗作）里出现 ≥3 首、但还没有整理成词条的词 → 下一批要加的候选
SELECT t.lemma, t.pos1, COUNT(DISTINCT t.song_id) AS songs, COUNT(*) AS total
FROM tokens t JOIN counted_songs s ON s.id = t.song_id
WHERE s.album = 'tousaku' AND t.pos1 IN ('名詞','動詞','形容詞','形状詞','副詞')
  AND t.lemma NOT IN (SELECT DISTINCT e.lemma FROM tokens e JOIN entry_hits h
                      ON h.song_id = e.song_id AND h.line_idx = e.line_idx AND e.c_start = h.c_start)
GROUP BY t.lemma, t.pos1 HAVING songs >= 3 ORDER BY songs DESC, total DESC;

-- 3. 两个词出现在同一句：「君」和「夏」
SELECT s.ja AS song, l.ja AS line, l.zh
FROM entry_hits a JOIN entry_hits b ON a.song_id = b.song_id AND a.line_idx = b.line_idx
JOIN lines l ON l.song_id = a.song_id AND l.idx = a.line_idx JOIN songs s ON s.id = a.song_id
WHERE a.w = '君' AND b.w = '夏' GROUP BY a.song_id, a.line_idx LIMIT 10;

-- 4. 每首歌的"已掌握覆盖率"（known 表需先导入已掌握的词）
SELECT s.ja, ROUND(100.0 * SUM(h.w IN (SELECT w FROM known)) / COUNT(*), 1) AS pct
FROM entry_hits h JOIN counted_songs s ON s.id = h.song_id
GROUP BY h.song_id ORDER BY pct DESC LIMIT 10;
