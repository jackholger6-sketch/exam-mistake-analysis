#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_pdf.py —— 把报告 HTML 打成 A4 PDF（用本机 Edge/Chrome，无需下载浏览器）

用法:
    python make_pdf.py 错题分析.html -o 错题分析.pdf

原理：Playwright launch(channel=msedge)，page.pdf()。打印样式已在模板里写好（@page A4、分页规则）。
"""
import argparse
import pathlib
import sys


def to_url(p):
    return "file:///" + str(pathlib.Path(p).resolve()).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        err = None
        for ch in ("msedge", "chrome", None):
            try:
                b = pw.chromium.launch(channel=ch) if ch else pw.chromium.launch()
                pg = b.new_page(viewport={"width": 1000, "height": 1400})
                pg.goto(to_url(a.html), wait_until="load")
                pg.wait_for_timeout(900)
                pg.emulate_media(media="print")
                pg.pdf(path=a.out, format="A4", print_background=True,
                       margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"})
                b.close()
                print("ok -> %s  (channel=%s)" % (a.out, ch or "bundled"))
                return
            except Exception as e:  # noqa: BLE001
                err = e
                continue
        raise SystemExit("PDF 生成失败：%s\n提示：确认本机装有 Edge 或 Chrome；或直接让用户用浏览器「打印 → 另存为 PDF」。" % str(err)[:300])


if __name__ == "__main__":
    main()
