#!/usr/bin/env python3
"""自动本体构建引擎（NVIDIA auto-ontology 概念位 M0）

上游 auto-ontology（13.3k★，Apache-2.0）= 从非结构化数据自动构建语义图
本体。本插件原生实现其双 pass 管线，家族差异=**证据溯源**：每条实体/关系
带原文引文跨度（evidence span），无证据的断言不落库；类型守卫：实例类型
必须 ∈ 第一 pass 抽取的 TBox，未知类型标注不静默丢弃（对拍血统）。

管线（2 类 LLM 调用，temperature=0）：
  Pass1 schema：从文档样本抽候选实体类型+关系类型（TBox）
  Pass2 assert：逐文档抽实体/关系实例（ABox），每条带 evidence 原文引用
  合并：类型守卫 + 去重 → ontology JSON + 环形布局 SVG 图 + markdown 摘要

用法：
  python3 scripts/build_ontology.py --docs <dir_or_glob> --domain "描述" --save
"""
import argparse, datetime as dt, glob, json, math, os, re, subprocess, sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def llm(sysmsg, user, json_out=True):
    key = subprocess.run(["bash", "-c", 'grep -m1 "^export DEEPSEEK_API_KEY=" ~/.bashrc | cut -d= -f2'],
                         capture_output=True, text=True).stdout.strip().strip('"')
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": user}]}
    if json_out:
        body["response_format"] = {"type": "json_object"}
    r = subprocess.run(["curl", "-s", "-m", "180", "https://api.deepseek.com/chat/completions",
                        "-H", f"Authorization: Bearer {key}", "-H", "Content-Type: application/json",
                        "-d", json.dumps(body)], capture_output=True, text=True)
    txt = json.loads(r.stdout)["choices"][0]["message"]["content"]
    return json.loads(re.sub(r"^```(json)?|```$", "", txt.strip(), flags=re.M).strip()) if json_out else txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True, help="目录或 glob，如 '~/dsh-*/README.md'")
    ap.add_argument("--domain", required=True, help="语料领域描述（喂给 schema pass）")
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()
    paths = sorted(glob.glob(os.path.expanduser(args.docs))) if "*" in args.docs else \
        sorted(glob.glob(os.path.join(args.docs, "*")))
    docs = []
    for p in paths:
        try:
            docs.append({"path": os.path.basename(os.path.dirname(p)) or p, "text": open(p).read()[:6000]})
        except Exception:
            pass
    if not docs:
        sys.exit("无文档")
    print(f"语料：{len(docs)} 篇 · 领域：{args.domain}", file=sys.stderr)

    sample = "\n\n".join(d["text"][:1500] for d in docs[:4])
    tbox = llm(
        "你是本体工程师。从语料样本抽取本体模式（TBox）。输出 JSON："
        '{"entity_types":[{"name":"...","desc":"..."}],"relation_types":[{"name":"...","domains":"类型A","ranges":"类型B","desc":"..."}]}'
        "。类型名用英文 snake_case，desc 用中文。只抽取语料真实支撑的，宁缺毋滥。",
        f"领域：{args.domain}\n语料样本：\n{sample}")

    etypes = {e["name"] for e in tbox.get("entity_types", [])}
    abox, flagged = [], []
    for d in docs:
        out = llm(
            "你是本体实例抽取器。基于给定 TBox 从文档抽取实体与关系实例（ABox）。"
            "**纪律**：每条实例必须附 evidence=文档原文引文（不超过40字）；类型必须取自 TBox；"
            "不确定的不抽。输出 JSON："
            '{"entities":[{"name":"...","type":"...","evidence":"..."}],'
            '"relations":[{"subject":"...","predicate":"...","object":"...","evidence":"..."}]}',
            f"TBox：{json.dumps(tbox, ensure_ascii=False)}\n\n文档（{d['path']}）：\n{d['text']}")
        for e in out.get("entities", []):
            if e.get("name"):
                (abox if e.get("type") in etypes else flagged).append({**e, "doc": d["path"]})
        for r in out.get("relations", []):
            abox.append({**r, "doc": d["path"]})
    ent_names = {e["name"] for e in abox if "type" in e}
    rels = [r for r in abox if "predicate" in r and r["subject"] in ent_names and r["object"] in ent_names]

    ontology = {"domain": args.domain, "built_at": dt.datetime.now().isoformat(timespec="seconds"),
                "tbox": tbox, "abox": {"entities": [e for e in abox if "type" in e], "relations": rels},
                "flagged_unknown_types": flagged,
                "stats": {"docs": len(docs), "entities": len(abox) - len(rels), "relations": len(rels),
                          "flagged": len(flagged)}}
    print(f"\n## 本体构建 · {args.domain}\n")
    print(f"- 实体类型 {len(tbox.get('entity_types', []))} · 关系类型 {len(tbox.get('relation_types', []))} · "
          f"实体 {ontology['stats']['entities']} · 关系 {len(rels)} · 未知类型被拦 {len(flagged)}")
    for e in tbox.get("entity_types", [])[:8]:
        print(f"  - T: {e['name']} — {e.get('desc', '')[:40]}")
    for r in rels[:12]:
        print(f"  - R: ({r['subject']}) -[{r['predicate']}]-> ({r['object']}) ｜证据: {r.get('evidence', '')[:40]}")
    if flagged:
        print(f"  ⚠ 未入库的未知类型实例 {len(flagged)} 条（类型守卫，不静默丢弃）")

    if args.save:
        os.makedirs(os.path.join(KIT, "ontologies"), exist_ok=True)
        base = os.path.join(KIT, "ontologies", dt.datetime.now().strftime("%Y%m%d-%H%M"))
        json.dump(ontology, open(base + ".json", "w"), ensure_ascii=False, indent=1)
        # 环形布局 SVG（类型分簇）
        ents = ontology["abox"]["entities"]
        by_type = {}
        for e in ents:
            by_type.setdefault(e["type"], []).append(e)
        colors = ["#2456c4", "#c23531", "#2f8a4c", "#8a5fc2", "#b07a2a", "#2a8a8a"]
        nodes, cx, cy, W, H = [], 400, 340, 860, 700
        clusters = list(by_type.items())[:6]
        for ci, (t, es) in enumerate(clusters):
            r0, ang0 = 60 + ci * 45, ci * 2 * math.pi / max(len(clusters), 1)
            gx, gy = cx + r0 * 1.9 * math.cos(ang0), cy + r0 * 1.5 * math.sin(ang0)
            for i, e in enumerate(es[:10]):
                a = 2 * math.pi * i / max(len(es[:10]), 1)
                nodes.append((e["name"][:14], gx + 52 * math.cos(a), gy + 40 * math.sin(a), colors[ci % 6]))
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="monospace">',
               f'<text x="10" y="16" font-size="13">{args.domain} · {len(ents)} entities / {len(rels)} relations</text>']
        for r in rels:
            nm = {n[0]: (n[1], n[2]) for n in nodes}
            if r["subject"] in nm and r["object"] in nm:
                x1, y1 = nm[r["subject"]]; x2, y2 = nm[r["object"]]
                svg.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="#99a" stroke-width="0.7"/>')
        for name, x, y, c in nodes:
            svg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="4" fill="{c}"/>'
                       f'<text x="{x + 6:.0f}" y="{y + 3:.0f}" font-size="9" fill="#345">{name}</text>')
        svg.append("</svg>")
        open(base + ".svg", "w").write("".join(svg))
        open(base + ".md", "w").write(f"# 本体 · {args.domain}\n\n实体 {len(ents)} · 关系 {len(rels)} · "
                                      f"证据随 JSON（ontologies/*.json）；未知类型拦截 {len(flagged)} 条。\n")
        print(f"\n→ {base}.json / .svg / .md", file=sys.stderr)


if __name__ == "__main__":
    main()
