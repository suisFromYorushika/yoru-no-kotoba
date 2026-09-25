"""catalog + lemmas + grammar + songs/*.json → data/data.json（网页用的汇总数据）。

- 只导出 catalog 里 done=true 的专辑。
- 重复版本（dup_of）不参与计数，避免同一首歌被算成两首。
- 词表只收出现在 ≥2 首歌里的词；语法点全部导出。
- 每个词/语法点附带出现位置 loc：{歌曲id: [[行号, 起, 止], ...]}，网页据此显示原句并高亮。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import _ok  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


def find_lemma(match, line):
    """返回该行中所有命中的 [起, 止]。"""
    spans = []
    toks = line["tok"]
    for alt in match:
        if isinstance(alt, str):
            spans += [t["i"] for t in toks if t["l"] == alt]
        elif isinstance(alt, dict):
            spans += [[m.start(), m.end()] for m in re.finditer(alt["re"], line["ja"])]
        else:
            n = len(alt)
            for i in range(len(toks) - n + 1):
                if all(_ok(toks[i + j], c) for j, c in enumerate(alt)):
                    spans.append([toks[i]["i"][0], toks[i + n - 1]["i"][1]])
    # 去重（不同写法规则命中同一位置时只算一次）
    uniq = sorted({tuple(s) for s in spans})
    out = []
    for s in uniq:
        if out and s[0] < out[-1][1]:
            continue
        out.append(list(s))
    return out


def collect(songs, finder):
    occ, loc = {}, {}
    for s in songs:
        hits = []
        for li, line in enumerate(s["lines"]):
            hits += [[li] + sp for sp in finder(line)]
        if hits:
            occ[s["id"]] = len(hits)
            loc[s["id"]] = hits
    return occ, loc


def build():
    cat = load("catalog.json")
    lemmas = load("lemmas.json")
    grammar = load("grammar.json")
    done = [a for a in cat["albums"] if a.get("done")]
    done_ids = {a["id"] for a in done}
    song_meta = [s for s in cat["songs"] if s["album"] in done_ids]
    songs = [load(f"songs/{s['id']}.json") for s in song_meta]
    counted = [s for s, m in zip(songs, song_meta) if "dup_of" not in m]

    vocab = []
    for lm in lemmas:
        occ, loc = collect(counted, lambda line: find_lemma(lm["match"], line))
        if len(occ) >= 2:
            vocab.append({"w": lm["w"], "k": lm["k"], "r": lm["r"], "m": lm["m"], "ex": lm["ex"],
                          "occ": occ, "loc": loc})
    vocab.sort(key=lambda v: (-len(v["occ"]), -sum(v["occ"].values())))

    gram = []
    for g in grammar:
        def finder(line, gid=g["id"]):
            return [h[1:] for h in line.get("gram", []) if h[0] == gid]
        occ, loc = collect(counted, finder)
        gram.append({"id": g["id"], "g": g["g"], "r": g["r"], "m": g["m"], "ex": g["ex"], "occ": occ, "loc": loc})

    return {
        "albums": [{"id": a["id"], "artist": a["band"], "ja": a["ja"], "zh": a["zh"], "year": a["year"],
                    "type": a["type"], "note": a["note"]} for a in done],
        "songs": [{k: m[k] for k in ("id", "album", "ja", "zh", "dup_of") if k in m} for m in song_meta],
        "lines": {s["id"]: [[l["ja"], l["zh"]] for l in s["lines"]] for s in songs},
        "vocab": vocab,
        "grammar": gram,
    }


def main():
    data = build()
    (ROOT / "data" / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
                                             encoding="utf-8")
    print(f"{len(data['albums'])} albums, {len(data['songs'])} songs, "
          f"{len(data['vocab'])} vocab, {len(data['grammar'])} grammar")


if __name__ == "__main__":
    main()
