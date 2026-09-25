"""data/data.json + web/template.html → web/index.html（单文件，双击即可离线打开）。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data = (ROOT / "data" / "data.json").read_text(encoding="utf-8").strip()
    data = data.replace("</", "<\\/")  # 防止歌词里的 "</" 提前结束 <script>
    tpl = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    out = ROOT / "web" / "index.html"
    out.write_text(tpl.replace("__DATA__", data, 1), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
