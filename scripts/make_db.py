"""data/*.json → local/kotoba.sqlite（查询用，随时可删可重建）。

用法：python scripts/make_db.py
然后：sqlite3 local/kotoba.sqlite   或用 DB Browser for SQLite 等工具打开。
示例查询见 docs/queries.sql。
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export import find_lemma  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "local" / "kotoba.sqlite"


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def main():
    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    cat = load("catalog.json")
    lemmas = load("lemmas.json")
    grammar = load("grammar.json")

    con.executemany("INSERT INTO bands VALUES (?,?,?)", [(b["id"], b["ja"], b["zh"]) for b in cat["bands"]])
    con.executemany("INSERT INTO albums VALUES (?,?,?,?,?,?,?,?)",
                    [(a["id"], a["band"], a["ja"], a["zh"], a["year"], a["type"], a["note"], int(a.get("done", False)))
                     for a in cat["albums"]])
    con.executemany("INSERT INTO songs VALUES (?,?,?,?,?,?)",
                    [(s["id"], s["album"], s.get("track"), s["ja"], s["zh"], s.get("dup_of")) for s in cat["songs"]])
    con.executemany("INSERT INTO entries VALUES (?,?,?,?,?,?,?)",
                    [(l["w"], l["k"], l["r"], l["m"], *(l.get("ex") or [None, None, None])) for l in lemmas])
    con.executemany("INSERT INTO grammar VALUES (?,?,?,?,?,?,?)",
                    [(g["id"], g["g"], g["r"], g["m"], *(g.get("ex") or [None, None, None])) for g in grammar])

    for s in cat["songs"]:
        song = load(f"songs/{s['id']}.json")
        sid = s["id"]
        for li, line in enumerate(song["lines"]):
            con.execute("INSERT INTO lines VALUES (?,?,?,?,?)", (sid, li, line["t"], line["ja"], line["zh"]))
            con.executemany("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                            [(sid, li, pi, t["s"], t["l"], t.get("k"), t.get("lk"), t["p"], t.get("p2"), t.get("f"),
                              t["i"][0], t["i"][1]) for pi, t in enumerate(line["tok"])])
            for g in line.get("gram", []):
                con.execute("INSERT INTO grammar_hits VALUES (?,?,?,?,?)", (g[0], sid, li, g[1], g[2]))
            for lm in lemmas:
                for a, b in find_lemma(lm["match"], line):
                    con.execute("INSERT INTO entry_hits VALUES (?,?,?,?,?)", (lm["w"], sid, li, a, b))
    con.commit()
    n = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("songs", "lines", "tokens", "entry_hits")}
    print(f"wrote {DB.relative_to(ROOT)}: {n}")


if __name__ == "__main__":
    main()
