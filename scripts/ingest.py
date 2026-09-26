"""把本地歌词库导入仓库：复制 .ja.lrc / .zh.lrc 和专辑背景 md 到 lyrics/，并生成/更新 data/catalog.json。

用法：python scripts/ingest.py [歌词库路径] [--force]
默认路径：~/Documents/Gemini Spark/Lyrics

- 歌词库里的乐队文件夹、专辑文件夹对应哪个乐队 / 专辑 id，写在 data/library.json；遇到没写的会停下来提示。
- 文件名统一 NFC 规范化（macOS 上是 NFD）。
- 已有的 catalog.json 中的 id、中文名、介绍等手工字段不会被覆盖，只补充新歌。
- 仓库里已有、但内容和歌词库不同的文件（整理时修过的歌词）默认保留；加 --force 才用歌词库的版本覆盖。
- 歌名更正过的歌，catalog.json 里的 `lib_ja` 记着歌词库里的旧歌名；导入时跳过这个文件，不会把它当成新歌加回来。
"""
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LYRICS_OUT = ROOT / "lyrics"
CATALOG = ROOT / "data" / "catalog.json"
V1_DATA = ROOT / "data" / "data.json"

LIBRARY = ROOT / "data" / "library.json"
TYPE_ZH = {"Full Album": "全长专辑", "Mini Album": "迷你专辑"}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def parse_album_dir(name):
    # "[概念专辑] 盗作 (2020.07)"
    m = re.match(r"\[(.+?)\]\s*(.+?)\s*\(([\d.\-]+)\)$", name)
    return m.group(1), m.group(2), m.group(3)


def parse_background(path):
    """从 00_专辑背景与曲目全解析.md 提取中文名、规格、第一句介绍、曲目中文名。"""
    text = nfc(path.read_text(encoding="utf-8"))
    info = {"zh": None, "spec": None, "note": None, "titles": {}}
    m = re.search(r"^# 《.+?\((.+?)\)》", text, re.M)
    if m:
        info["zh"] = m.group(1).split("/")[-1].strip()
    m = re.search(r"专辑规格\*\*[：:]\s*(.+)", text)
    if m:
        info["spec"] = m.group(1).strip()
    m = re.search(r"## 一、.*?\n\n(.+?)\n", text, re.S)
    if m:
        first = re.split(r"(?<=[。！？])", m.group(1).strip())[0]
        info["note"] = first.strip()
    for tm in re.finditer(r"^\|\s*\*\*(\d+)\.\s*(.+?)\*\*\s*\|\s*\*\*(.+?)\*\*", text, re.M):
        info["titles"][tm.group(2).strip()] = tm.group(3).split("/")[0].strip()
    return info


def album_type(folder_type, spec):
    if spec:
        s = re.sub(r"\s*\(.*?\)", "", spec)
        for en, zh in TYPE_ZH.items():
            s = s.replace(en, zh)
        return s
    return folder_type


def load_catalog():
    if CATALOG.exists():
        return json.loads(CATALOG.read_text(encoding="utf-8"))
    cat = {"bands": [], "albums": [], "songs": []}
    # 首次运行：沿用 v1 的专辑与歌曲 id / 中文名
    if V1_DATA.exists():
        v1 = json.loads(V1_DATA.read_text(encoding="utf-8"))
        for a in v1["albums"]:
            cat["albums"].append({"id": a["id"], "band": a["artist"], "ja": a["ja"], "zh": a["zh"],
                                  "year": a["year"], "type": a["type"], "note": a["note"], "done": True})
        for s in v1["songs"]:
            cat["songs"].append({"id": s["id"], "album": s["album"], "ja": s["ja"], "zh": s["zh"]})
    return cat


def load_library():
    """data/library.json：歌词库文件夹名 → 乐队、专辑名 → 专辑 id。"""
    lib = json.loads(LIBRARY.read_text(encoding="utf-8"))
    bands = {nfc(b["lib"]): {k: b[k] for k in ("id", "ja", "zh")} for b in lib["bands"]}
    albums = {nfc(a["lib"]): a["id"] for a in lib["albums"]}
    return bands, albums


