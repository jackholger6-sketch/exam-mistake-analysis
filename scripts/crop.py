#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crop.py —— 从整页图里裁出一块并放大，做成"卷面证据图"

用法:
    python crop.py page_01.png 860,872,1400,940 evidence/e1.jpg --width 900
    python crop.py page_01.png 860,872,1400,940 e1.jpg --scale 3

要点:
  - 裁得紧一点：一张图只说明一道题，图里出现别的题会让人分心。
  - 输出宽度统一 900px 左右，报告里视觉最舒服，PDF 也不会太大。
"""
import argparse
import os
from PIL import Image


def parse_box(s):
    parts = [p for p in s.replace("，", ",").split(",") if p.strip()]
    if len(parts) != 4:
        raise SystemExit("框要写 x0,y0,x1,y1 四个数")
    return tuple(int(float(p)) for p in parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("box")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=900)
    ap.add_argument("--scale", type=float, default=0)
    ap.add_argument("--grid", action="store_true", help="先输出带坐标网格的参考图，方便量框")
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGB")

    if a.grid:
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        for x in range(0, im.width, 100):
            d.line([(x, 0), (x, im.height)], fill=(0, 120, 255), width=1)
            d.text((x + 2, 2), str(x), fill=(0, 0, 255))
        for y in range(0, im.height, 100):
            d.line([(0, y), (im.width, y)], fill=(255, 140, 0), width=1)
            d.text((2, y + 2), str(y), fill=(255, 80, 0))
        out = os.path.splitext(a.out)[0] + "_grid.jpg"
        im.save(out, quality=90)
        print("grid -> %s  (%dx%d)" % (out, im.width, im.height))
        return

    x0, y0, x1, y1 = parse_box(a.box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(im.width, x1), min(im.height, y1)
    if x1 - x0 < 20 or y1 - y0 < 20:
        raise SystemExit("框太小了：%s" % (a.box,))
    c = im.crop((x0, y0, x1, y1))
    if a.scale:
        c = c.resize((int(c.width * a.scale), int(c.height * a.scale)), Image.LANCZOS)
    elif c.width != a.width:
        c = c.resize((a.width, int(c.height * a.width / c.width)), Image.LANCZOS)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if a.out.lower().endswith(".png"):
        c.save(a.out)
    else:
        c.convert("RGB").save(a.out, quality=86, optimize=True)
    print("ok -> %s  %dx%d  %.0f KB" % (a.out, c.width, c.height, os.path.getsize(a.out) / 1024))


if __name__ == "__main__":
    main()
