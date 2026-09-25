"""整理专辑用的辅助查询（需先 make db）。

用法：python scripts/candidates.py tousaku            # 候选词：这张专辑里出现、还没被任何词条覆盖的实词，
                                                      # 在「已整理的专辑 + 这张」里出现 ≥2 首，附原句
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
# 这些语法点命中的词本身就是语法成分，不再列为候选
GRAMMAR_WORDS = ("mama", "you", "mitai", "hoshii", "teiru", "teiku", "teshimau", "tekureru", "temiru", "koto", "mono",
                 "sou", "kuseni", "tame", "teoku", "nitotte", "tabi", "sugiru", "teyaru", "tekudasai", "hazu", "toori", "teageru", "uchini", "temorau")


def candidates(con, albums, ph):
    # 统计范围 = 已整理（done）的专辑 + 这次要整理的专辑；候选词必须在这次的专辑里出现
    scope = sorted({r[0] for r in con.execute("SELECT id FROM albums WHERE done = 1")} | set(albums))
    sp = ",".join("?" * len(scope))
    # 被某个词条命中区间完全覆盖的词不算候选（多词组成的词条也能正确排除）；
    # 已经作为语法点统计的（こと/もの/よう/まま/みたい/〜ている 的 いる 等）也不算
    gids = ",".join(f"'{g}'" for g in GRAMMAR_WORDS)
    rows = con.execute(f"""
      WITH covered AS (SELECT DISTINCT t.song_id, t.line_idx, t.pos FROM tokens t JOIN entry_hits h
         ON h.song_id = t.song_id AND h.line_idx = t.line_idx AND t.c_start >= h.c_start AND t.c_end <= h.c_end
       UNION SELECT DISTINCT t.song_id, t.line_idx, t.pos FROM tokens t JOIN grammar_hits g
         ON g.song_id = t.song_id AND g.line_idx = t.line_idx AND t.c_start >= g.c_start AND t.c_end <= g.c_end
         AND g.grammar_id IN ({gids}))
      SELECT t.lemma, MAX(t.lemma_kana), t.pos1, COUNT(DISTINCT t.song_id) AS songs,
             COUNT(DISTINCT CASE WHEN s.album IN ({ph}) THEN t.song_id END) AS here, COUNT(*) AS total
      FROM tokens t JOIN counted_songs s ON s.id = t.song_id
      WHERE s.album IN ({sp}) AND t.pos1 IN ({','.join('?' * len(POS))}) AND t.lemma GLOB '*[^ -~]*'
        AND NOT EXISTS (SELECT 1 FROM covered c WHERE c.song_id = t.song_id AND c.line_idx = t.line_idx AND c.pos = t.pos)
      GROUP BY t.lemma, t.pos1 HAVING songs >= 2 AND here >= 1 ORDER BY songs DESC, total DESC""",
                       albums + scope + list(POS)).fetchall()
    print(f"{len(rows)} 个候选（统计范围：{', '.join(scope)}）")
    for lemma, kana, pos, songs, here, total in rows:
        print(f"\n## {lemma}  {kana}  {pos}  {songs} 首（本次 {here} 首）/ {total} 次")
        seen = set()
        # 先列这次专辑里的原句，再列已整理专辑里的
        for sid, ja, a, b, zh, k in con.execute(f"""
            SELECT t.song_id, l.ja, t.c_start, t.c_end, l.zh, t.kana FROM tokens t JOIN counted_songs s ON s.id = t.song_id
            JOIN lines l ON l.song_id = t.song_id AND l.idx = t.line_idx
            WHERE s.album IN ({sp}) AND t.lemma = ? AND t.pos1 = ?
            ORDER BY s.album NOT IN ({ph}), t.song_id, t.line_idx""", scope + [lemma, pos] + albums):
            if sid in seen:
                continue
            seen.add(sid)
            print(f"   {sid}: {ja[:a]}【{ja[a:b]}|{k}】{ja[b:]}  // {zh}")
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