def main():
    BANDS, ALBUM_IDS = load_library()
    band_order = [b["id"] for b in BANDS.values()]
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv[1:]
    src = Path(args[0] if args else os.path.expanduser("~/Documents/Gemini Spark/Lyrics"))
    cat = load_catalog()
    bands = {b["id"]: b for b in cat["bands"]}
    albums = {a["id"]: a for a in cat["albums"]}
    songs = cat["songs"]
    next_id = max((int(s["id"][1:]) for s in songs), default=-1) + 1

    album_dirs = []
    for band_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        band = BANDS.get(nfc(band_dir.name))
        if band is None:
            sys.exit(f"歌词库里的「{nfc(band_dir.name)}」不认识：请在 data/library.json 的 bands 里加一行（lib 写这个文件夹名）")
        bands.setdefault(band["id"], dict(band))
        for d in band_dir.iterdir():
            if d.is_dir():
                ftype, ja, year = parse_album_dir(nfc(d.name))
                if ja not in ALBUM_IDS:
                    sys.exit(f"专辑「{ja}」没有 id：请在 data/library.json 的 albums 里加一行，例如 {{\"lib\": \"{ja}\", \"id\": \"英文或罗马字\"}}")
                album_dirs.append((band["id"], year, d, ftype, ja))
    album_dirs.sort(key=lambda x: (band_order.index(x[0]), x[1]))

    kept = []  # 仓库里改过（和歌词库不同）、这次没覆盖的文件

    def copy(f, dst):
        if dst.exists() and not force and dst.read_bytes() != f.read_bytes():
            kept.append(dst.relative_to(ROOT))
        else:
            shutil.copyfile(f, dst)

    for band_id, year, d, ftype, ja in album_dirs:
        aid = ALBUM_IDS[ja]
        files = {nfc(f.name): f for f in d.iterdir()}
        bg_name = next((n for n in files if n.startswith("00_专辑背景")), None)
        bg = parse_background(files[bg_name]) if bg_name else {"zh": None, "spec": None, "note": None, "titles": {}}
        a = albums.setdefault(aid, {"id": aid, "band": band_id, "ja": ja, "zh": bg["zh"] or ja,
                                    "year": year, "type": album_type(ftype, bg["spec"]),
                                    "note": bg["note"] or "", "done": False})
        a["dir"] = f"{band_id}/{aid}"
        out = LYRICS_OUT / band_id / aid
        out.mkdir(parents=True, exist_ok=True)
        if bg_name:
            copy(files[bg_name], out / "_album.md")

        for name in sorted(files):
            m = re.match(r"(\d+)\.\s*(.+)\.ja\.lrc$", name)
            if not m:
                continue
            track, title = int(m.group(1)), m.group(2)
            song = next((s for s in songs if s["album"] == aid and title in (s["ja"], s.get("lib_ja"))), None)
            if song is not None and title != song["ja"]:
                print(f"跳过 {ja}/{name}：这首歌已更正为「{song['ja']}」")
                continue
            zh_name = name[:-len(".ja.lrc")] + ".zh.lrc"
            stem = f"{track:02d}.{title}"
            copy(files[name], out / f"{stem}.ja.lrc")
            if zh_name in files:
                copy(files[zh_name], out / f"{stem}.zh.lrc")
            if song is None:
                song = {"id": f"s{next_id}", "album": aid, "ja": title, "zh": bg["titles"].get(title, title)}
                next_id += 1
                songs.append(song)
            song["track"] = track
            song["file"] = f"{a['dir']}/{stem}"

    # 同一乐队内曲名相同（或只差版本后缀）的歌，标记为重复版本，统计"出现在几首歌"时只算一次
    def base_title(t):
        return re.sub(r"\s*\((?:[^()]*ver\.?|demo)\)\s*$", "", t, flags=re.I).strip()
    album_band = {a["id"]: a["band"] for a in albums.values()}
    album_order = {aid: i for i, (_, _, _, _, ja) in enumerate(album_dirs) for aid in [ALBUM_IDS[ja]]}
    seen = {}
    for s in sorted(songs, key=lambda s: (album_order.get(s["album"], 99), s.get("track", 0))):
        key = (album_band[s["album"]], base_title(s["ja"]))
        if key in seen:
            s["dup_of"] = seen[key]
        else:
            s.pop("dup_of", None)
            seen[key] = s["id"]

    order = {aid: i for i, aid in enumerate(album_order)}
    cat["bands"] = list(bands.values())
    cat["albums"] = sorted(albums.values(), key=lambda a: order.get(a["id"], 99))
    cat["songs"] = sorted(songs, key=lambda s: int(s["id"][1:]))
    CATALOG.write_text(json.dumps(cat, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if kept:
        print(f"保留了 {len(kept)} 个仓库里改过的文件（和歌词库里的不同；要用歌词库的版本覆盖，加 --force）：")
        for k in kept:
            print(f"  {k}")
    print(f"{len(cat['albums'])} albums, {len(cat['songs'])} songs, "
          f"{sum(1 for s in cat['songs'] if 'dup_of' in s)} duplicate versions")


if __name__ == "__main__":
    main()
