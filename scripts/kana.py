"""假名工具：片假名→平假名，假名→连写罗马音（沿用 v1 写法：kyou / gitaa / wo）。"""

_BASE = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "ゐ": "i", "ゑ": "e", "を": "wo", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o", "ゔ": "vu",
}
_YOON = {"ゃ": "a", "ゅ": "u", "ょ": "o"}
_SMALL_VOWEL = {"ぁ": "a", "ぃ": "i", "ぅ": "u", "ぇ": "e", "ぉ": "o"}


def to_hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def to_romaji(s):
    s = to_hira(s)
    out = []
    i = 0
    while i < len(s):
        c = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        if c == "っ":
            r = _syllable(s, i + 1)[0]
            out.append(r[0] if r and r[0] not in "aiueon" else "")
            i += 1
            continue
        if c == "ー":
            prev = "".join(out)
            out.append(next((ch for ch in reversed(prev) if ch in "aiueo"), ""))
            i += 1
            continue
        r, n = _syllable(s, i)
        if r is None:
            out.append(c)
            i += 1
        else:
            out.append(r)
            i += n
    return "".join(out)


def _syllable(s, i):
    if i >= len(s):
        return "", 0
    c = s[i]
    nxt = s[i + 1] if i + 1 < len(s) else ""
    base = _BASE.get(c)
    if base is None:
        return None, 1
    if nxt in _YOON and base.endswith("i") and c not in "いぃ":
        head = base[:-1]
        if head in ("sh", "ch", "j"):
            return head + _YOON[nxt], 2
        return head + "y" + _YOON[nxt], 2
    if nxt in _SMALL_VOWEL and c not in _SMALL_VOWEL:
        if c == "ふ":
            return "f" + _SMALL_VOWEL[nxt], 2
        if c in "てで" and nxt == "ぃ":
            return base[0] + "i", 2
        if c == "う":
            return "w" + _SMALL_VOWEL[nxt], 2
        if base.endswith("i"):
            return base[:-1] + _SMALL_VOWEL[nxt], 2
    return base, 1


if __name__ == "__main__":
    for w in ["わすれる", "きょう", "ギター", "ロックンロール", "ずっと", "しょうらい", "ティー", "ファン", "を"]:
        print(w, to_romaji(w))
