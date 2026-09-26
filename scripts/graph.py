"""data/data.json → web/demos/graph.json：关系图演示用的数据。

- 节点：词表里的每个词（写法、读音、意思、出现在几首歌、属于哪个乐队、词群）
- 连线：两个词在同一句歌词里一起出现的次数。强度 = 次数 / √(两个词各自出现的句数)，
  压低「君」「僕」这种到处都有的词；每个词只保留最强的 6 条，全图保留 2 次以上的
- 每条线附上一起出现的歌词（最多 20 句，带两个词的位置），点线时直接显示
- 词群：按连线强度用 Louvain 算法分群（最多 10 个），以群里出现最多的 3 个词命名
- 位置：固定种子的随机初始位置，演示页里由各个库自己排布

用法：.venv/bin/python scripts/graph.py（需要 networkx）
"""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parent.parent
TOP_K = 6
REFS = 20   # 每条线最多带几句一起出现的歌词


def reading(segs):
    """一行歌词的读音：每段（词 + 粘着的词尾）连在一起，段之间用空格隔开；标点原样保留。"""
    out = []
    for seg in segs:
        r = "".join(t if isinstance(t, str) else (t[1] if len(t) > 1 and t[1] else t[0]) for t in seg)
        if r.strip():
            out.append(r.strip())
    return " ".join(out)


