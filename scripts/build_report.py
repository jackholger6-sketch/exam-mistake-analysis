#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_report.py —— 把 report.json 渲染成错题分析报告 HTML（图片以 base64 内嵌，单文件可发微信）

用法:
    python build_report.py report.json -o 错题分析.html

设计约束（本技能的硬规则）:
  1. 正文错题卡里【只放题目】，答案一律放到最后一页的"参考答案"区。
  2. 复习表按艾宾浩斯 1/3/7/15/30 天从"批改日期"起算，每轮一个可打钩的方框。
  3. 单文件输出：证据截图 base64 内嵌，不依赖外部目录。
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import sys

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "report-template.html")
WEEK_CN = "一二三四五六日"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def parse_date(s):
    s = (s or "").strip().replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y%m%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise SystemExit("日期格式无法识别: %r（要 2026-11-11 这种）" % s)


def img_uri(path, base_dir):
    p = path if os.path.isabs(path) else os.path.join(base_dir, path)
    if not os.path.exists(p):
        raise SystemExit("找不到证据图: %s" % p)
    ext = os.path.splitext(p)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(p, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def review_text(idx, offsets, errors, prac_total):
    n = len(errors)
    heavy = sorted(errors, key=lambda e: -float(e.get("deduct", 0)))[:2]
    heavy_no = "、".join(e["no"] for e in heavy) if heavy else ""
    if idx == 0:
        return "全部 %d 道错题<b>原题重做</b>（不看答案），只要求写出算式和答案" % n
    if idx == 1:
        return "全部 %d 道原题再做一遍，每道再配 1 道变式" % n
    if idx == 2:
        return "重点看扣分最多的 %s，原题＋对应变式各做一遍" % heavy_no
    if idx == 3:
        return "把 %d 道变式<b>全部</b>做一遍（这一轮检验「是不是真的会了」）" % prac_total
    return "随机抽 3 道原题 + 3 道变式，<b>限时</b>做完，模拟考试手感"


def build(data, base_dir):
    m = data.get("meta", {})
    errors = data.get("errors", [])
    if not errors:
        raise SystemExit("report.json 里 errors 是空的，没有可分析的错题")

    graded = parse_date(m.get("graded_date") or dt.date.today().isoformat())
    offsets = m.get("review_offsets") or [1, 3, 7, 15, 30]
    prac_total = sum(len(e.get("practice", [])) for e in errors)
    total_deduct = sum(float(e.get("deduct", 0)) for e in errors)
    full = m.get("full_score")

    # ---- 分数 chips ----
    chips = data.get("scorechips")
    if not chips:
        chips = []
        if m.get("score") is not None:
            chips.append({"v": m["score"], "l": "本次得分"})
        chips.append({"v": len(errors), "l": "失分点"})
        chips.append({"v": "-%g" % total_deduct, "l": "共扣 %g 分" % total_deduct})
        if m.get("top_note"):
            chips.append({"v": m["top_note"][0], "l": m["top_note"][1]})
    chips_html = "".join(
        '<div class="scorechip"><b>%s</b><span>%s</span></div>' % (esc(c["v"]), esc(c["l"])) for c in chips
    )

    # ---- 失分条 ----
    bars = data.get("bars", [])
    mx = max([float(b["points"]) for b in bars], default=1) or 1
    bars_html = "".join(
        '<div class="bar"><span class="nm">%s</span><span class="track">'
        '<span class="fill" style="width:%.1f%%"></span></span><span class="val">%g 分</span></div>'
        % (esc(b["name"]), max(2.0, float(b["points"]) / mx * 100), float(b["points"]))
        for b in bars
    )

    # ---- 总表 ----
    rows = "".join(
        '<tr><td><b>%s</b></td><td>%s</td><td><span class="tag t-red">-%g</span></td><td>%s</td><td>%s</td></tr>'
        % (esc(e["no"]), esc(e.get("type", "")), float(e["deduct"]), esc(e.get("topic", "")), esc(e.get("brief", "")))
        for e in errors
    )

    # ---- 错题卡（正文只给题，不给答案）----
    cards = []
    for i, e in enumerate(errors, 1):
        img_html = ""
        if e.get("image"):
            img_html = (
                '<figure class="ev"><img src="%s" alt="原卷 %s 作答">'
                '<figcaption>%s</figcaption></figure>' % (img_uri(e["image"], base_dir), esc(e["no"]), e.get("caption", ""))
            )
        diag = "".join("<li>%s</li>" % d for d in e.get("diagnosis", []))
        steps = ""
        if e.get("teach_steps"):
            steps = '<ol class="steps">%s</ol>' % "".join("<li>%s</li>" % s for s in e["teach_steps"])
        formula = ""
        if e.get("teach_formula"):
            formula = '<p style="margin-top:8px">%s</p>' % "".join(
                '<span class="formula">%s</span>　' % f for f in
                (e["teach_formula"] if isinstance(e["teach_formula"], list) else [e["teach_formula"]])
            )
        extra = e.get("teach_extra") or ""
        prac = "".join("<li>%s</li>" % q for q in e.get("practice", []))
        tip = '<div class="tip">%s</div>' % e["practice_tip"] if e.get("practice_tip") else ""
        cards.append(
            """
  <article class="card">
    <div class="head">
      <div class="num">%02d</div>
      <h3>%s　%s</h3>
      <span class="pts">-%g 分</span>
    </div>
    <div class="body">
      <div class="qbox">
        <div class="lbl">原题</div>
        %s
      </div>
      %s
      <div class="abox">
        <div class="ans wrong"><div class="lbl">孩子作答</div>%s</div>
        <div class="ans right"><div class="lbl">正确答案</div>%s</div>
      </div>
      <div class="diag">
        <div class="lbl">诊断：错在哪</div>
        <ul>%s</ul>
      </div>
      <div class="teach">
        <div class="lbl">%s</div>
        %s%s%s
      </div>
      <div class="prac">
        <div class="lbl">举一反三 · 同类型 %d 题</div>
        <ol>%s</ol>%s
        <div class="tip" style="color:#a8526d;font-weight:600;margin-top:8px">答案在最后一页 · 先做完再看</div>
      </div>
    </div>
  </article>"""
            % (
                i, esc(e["no"]), e.get("card_title", ""), float(e["deduct"]),
                e.get("question", ""), img_html,
                e.get("student", ""), e.get("correct", ""),
                diag,
                e.get("teach_title", "正确思路"), steps, formula, extra,
                len(e.get("practice", [])), prac, tip,
            )        )

    # ---- 复习表 ----
    rev_rows = []
    for idx, off in enumerate(offsets):
        d = graded + dt.timedelta(days=int(off))
        label = "第 %d 轮" % (idx + 1)
        key = "%s_r%d" % (graded.isoformat(), off)
        rev_rows.append(
            '<tr><td class="rno">%s</td><td class="rdate">%s<small>周%s</small></td>'
            '<td class="rday">+%s 天</td><td>%s</td>'
            '<td><input type="checkbox" class="chk" data-k="%s"><span class="cktxt">未完成</span></td></tr>'
            % (label, d.isoformat(), WEEK_CN[d.weekday()], off,
               review_text(idx, offsets, errors, prac_total), key)
        )

    # ---- 最后一页：答案 ----
    ans_sections = []
    for i, e in enumerate(errors, 1):
        ans = e.get("answers") or []
        if not ans:
            continue
        ans_sections.append(
            '<div class="agroup"><div class="gh"><div class="gno">%02d</div>'
            '<div class="gt">%s　%s</div></div><div class="gb">%s</div></div>'
            % (i, esc(e["no"]), e.get("card_title", ""),
               "".join("<p>%s</p>" % a for a in ans))
        )
    if not ans_sections:
        ans_sections = ['<p class="muted">（本次未生成变式，或答案缺失）</p>']

    # ---- 一周计划 ----
    plan = data.get("week_plan") or []
    plan_html = "".join(p if p.strip().startswith("<") else "<p>%s</p>" % p for p in plan)
    if data.get("callout"):
        plan_html += '<div class="callout">%s</div>' % data["callout"]

    rid = hashlib.md5((data.get("title", "") + graded.isoformat()).encode("utf-8")).hexdigest()[:10]

    with open(TEMPLATE, encoding="utf-8") as f:
        tpl = f.read()

    repl = {
        "{{TITLE}}": esc(data.get("title", "错题分析与举一反三")),
        "{{KICKER}}": data.get("kicker", "试卷逐题批改还原 · 错因诊断 · 举一反三"),
        "{{H1}}": data.get("h1", "错题清单 · 知识点诊断 · 举一反三"),
        "{{SUBTITLE}}": data.get("subtitle", ""),
        "{{SCORECHIPS}}": chips_html,
        "{{GRADED_DATE}}": graded.isoformat(),
        "{{GENERATED_AT}}": m.get("generated_at") or dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "{{REVIEW_START}}": graded.isoformat() + "（批改当天）",
        "{{BARS}}": bars_html,
        "{{CONCLUSION}}": data.get("conclusion", ""),
        "{{TABLE_ROWS}}": rows,
        "{{ERROR_COUNT}}": str(len(errors)),
        "{{CARDS}}": "".join(cards),
        "{{REVIEW_ROWS}}": "".join(rev_rows),
        "{{WEEK_PLAN}}": plan_html,
        "{{PRACTICE_COUNT}}": str(prac_total),
        "{{ANSWER_SECTIONS}}": "".join(ans_sections),
        "{{REPORT_ID}}": rid,
        "{{FOOT}}": data.get("foot", ""),
    }
    out = tpl
    for k, v in repl.items():
        out = out.replace(k, v)
    left = [k for k in repl if k in out]
    if left:
        print("警告：模板里还有未替换的占位符 %s" % left, file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    with open(a.json, encoding="utf-8") as f:
        data = json.load(f)
    html = build(data, os.path.dirname(os.path.abspath(a.json)))
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print("ok -> %s (%.0f KB)" % (a.out, len(html.encode()) / 1024))


if __name__ == "__main__":
    main()
