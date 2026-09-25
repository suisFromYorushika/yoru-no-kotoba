"""一次性迁移：v1 的 vocab_def.py / examples.py → data/lemmas.json 和 data/grammar.json。

词条的 match（怎么在分词结果里找到这个词）：
  "忘れる"                        原形等于它的词
  [{"l": "神"}, {"l": "様"}]      连续几个词依次满足条件（条件格式同 grammar.json 的 tok 规则）
  {"re": "どうでもいい"}           对整行日文用正则（多词短语的兜底）
"""
import json
import sys
from pathlib import Path

import fugashi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from vocab_def import W, G  # noqa: E402
from examples import EX  # noqa: E402

# 自动推断（每个写法分词后若只有一个词，就用它的原形）不对的，手工指定
MATCH_OVERRIDE = {
    "神様": [[{"l": "神"}, {"l": "様", "p": "接尾辞"}], "神様"],
    "歌": ["歌", "唄"],
    "いらない": [[{"l": "要る"}, {"l": "ない"}]],
    "足りない": [[{"l": "足りる"}, {"l": "ない"}]],
    "どうでもいい": [{"re": "どうでもいい|どうだっていい"}],
    "このまま": [[{"l": "此の"}, {"l": "侭"}], "此の侭"],
    "一つ": [[{"s": "一"}, {"s": "つ"}], "一つ"],
    "六畳": [[{"s": "六"}, {"s": "畳"}], "六畳"],
    "花緑青": [[{"s": "花"}, {"s": "緑青"}], "花緑青"],
    "マシンガン": [[{"s": "マシン"}, {"s": "ガン"}], "マシンガン"],
    "仕方がない": [{"re": "仕方(が)?ない"}],
    "辞める": [[{"l": "止める", "s": "辞.*"}]],
    "目 / 眼": [[{"l": "目", "p": "名詞"}]],
    "青": ["青", "青い"],
    "遠く / 遠い": ["遠い", "遠く"],
    "ただ": ["唯", "只"],
    "夜明け": ["夜明け", [{"l": "夜"}, {"s": "が"}, {"l": "明ける"}], [{"l": "夜"}, {"l": "明ける"}]],
}

# v1 语法 → 新规则。re：整行正则；tok：按分词结果匹配（能排除「言って」「死んだ」「さよなら」这类误判）
GRAMMAR_RULE = {
    "〜まま": {"re": "まま"},
    "〜ように / 〜ような": {"tok": [{"l": "様", "p": "形状詞"}, {"s": "[にな]"}]},
    "〜たい / 〜たくない": {"tok": [{"l": "たい", "p": "助動詞"}]},
    "〜だけ": {"tok": [{"s": "だけ", "p": "助詞"}]},
    "〜ばかり / 〜ばっか": {"re": "ばかり|ばっか"},
    "〜なんて": {"re": "なんて"},
    "〜って": {"tok": [{"s": "って", "p": "助詞"}]},
    "〜んだ / 〜のだ / 〜のさ": {"tok": [{"p2": "準体助詞"}, {"s": "だ|だっ|です|さ|だろう?"}]},
    "〜みたい": {"tok": [{"l": "みたい"}]},
    "〜なら": {"tok": [{"s": "なら", "l": ["だ", "なら", "なり"]}]},
    "〜ても / 〜でも": {"tok": [{"s": "[てで]", "p": ["助詞", "助動詞"]}, {"s": "も", "p": "助詞"}]},
    "〜たら": {"tok": [{"s": "[たど]ら", "l": "た"}]},
    "〜ながら": {"tok": [{"s": "ながら", "p": "助詞"}]},
    "〜ないで": {"tok": [{"l": "ない", "p": "助動詞"}, {"s": "で", "p": "助詞"}]},
    "〜だろう / 〜だろ": {"re": "だろ"},
    "〜ほど": {"tok": [{"s": "ほど", "p": "助詞"}]},
    "〜ほしい / 欲しい": {"tok": [{"l": "欲しい"}]},
    "〜ものか / 〜もんか": {"re": "ものか|もんか"},
    "〜ずに / 〜ぬ(文语否定)": {"tok": [{"l": "ず", "p": "助動詞"}]},
    "〜こそ": {"tok": [{"s": "こそ", "p": "助詞"}]},
    # 分词器常把「描け」「思い出せ」误判为连用形/未然形，所以用 v1 的列表补充
    "命令形(歌え・消えろ…)": {"any": [{"tok": [{"p": ["動詞", "助動詞"], "f": "命令形"}]},
                                  {"re": "歌え|消えろ|描け(?![るばた])|思い出せ(?![るばた])|言い返せ|往け|開け(?!た)"}]},
}

GRAMMAR_ID = {
    "〜まま": "mama", "〜ように / 〜ような": "you", "〜たい / 〜たくない": "tai", "〜だけ": "dake",
    "〜ばかり / 〜ばっか": "bakari", "〜なんて": "nante", "〜って": "tte", "〜んだ / 〜のだ / 〜のさ": "nda",
    "〜みたい": "mitai", "〜なら": "nara", "〜ても / 〜でも": "temo", "〜たら": "tara", "〜ながら": "nagara",
    "〜ないで": "naide", "〜だろう / 〜だろ": "darou", "〜ほど": "hodo", "〜ほしい / 欲しい": "hoshii",
    "〜ものか / 〜もんか": "monoka", "〜ずに / 〜ぬ(文语否定)": "zuni", "〜こそ": "koso",
    "命令形(歌え・消えろ…)": "meirei",
}


def auto_match(word, tagger):
    lemmas = []
    for form in word.split(" / "):
        toks = list(tagger(form))
        if len(toks) != 1:
            raise ValueError(f"需要手工指定 match：{word}")
        lemma = (toks[0].feature.lemma or form).split("-")[0]
        if lemma not in lemmas:
            lemmas.append(lemma)
    return lemmas


def split_ex(s):
    # "電気をつけたまま寝た。(开着灯就睡着了。)" → ["電気をつけたまま寝た。", "", "开着灯就睡着了。"]
    ja, _, zh = s.partition("(")
    return [ja.strip(), "", zh.rstrip(")").strip()]


def main():
    tagger = fugashi.Tagger()
    lemmas = []
    for w, k, r, m, _rx in W:
        match = MATCH_OVERRIDE.get(w) or auto_match(w, tagger)
        ex = EX.get(w)
        lemmas.append({"w": w, "k": k, "r": r, "m": m, "ex": list(ex) if ex else None, "match": match})
    (ROOT / "data" / "lemmas.json").write_text(
        "[\n" + ",\n".join(json.dumps(x, ensure_ascii=False) for x in lemmas) + "\n]\n", encoding="utf-8")

    grammar = []
    for g, r, m, _rx, ex in G:
        grammar.append({"id": GRAMMAR_ID[g], "g": g, "r": r, "m": m, "ex": split_ex(ex), "rule": GRAMMAR_RULE[g]})
    (ROOT / "data" / "grammar.json").write_text(
        "[\n" + ",\n".join(json.dumps(x, ensure_ascii=False) for x in grammar) + "\n]\n", encoding="utf-8")
    print(len(lemmas), "lemmas,", len(grammar), "grammar")


if __name__ == "__main__":
    main()
