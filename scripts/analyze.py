"""歌词 → 分词结果：读取 lyrics/ 下的 LRC，按时间戳对齐中日行，用 fugashi + UniDic 分词，
匹配 data/grammar.json 里的语法规则，每首歌写一个 data/songs/<id>.json。

用法：python scripts/analyze.py            # 全部歌曲
      python scripts/analyze.py s14 s15    # 指定歌曲

每行歌词：
  {"t": 毫秒, "ja": 日文, "zh": 中文, "tok": [词...], "gram": [[语法id, 起, 止], ...]}
每个词（tok 的元素）：
  s  原文写法          l  原形（UniDic lemma，归一写法：想い出→思い出）  lk 原形的读音
  k  读音（平假名）    p  词性大类（名詞/動詞/助詞…）  p2 词性细类
  f  活用形（仅活用词） i  [起, 止] 在该行日文中的字符位置
"""
import json
import re
import sys
from pathlib import Path

import fugashi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kana import to_hira  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CREDIT = re.compile(r"^\s*(作词|作詞|作曲|编曲|編曲|演唱|制作人|标题|歌)\s*[:：]")
TITLE = re.compile(r"^(ヨルシカ|あたらよ)\s*[-－–—]\s|\s[-－–—]\s*(ヨルシカ|あたらよ)$")  # 「ヨルシカ - 曲名」这类标题行
RUBY = re.compile(r"([\u3400-\u9fff々〆ヶ]+)[(（]([ぁ-ゖァ-ヺー]+)[)）]")  # 歌词里用括号标的读音：噤(つぐ)んだ
TS = re.compile(r"\[(\d+):(\d+)(?:[.:](\d+))?\]")
KANJI_RE = re.compile(r"[\u3400-\u9fff々〆ヶ]")
KATA_RE = re.compile(r"[ァ-ヺー・]+")

tagger = fugashi.Tagger()


def parse_lrc(path):
    """返回 [(毫秒, 文本)]，去掉元数据标签和作词作曲等信息行、空行。"""
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        stamps = []
        pos = 0
        while True:
            m = TS.match(line, pos)
            if not m:
                break
            mm, ss, frac = m.group(1), m.group(2), m.group(3) or "0"
            stamps.append(int(mm) * 60000 + int(ss) * 1000 + int(frac.ljust(3, "0")[:3]))
            pos = m.end()
        text = line[pos:].strip().strip("\u200b\u200e\u200f\ufeff").strip()  # 去掉看不见的方向标记
        if not stamps or not text or CREDIT.match(text) or TITLE.search(text):
            continue
        rows.extend((t, text) for t in stamps)
    rows.sort(key=lambda r: r[0])
    return rows


def align(ja_rows, zh_rows):
    """按时间戳对齐：完全相同优先，否则取 ±300ms 内最近的中文行。"""
    zh_by_t = {}
    for t, text in zh_rows:
        zh_by_t.setdefault(t, text)
    zh_times = sorted(zh_by_t)
    out = []
    for t, ja in ja_rows:
        zh = zh_by_t.get(t)
        if zh is None and zh_times:
            near = min(zh_times, key=lambda x: abs(x - t))
            if abs(near - t) <= 300:
                zh = zh_by_t[near]
        out.append((t, ja, zh or ""))
    return out


def tokenize(text):
    toks = []
    cur = 0
    for w in tagger(text):
        f = w.feature
        start = text.find(w.surface, cur)
        if start < 0:
            start = cur
        end = start + len(w.surface)
        cur = end
        tok = {"s": w.surface, "l": (f.lemma or w.surface).split("-")[0], "p": f.pos1}
        if f.kana and f.kana != "*":
            tok["k"] = to_hira(f.kana)
        if f.pos2 and f.pos2 != "*":
            tok["p2"] = f.pos2
        if f.cForm and f.cForm != "*":
            tok["f"] = f.cForm
        if f.lForm and f.lForm != "*":
            tok["lk"] = to_hira(f.lForm)
        # 人名地名的原形 UniDic 写成片假名（小平 → コダイラ），弹窗里没用，改成原文写法
        if tok.get("p2") == "固有名詞" and KATA_RE.fullmatch(tok["l"]):
            tok["l"] = w.surface
            if "k" in tok:
                tok["lk"] = tok["k"]
        tok["i"] = [start, end]
        toks.append(tok)
    return toks


