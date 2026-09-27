"""提交前 / CI 的检查：学习进度的键不能被改掉。

- data/lemmas.json 里每个词条都有 w，且不重复
- 和基准版本（默认 origin/main）比，原来有的 w 一个都不能少
- 网页模板里 localStorage 的键名还在

用法：python3 scripts/check.py [基准 git 版本]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE_KEYS = ["yorushika_learned_v1", "yoru_srs_v1", "yoru_log_v1", "yoru_ui_v1", "yoru_player_v1", "yoru_synced_v1"]


def words(lemmas):
    return [x.get("w") for x in lemmas]


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    errors = []

    head = words(json.loads((ROOT / "data" / "lemmas.json").read_text(encoding="utf-8")))
    if None in head:
        errors.append(f"lemmas.json 有 {head.count(None)} 个词条没有 w")
    seen, dup = set(), set()
    for w in head:
        (dup if w in seen else seen).add(w)
    if dup:
        errors.append("lemmas.json 里 w 重复：" + "、".join(sorted(dup)))

    try:
        old = subprocess.run(["git", "show", f"{base}:data/lemmas.json"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError:
        print(f"找不到基准版本 {base}，跳过 w 对比")
    else:
        missing = [w for w in words(json.loads(old)) if w not in seen]
        if missing:
            errors.append(f"和 {base} 比，这些 w 不见了（用户进度会对不上）：" + "、".join(missing))

    tpl = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    gone = [k for k in STORAGE_KEYS if k not in tpl]
    if gone:
        errors.append("web/template.html 里找不到 localStorage 键：" + "、".join(gone))

    for e in errors:
        print("✗", e)
    if errors:
        sys.exit(1)
    print(f"✓ {len(head)} 个词条，w 完整；localStorage 键都在")


if __name__ == "__main__":
    main()
