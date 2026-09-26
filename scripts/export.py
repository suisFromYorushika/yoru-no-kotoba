"""catalog + lemmas + grammar + songs/*.json → data/data.json（网页用的汇总数据）。

- 只导出 catalog 里 done=true 的专辑。
- 重复版本（dup_of）不参与计数，避免同一首歌被算成两首。
- 词表只收出现在 ≥2 首歌里的词；语法点全部导出。
- 每个词/语法点附带出现位置 loc：{歌曲id: [[行号, 起, 止], ...]}，网页据此显示原句并高亮；
  x = [歌曲id, 行号] 是从歌词里自动挑的例句（优先有中文翻译、长度适中的句子）。
- 每行歌词：[日文, 中文, 分段, 时间戳毫秒]。分段是按"词+后面粘着的助动词/后缀"切开的列表，
  每段由若干词组成；词见 encode_tok（标点是字符串）。网页据此注假名、标罗马音、点词查看原形和词性。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import seq_spans  # noqa: E402

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
            spans += seq_spans(alt, toks)
    # 去重（不同写法规则命中同一位置时只算一次）
    uniq = sorted({tuple(s) for s in spans})
    out = []
    for s in uniq:
        if out and s[0] < out[-1][1]:
            continue
        out.append(list(s))
    return out


KANJI = re.compile(r"[\u3400-\u9fff々〆ヶ]")


def attaches(t, prev):
    """这个词是否粘在前一个词后面（同属一段）：助动词（だ/です 除外）、后缀、て/で/ば，以及前缀后面的词。"""
    if prev is None or prev["p"] in ("補助記号", "空白") or t["p"] in ("補助記号", "空白"):
        return False
    if prev["p"] == "接頭辞":
        return True
    if t["p"] == "助動詞":
        return t["l"] not in ("だ", "です")  # だろう/です 这类判断词单独成段：shiteru darou
    if t["p"] == "接尾辞":
        return True
    return t["p"] == "助詞" and t.get("p2") == "接続助詞" and t["s"] in ("て", "で", "ば", "ちゃ", "じゃ")


POS = {"名詞": "n", "動詞": "v", "形容詞": "a", "形状詞": "na", "副詞": "adv", "代名詞": "pr", "助詞": "p",
       "助動詞": "aux", "接尾辞": "suf", "接頭辞": "pre", "接続詞": "cj", "連体詞": "adn", "感動詞": "int"}


def encode_tok(t):
    """词 → [写法, 读音, 词性, 原形, 原形读音]，末尾的空项省略。
    读音只在含汉字（或助词 は/へ）时给出，否则读音就是写法；原形只在和写法不同时给出。"""
    if t["p"] in ("補助記号", "空白"):
        return t["s"]
    if t.get("k") and KANJI.search(t["s"]):
        k = t["k"]
    elif t["p"] == "助詞" and t["s"] in ("は", "へ"):
        k = {"は": "わ", "へ": "え"}[t["s"]]
    else:
        k = ""
    out = [t["s"], k, POS.get(t["p"], "")]
    if t["l"] != t["s"]:
        out += [t["l"], t.get("lk", "") if KANJI.search(t["l"]) else ""]
    while out and out[-1] == "":
        out.pop()
    return out[0] if len(out) == 1 else out


def segments(line):
    """一行歌词 → 分段列表；词之间的空白单独成段，保证各段拼起来就是原文。"""
    segs, cur, prev = [], 0, None
    for t in line["tok"]:
        a, b = t["i"]
        if a > cur:
            segs.append([line["ja"][cur:a]])
            prev = None
        if attaches(t, prev) and segs:
            segs[-1].append(encode_tok(t))
        else:
            segs.append([encode_tok(t)])
        cur, prev = b, t
    if cur < len(line["ja"]):
        segs.append([line["ja"][cur:]])
    return segs


def pick_example(loc, songs_by_id, order):
    """从出现位置里挑一句做例句：有中文翻译、8–20 字的优先，再按出现次数多的歌、歌曲顺序。"""
    best = None
    for sid, hits in loc.items():
        lines = songs_by_id[sid]["lines"]
        for li, *_ in hits:
            ja, zh = lines[li]["ja"], lines[li]["zh"]
            n = len(ja)
            key = (not zh, max(0, n - 20) + max(0, 8 - n), -len(hits), order[sid], li)
            if best is None or key < best[0]:
                best = (key, [sid, li])
    return best[1] if best else None


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
    by_id = {s["id"]: s for s in songs}
    order = {m["id"]: i for i, m in enumerate(song_meta)}

    vocab = []
    for lm in lemmas:
        occ, loc = collect(counted, lambda line: find_lemma(lm["match"], line))
        if len(occ) >= 2:
            vocab.append({"w": lm["w"], "k": lm["k"], "r": lm["r"], "m": lm["m"],
                          "occ": occ, "loc": loc, "x": pick_example(loc, by_id, order)})
    vocab.sort(key=lambda v: (-len(v["occ"]), -sum(v["occ"].values())))

    gram = []
    for g in grammar:
        def finder(line, gid=g["id"]):
            return [h[1:] for h in line.get("gram", []) if h[0] == gid]
        occ, loc = collect(counted, finder)
        gram.append({"id": g["id"], "g": g["g"], "r": g["r"], "m": g["m"], "occ": occ, "loc": loc,
                     "x": pick_example(loc, by_id, order)})

    album_keys = ("id", "band", "ja", "zh", "short", "year", "type", "note", "cover", "badge")
    return {
        "albums": [{("artist" if k == "band" else k): a[k] for k in album_keys if k in a} for a in done],
        "pending": [{k: a[k] for k in ("id", "band", "ja", "zh", "short", "year", "cover") if k in a}
                    for a in cat["albums"] if not a.get("done")],
        "bands": cat["bands"],
        "songs": [{k: m[k] for k in ("id", "album", "track", "ja", "zh", "dup_of", "links") if k in m} for m in song_meta],
        "lines": {s["id"]: [[l["ja"], l["zh"], segments(l), l["t"]] for l in s["lines"]] for s in songs},
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