def strip_ruby(text):
    """去掉歌词里括号标注的读音（塵(ごみ) → 塵），返回新文本和 [(起, 止, 读音)]，分词后再把读音写回去。"""
    out, notes, pos = "", [], 0
    for m in RUBY.finditer(text):
        out += text[pos:m.start()]
        notes.append((len(out), len(out) + len(m.group(1)), m.group(2)))
        out += m.group(1)
        pos = m.end()
    return out + text[pos:], notes


def apply_ruby(text, toks, notes):
    """把括号里的读音写到对应的词上：正好是一个词就直接改读音；词后面还带假名（噤ん）就接上；
    被拆成几个词（山桜桃梅）就合成一个名词。"""
    for a, b, r in notes:
        first = next((t for t in toks if t["i"][0] == a), None)
        inside = [t for t in toks if t["i"][0] >= a and t["i"][1] <= b]
        if first and first["i"][1] == b:
            first["k"] = r
        elif first and first["i"][1] > b and re.fullmatch(r"[ぁ-ゖ]+", first["s"][b - a:]):
            first["k"] = r + first["s"][b - a:]
        elif inside and inside[0]["i"][0] == a and inside[-1]["i"][1] == b:
            word = text[a:b]
            merged = {"s": word, "l": word, "p": "名詞", "k": r, "p2": "普通名詞", "lk": r, "i": [a, b]}
            k = toks.index(inside[0])
            toks[k:k + len(inside)] = [merged]


# ── 语法规则 ──────────────────────────────────────────────
# rule = {"re": 正则}                  作用于整行日文
#      | {"tok": [条件, ...]}          连续的词依次满足各条件
# 条件的键：s(写法正则) k(读音正则，平假名) l(原形，字符串或列表) p/p2(词性，可用 "!x" 表示排除) f(活用形正则)
#          prev/next(前一个/后一个词须满足的条件)  !prev/!next(前一个/后一个词不能满足的条件)
#          例：{"l": "居る", "!prev": {"l": "て", "p": "助詞"}} 只算「在」，不算「〜ている」

def _ok(tok, cond):
    for key, want in cond.items():
        if key == "s":
            if not re.fullmatch(want, tok["s"]):
                return False
        elif key == "k":
            if not re.fullmatch(want, tok.get("k", "")):
                return False
        elif key == "f":
            if not re.match(want, tok.get("f", "")):
                return False
        elif key == "l":
            if tok["l"] not in (want if isinstance(want, list) else [want]):
                return False
        elif key in ("p", "p2"):
            val = tok.get(key, "")
            wants = want if isinstance(want, list) else [want]
            neg = [w[1:] for w in wants if w.startswith("!")]
            pos = [w for w in wants if not w.startswith("!")]
            if val in neg or (pos and val not in pos):
                return False
    return True


def _ctx_ok(toks, k, cond):
    """检查第 k 个词的前后文条件（prev / next / !prev / !next）。"""
    for key, off in (("prev", -1), ("next", 1)):
        j = k + off
        nb = toks[j] if 0 <= j < len(toks) else None
        if key in cond and not (nb and _ok(nb, cond[key])):
            return False
        if "!" + key in cond and nb and _ok(nb, cond["!" + key]):
            return False
    return True


def seq_spans(seq, toks):
    """连续的词依次满足 seq 里的各条件，返回每处命中的 [起, 止]。"""
    n = len(seq)
    return [[toks[i]["i"][0], toks[i + n - 1]["i"][1]]
            for i in range(len(toks) - n + 1)
            if all(_ok(toks[i + j], c) and _ctx_ok(toks, i + j, c) for j, c in enumerate(seq))]


def rule_spans(rule, text, toks):
    """rule 可以是 {"re": ...}、{"tok": [...]}，或 {"any": [rule, ...]}（取并集，重叠的只算一次）。"""
    if "any" in rule:
        spans = sorted({tuple(s) for r in rule["any"] for s in rule_spans(r, text, toks)})
        out = []
        for s in spans:
            if out and s[0] < out[-1][1]:
                continue
            out.append(list(s))
        return out
    if "re" in rule:
        return [[m.start(), m.end()] for m in re.finditer(rule["re"], text)]
    return seq_spans(rule["tok"], toks)


