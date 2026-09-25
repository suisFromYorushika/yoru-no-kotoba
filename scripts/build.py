"""data/data.json + web/template.html → 两个网页：

- web/index.html     完整的单文件网页（GitHub Pages / 双击离线打开），封面在 web/covers/
- web/artifact.html  发布到 claude.ai 的版本（去掉 <html>/<head>/<body> 外壳，平台会自动套上），
                     在那里打开可以用 claude.ai 账号登录并把进度存到云端
网址和 Supabase 配置在 data/site.json；填了 supabase_url / supabase_key，GitHub Pages 版就能用 Supabase 账号登录同步。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data = (ROOT / "data" / "data.json").read_text(encoding="utf-8").strip()
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    # 防止歌词里的 "</" 提前结束 <script>
    data = data.replace("</", "<\\/")
    tpl = (ROOT / "web" / "template.html").read_text(encoding="utf-8")

    def page(host):
        # host：pages（GitHub Pages / 本地打开，可用 Supabase 登录）或 claude（claude.ai 版，用 claude.ai 账号）
        site_js = json.dumps({**site, "host": host}, ensure_ascii=False).replace("</", "<\\/")
        return tpl.replace("__DATA__", data, 1).replace("__SITE__", site_js, 1)

    out = ROOT / "web" / "index.html"
    out.write_text(page("pages"), encoding="utf-8")

    html = page("claude")
    head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
    head = re.sub(r'\s*<meta charset="UTF-8">|\s*<meta name="viewport"[^>]*>', "", head)
    body = re.search(r"<body>(.*?)</body>", html, re.S).group(1)
    art = ROOT / "web" / "artifact.html"
    art.write_text(head.strip() + "\n" + body.strip() + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB), "
          f"{art.relative_to(ROOT)} ({art.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
