#!/usr/bin/env python3
"""render_html — IC-MEMO → single-file HTML (issue #4, R3)

One static page: sidebar table of contents, the yaml head as a highlighted block,
sections, tables (guest critiques), and the footer — no frameworks, no external
assets, shareable as a single file; readable in a browser, on a phone, in print.

A deliberately small Markdown subset, enough for IC-MEMO structure: headings,
fenced code blocks, tables, lists, bold/inline-code, hr, blockquotes, paragraphs.

Usage:
  python3 scripts/render_html.py memos/DEMO-2026-11-16-guests.md   # → <name>.html
  python3 scripts/render_html.py memo.md -o out.html
"""
import argparse, html, os, re, sys


def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\w)\*(?!\s)([^*]+?)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "s"


def render(md, title=None):
    lines = md.splitlines()
    out, toc, in_code, code_buf, table_buf, para_buf = [], [], False, [], [], []
    title = title or (re.match(r"#\s+(.+)", next((l for l in lines if l.startswith("# ")), "")).group(1)
                      if any(l.startswith("# ") for l in lines) else "IC-MEMO")

    def flush_para():
        if para_buf:
            out.append("<p>" + inline(" ".join(para_buf)) + "</p>")
            para_buf.clear()

    def flush_table():
        if not table_buf:
            return
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table_buf]
        if len(rows) > 1 and set("".join(rows[1])) <= set("-: "):
            rows.pop(1)
        t = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr></thead><tbody>"]
        for r in rows[1:]:
            t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
        t.append("</tbody></table>")
        out.append("".join(t))
        table_buf.clear()

    for line in lines:
        if line.strip().startswith("```"):
            flush_para(); flush_table()
            if in_code:
                out.append('<pre class="yaml">' + esc("\n".join(code_buf)) + "</pre>")
                code_buf.clear()
            in_code = not in_code
            continue
        if in_code:
            code_buf.append(line)
            continue
        if line.strip().startswith("|"):
            flush_para()
            table_buf.append(line)
            continue
        flush_table()
        h = re.match(r"^(#{1,3})\s+(.*)", line)
        if h:
            flush_para()
            level = len(h.group(1))
            sid = slug(h.group(2))
            if level <= 2 and not line.startswith("# "):
                toc.append(f'<a href="#{sid}">{esc(h.group(2))}</a>')
            out.append(f'<h{level} id="{sid}">{inline(h.group(2))}</h{level}>')
        elif re.match(r"^-{3,}$", line.strip()):
            flush_para(); out.append("<hr>")
        elif line.startswith("> "):
            flush_para(); out.append("<blockquote>" + inline(line[2:]) + "</blockquote>")
        elif line.startswith("- "):
            flush_para()
            out.append("<ul><li>" + inline(line[2:]) + "</li></ul>")  # IC-MEMO lists are flat
        elif not line.strip():
            flush_para()
        else:
            para_buf.append(line.strip())
    flush_para(); flush_table()

    toc_html = "".join(toc) or "<em>(no sections)</em>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>
:root{{--bg:#0d1117;--panel:#161b22;--fg:#c9d1d9;--dim:#8b949e;--accent:#f2cc60;--link:#a5d6ff;--ok:#3fb950;--warn:#e3b341}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif}}
.layout{{display:flex;min-height:100vh}}
nav{{width:260px;flex:none;background:var(--panel);padding:24px 18px;border-right:1px solid #21262d;position:sticky;top:0;max-height:100vh;overflow:auto}}
nav b{{color:var(--accent);font-size:13px;letter-spacing:.06em;text-transform:uppercase}}
nav a{{display:block;color:var(--dim);text-decoration:none;font-size:13px;padding:5px 8px;border-radius:6px}}
nav a:hover{{color:var(--link);background:#1c2129}}
main{{flex:1;max-width:820px;margin:0 auto;padding:40px 32px}}
h1{{font-size:26px;margin:0 0 4px}}
h2{{font-size:19px;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid #21262d}}
h3{{font-size:16px;color:var(--accent);margin:24px 0 8px}}
pre.yaml{{background:var(--panel);border:1px solid #21262d;border-radius:10px;padding:14px 16px;overflow:auto;font:12.5px/1.5 ui-monospace,Menlo,Consolas,monospace;color:var(--link)}}
table{{border-collapse:collapse;margin:14px 0;width:100%}}
th,td{{border:1px solid #21262d;padding:7px 12px;text-align:left;font-size:14px}}
th{{color:var(--accent);background:var(--panel)}}
blockquote{{border-left:3px solid var(--accent);margin:12px 0;padding:2px 14px;color:var(--dim)}}
code{{background:var(--panel);border-radius:5px;padding:1px 5px;font-size:13px}}
ul{{padding-left:22px}} li{{margin:4px 0}}
hr{{border:0;border-top:1px solid #21262d;margin:28px 0}}
footer,.foot{{color:var(--dim);font-size:13px}}
@media(max-width:860px){{.layout{{display:block}}nav{{position:static;width:auto;border-right:0;border-bottom:1px solid #21262d}}nav a{{display:inline-block;margin:2px}}}}
@media print{{nav{{display:none}}body{{background:#fff;color:#111}}}}
</style></head>
<body><div class="layout">
<nav><b>IC-MEMO</b>{toc_html}</nav>
<main>{''.join(out)}
<p class="foot">Rendered by dsh-tradingagents · single-file page, no external assets · not investment advice</p>
</main></div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("memo", help="IC-MEMO markdown file")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()
    md = open(args.memo, encoding="utf-8").read()
    out = args.out or os.path.splitext(args.memo)[0] + ".html"
    open(out, "w", encoding="utf-8").write(render(md))
    print(f"html → {out}")


if __name__ == "__main__":
    main()