def match_grammar(rules, text, toks):
    hits = [[g["id"]] + s for g in rules for s in rule_spans(g["rule"], text, toks)]
    hits.sort(key=lambda h: (h[1], h[0]))
    return hits


def dump_song(song):
    """一行歌词一行 JSON，便于 git diff。"""
    head = {k: song[k] for k in song if k != "lines"}
    body = ",\n".join("  " + json.dumps(l, ensure_ascii=False, separators=(",", ":")) for l in song["lines"])
    h = json.dumps(head, ensure_ascii=False)[:-1]
    return f'{h}, "lines": [\n{body}\n]}}\n'


def relemma_reading(t):
    """读音改了以后，原形的读音跟着改：開い(あい) → 開く(あく)，弾ける(はじける) → 弾く(はじく)。
    做法：写法和原形共用的汉字开头按新读音算，后面的假名词尾换成原形的词尾；对不上就不动。"""
    s, l, k = t["s"], t["l"], t["k"]
    if l == s:
        return  # 没变形的词不动：修正的读音常常只在这里成立（入道雲 的 雲 读 ぐも，原形还是 くも）
    i = 0
    while i < min(len(s), len(l)) and s[i] == l[i]:
        i += 1
    stem, s_tail, l_tail = s[:i], s[i:], l[i:]
    if not s_tail or not KANJI_RE.search(stem) or KANJI_RE.search(s_tail + l_tail):
        return  # 只处理「汉字 + 假名词尾」的变形（開い、弾ける）；憂(ゆう) 这种单个汉字对不出原形读音
    tail = to_hira(s_tail)
    if not k.endswith(tail) or len(k) <= len(tail):
        return
    t["lk"] = k[:len(k) - len(tail)] + to_hira(l_tail)


def fix_readings(fixes, toks, text=""):
    """按 data/readings.json 修正 UniDic 的错误：k 改读音（原形的读音跟着改）；
    l / lk / p / p2 改原形和词性（UniDic 把 そうか 当成人名 爽果、金 当成人名 キン 这类）。
    可以加 "line": 正则，只在这一行日文包含它时才改（用来区分 溜息を吐く(つく) 和 息を吐く(はく)）。"""
    fixes = [fx for fx in fixes if "line" not in fx or re.search(fx["line"], text)]
    hits = []
    for i, t in enumerate(toks):
        for fx in fixes:
            if _ok(t, fx["tok"]) and _ctx_ok(toks, i, fx["tok"]):
                hits.append((t, fx))
                break
    # 先全部判断完再改，免得前一个词改了原形，后一个词的 prev 条件就对不上了
    for t, fx in hits:
        for key in ("l", "p", "p2"):
            if key in fx:
                t[key] = fx[key]
        if "k" in fx:
            t["k"] = fx["k"]
            relemma_reading(t)
        if "lk" in fx:
            t["lk"] = fx["lk"]


def main():
    catalog = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    fpath = ROOT / "data" / "readings.json"
    fixes = json.loads(fpath.read_text(encoding="utf-8")) if fpath.exists() else []
    gpath = ROOT / "data" / "grammar.json"
    rules = json.loads(gpath.read_text(encoding="utf-8")) if gpath.exists() else []
    want = set(sys.argv[1:])
    out_dir = ROOT / "data" / "songs"
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for s in catalog["songs"]:
        if want and s["id"] not in want:
            continue
        base = ROOT / "lyrics" / s["file"]
        rows = align(parse_lrc(base.with_name(base.name + ".ja.lrc")),
                     parse_lrc(base.with_name(base.name + ".zh.lrc")))
        lines = []
        for t, ja, zh in rows:
            ja, notes = strip_ruby(ja)
            toks = tokenize(ja)
            fix_readings(fixes, toks, ja)
            apply_ruby(ja, toks, notes)
            line = {"t": t, "ja": ja, "zh": zh, "tok": toks}
            gram = match_grammar(rules, ja, toks)
            if gram:
                line["gram"] = gram
            lines.append(line)
        song = {"id": s["id"], "album": s["album"], "ja": s["ja"], "zh": s["zh"], "lines": lines}
        (out_dir / f"{s['id']}.json").write_text(dump_song(song), encoding="utf-8")
        n += 1
    print(f"analyzed {n} songs")


if __name__ == "__main__":
    main()
