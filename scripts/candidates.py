"""整理专辑用的辅助查询（需先 make db）。

用法：python scripts/candidates.py tousaku            # 候选词：≥2 首、实词、还没被任何词条覆盖，附原句
      python scripts/candidates.py tousaku --audit    # 核对：已有词条在这张专辑里命中的读音和首数
可以写多张专辑：python scripts/candidates.py dakara,elma
"""
import collections
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POS = ("名詞", "動詞", "形容詞", "形状詞", "副詞", "代名詞")


def candidates(con, albums, ph):
    # 被某个词条命中区间完全覆盖的词不算候选（多词组成的词条也能正确排除）
    rows = con.execute(f"""
      WITH covered AS (SELECT DISTINCT t.song_id, t.line_idx, t.pos FROM tokens t JOIN entry_hits h
         ON h.song_id = t.song_id AND h.line_idx = t.line_idx AND t.c_start >= h.c_start AND t.c_end <= h.c_end)
      SELECT t.lemma, MAX(t.lemma_kana), t.pos1, COUNT(DISTINCT t.song_id) AS songs, COUNT(*) AS total
      FROM tokens t JOIN counted_songs s ON s.id = t.song_id
      WHERE s.album IN ({ph}) AND t.pos1 IN ({','.join('?' * len(POS))})
        AND NOT EXISTS (SELECT 1 FROM covered c WHERE c.song_id = t.song_id AND c.line_idx = t.line_idx AND c.pos = t.pos)
      GROUP BY t.lemma, t.pos1 HAVING songs >= 2 ORDER BY songs DESC, total DESC""", albums + list(POS)).fetchall()
    print(f"{len(rows)} 个候选")
    for lemma, kana, pos, songs, total in rows:
        print(f"\n## {lemma}  {kana}  {pos}  {songs} 首 / {total} 次")
        seen = set()
        for sid, ja, a, b, zh in con.execute(f"""
            SELECT t.song_id, l.ja, t.c_start, t.c_end, l.zh FROM tokens t JOIN counted_songs s ON s.id = t.song_id
            JOIN lines l ON l.song_id = t.song_id AND l.idx = t.line_idx
            WHERE s.album IN ({ph}) AND t.lemma = ? AND t.pos1 = ? ORDER BY t.song_id, t.line_idx""",
                albums + [lemma, pos]):
            if sid in seen:
                continue
            seen.add(sid)
            print(f"   {sid}: {ja[:a]}【{ja[a:b]}】{ja[b:]}  // {zh}")
            if len(seen) >= 3:
                break


def audit(con, albums, ph):
    lemmas = json.loads((ROOT / "data" / "lemmas.json").read_text(encoding="utf-8"))
    for lm in lemmas:
        rows = con.execute(f"""
            SELECT h.song_id, t.kana FROM entry_hits h JOIN counted_songs s ON s.id = h.song_id
            JOIN tokens t ON t.song_id = h.song_id AND t.line_idx = h.line_idx
             AND t.c_start >= h.c_start AND t.c_end <= h.c_end
            WHERE s.album IN ({ph}) AND h.w = ?""", albums + [lm["w"]]).fetchall()
        if rows:
            kana = collections.Counter(k for _, k in rows)
            print(f"{lm['w']:<14} k={lm['k']:<14} {len({s for s, _ in rows})} 首  {dict(kana)}")


def main():
    albums = sys.argv[1].split(",")
    con = sqlite3.connect(ROOT / "local" / "kotoba.sqlite")
    ph = ",".join("?" * len(albums))
    (audit if "--audit" in sys.argv else candidates)(con, albums, ph)


if __name__ == "__main__":
    main()
