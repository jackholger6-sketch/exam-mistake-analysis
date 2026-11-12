#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prep_sheet.py —— 把试卷扫描件（PDF / 图片）转成可读的页面图

优先用 PyMuPDF 渲染整页（最忠实，含空白与批改痕迹）；
PyMuPDF 不可用时退化为「抽取 PDF 内嵌 JPEG」（扫描件通常就是一页一张图）。

用法:
    python prep_sheet.py 卷子.pdf -o pages --dpi 170
    python prep_sheet.py 卷子.jpg -o pages
"""
import argparse
import os
import re
import sys


def via_pymupdf(pdf, outdir, dpi):
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return 0
    doc = pymupdf.open(pdf)
    n = 0
    for i, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=dpi)
        p = os.path.join(outdir, "page_%02d.png" % i)
        pix.save(p)
        print("page %d -> %s  %dx%d" % (i, p, pix.width, pix.height))
        n += 1
    return n


def via_streams(pdf, outdir):
    with open(pdf, "rb") as f:
        data = f.read()
    n = 0
    for m in re.finditer(rb"/Subtype\s*/Image", data):
        head = data[max(0, m.start() - 2000):m.start() + 2000]
        if b"DCTDecode" not in head:
            continue
        s = data.find(b"\xff\xd8\xff", m.start())
        e = data.find(b"\xff\xd9", s)
        if s < 0 or e < 0 or e - s < 20000:
            continue
        n += 1
        p = os.path.join(outdir, "img_%02d.jpg" % n)
        with open(p, "wb") as o:
            o.write(data[s:e + 2])
        print("embedded jpeg -> %s (%.0f KB)" % (p, (e - s) / 1024))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--dpi", type=int, default=170)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    if a.src.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        print("已经是图片，直接读：%s" % a.src)
        return

    n = via_pymupdf(a.src, a.outdir, a.dpi)
    if n == 0:
        print("PyMuPDF 不可用，改用抽取内嵌图片……", file=sys.stderr)
        print("（要装的话：python -m pip install pymupdf -i https://pypi.tuna.tsinghua.edu.cn/simple）", file=sys.stderr)
        n = via_streams(a.src, a.outdir)
    if n == 0:
        raise SystemExit("没能从这份 PDF 里取到页面。请让用户导出为图片，或用手机重新拍一页一张的照片。")
    print("共 %d 张，下一步：逐张用看图工具读题，再裁剪错题证据图。" % n)


if __name__ == "__main__":
    main()