def main():
    data = json.loads((ROOT / "data" / "data.json").read_text(encoding="utf-8"))
    songs = {s["id"]: s for s in data["songs"]}
    albums = {a["id"]: a for a in data["albums"]}
    vocab = data["vocab"]

    # 每句歌词里有哪些词、每个词在这句里的位置
    line_words = defaultdict(dict)          # "sid|li" → {词序号: [[起, 止]…]}
    for i, v in enumerate(vocab):
        for sid, hits in v["loc"].items():
            for li, a, b in hits:
                line_words[f"{sid}|{li}"].setdefault(i, []).append([a, b])
    n_lines = defaultdict(int)
    for words in line_words.values():
        for i in words:
            n_lines[i] += 1

    pair = defaultdict(list)                 # (a, b) → [句子…]
    for key, words in line_words.items():
        ids = sorted(words)
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                pair[ids[x], ids[y]].append(key)

    scored = {}
    for (a, b), keys in pair.items():
        if len(keys) >= 2:
            scored[a, b] = len(keys) / math.sqrt(n_lines[a] * n_lines[b])
    best = defaultdict(list)
    for (a, b), s in scored.items():
        best[a].append((s, b))
        best[b].append((s, a))
    keep = set()
    for a, lst in best.items():
        for s, b in sorted(lst, reverse=True)[:TOP_K]:
            keep.add((min(a, b), max(a, b)))

    lines_out, edges = {}, []
    for a, b in sorted(keep):
        keys = pair[a, b]
        # 例句：优先挑有中文翻译、长度适中的句子
        keys = sorted(keys, key=lambda k: (not data["lines"][k.split("|")[0]][int(k.split("|")[1])][1],
                                           abs(len(data["lines"][k.split("|")[0]][int(k.split("|")[1])][0]) - 18)))
        # 同一首歌里一模一样的句子（副歌重复）只留一句，记下唱了几遍
        uniq = {}
        for k in keys:
            sid, li = k.split("|")
            uniq.setdefault((sid, data["lines"][sid][int(li)][0]), []).append(k)
        refs = []
        for ks in list(uniq.values())[:REFS]:
            k = ks[0]
            sid, li = k.split("|")
            if k not in lines_out:
                ja, zh = data["lines"][sid][int(li)][:2]
                s = songs[sid]
                lines_out[k] = [ja, zh, s["ja"], albums[s["album"]].get("short") or albums[s["album"]]["ja"],
                                reading(data["lines"][sid][int(li)][2])]
            refs.append([k, line_words[k][a], line_words[k][b], len(ks)])
        edges.append({"s": a, "t": b, "n": len(pair[a, b]), "w": round(scored[a, b], 4), "refs": refs})

    g = nx.Graph()
    g.add_nodes_from(range(len(vocab)))
    for e in edges:
        g.add_edge(e["s"], e["t"], weight=e["w"])
    comms = nx.community.louvain_communities(g, weight="weight", resolution=0.45, seed=7)
    comms = sorted((c for c in comms if len(c) >= 8), key=len, reverse=True)[:10]   # 最多 10 个群，其余算「其他」
    group = {}
    names = []
    for gi, c in enumerate(comms):
        top = sorted(c, key=lambda i: (-len(vocab[i]["occ"]), -sum(vocab[i]["occ"].values())))[:3]
        names.append("・".join(vocab[i]["w"].split(" / ")[0] for i in top))
        for i in c:
            group[i] = gi
    rnd = random.Random(7)
    pos = {i: (rnd.uniform(-1, 1), rnd.uniform(-1, 1)) for i in range(len(vocab))}

    band_of = {sid: albums[s["album"]]["artist"] for sid, s in songs.items()}
    # 时间轴：专辑按发行时间排序；歌曲只算正式版本（dup_of 的其他版本不算）
    album_list = sorted(data["albums"], key=lambda a: a["year"])
    a_idx = {a["id"]: i for i, a in enumerate(album_list)}
    song_list = [s for s in data["songs"] if not s.get("dup_of")]
    s_idx = {s["id"]: i for i, s in enumerate(song_list)}
    nodes = []
    for i, v in enumerate(vocab):
        bands = {band_of[sid] for sid in v["occ"]}
        x = None
        if v.get("x"):
            sid, li = v["x"]
            k = f"{sid}|{li}"
            if k not in lines_out:
                ja, zh = data["lines"][sid][li][:2]
                s = songs[sid]
                lines_out[k] = [ja, zh, s["ja"], albums[s["album"]].get("short") or albums[s["album"]]["ja"],
                                reading(data["lines"][sid][int(li)][2])]
            x = [k, line_words[k].get(i, [])]
        nodes.append({"id": i, "w": v["w"].split(" / ")[0], "full": v["w"], "k": v["k"], "r": v["r"], "m": v["m"],
                      "n": len(v["occ"]), "band": bands.pop() if len(bands) == 1 else "both",
                      "g": group.get(i, -1), "x": round(float(pos[i][0]), 4), "y": round(float(pos[i][1]), 4), "ex": x,
                      "so": sorted(s_idx[sid] for sid in v["occ"] if sid in s_idx),
                      "fa": min(a_idx[songs[sid]["album"]] for sid in v["occ"])})

    out = {"nodes": nodes, "edges": edges, "groups": names, "lines": lines_out,
           "bands": {b["id"]: b["ja"] for b in data["bands"]},
           "albums": [{"id": a["id"], "ja": a["ja"], "short": a.get("short") or a["ja"], "zh": a["zh"], "year": a["year"],
                       "band": a["artist"], "cover": a.get("cover")} for a in album_list],
           "songs": [{"id": s["id"], "ja": s["ja"], "zh": s["zh"], "a": a_idx[s["album"]]} for s in song_list]}
    # 「一首歌的星座」用：每首歌逐行的歌词、读音和这行里的词（单独一个文件，用到时才加载）
    per_song = {}
    for s in song_list:
        rows = []
        for li, (ja, zh, segs, t) in enumerate(data["lines"][s["id"]]):
            rows.append([ja, zh, reading(segs), sorted(line_words.get(f"{s['id']}|{li}", {}))])
        per_song[s["id"]] = rows
    (ROOT / "web" / "demos" / "songs.json").write_text(json.dumps(per_song, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    dst = ROOT / "web" / "demos" / "graph.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(nodes)} nodes, {len(edges)} edges, {len(names)} groups, {len(lines_out)} lines, "
          f"{dst.stat().st_size // 1024} KB → {dst.relative_to(ROOT)}")
    for gi, n in enumerate(names):
        print(f"  群 {gi}: {n}（{sum(1 for x in nodes if x['g'] == gi)} 个词）")


if __name__ == "__main__":
    main()
