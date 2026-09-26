"""data/data.json + web/template.html → web/index.html

完整的单文件网页（GitHub Pages / 双击离线打开），封面在 web/covers/。
网址和 Supabase 配置在 data/site.json；填了 supabase_url / supabase_key，就能用 Supabase 账号登录同步。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data = (ROOT / "data" / "data.json").read_text(encoding="utf-8").strip()
    site = (ROOT / "data" / "site.json").read_text(encoding="utf-8")
    # 防止歌词里的 "</" 提前结束 <script>
    data = data.replace("</", "<\\/")
    site_js = json.dumps(json.loads(site), ensure_ascii=False).replace("</", "<\\/")
    tpl = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    out = ROOT / "web" / "index.html"
    out.write_text(tpl.replace("__DATA__", data, 1).replace("__SITE__", site_js, 1), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
