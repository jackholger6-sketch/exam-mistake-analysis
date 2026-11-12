---
name: exam-mistake-analysis
description: 把孩子的试卷/作业扫描件做成一份「错题清单 + 知识点诊断 + 举一反三」报告。逐题判读红笔批改痕迹、还原孩子答案与正确答案、诊断知识漏洞与思维断点、按错因出同类型变式（答案统一放最后一页），并附艾宾浩斯遗忘曲线复习表（1/3/7/15/30 天，复习一次打一个钩）。当用户说「分析错题 / 整理错题 / 错题本 / 试卷分析 / 这张卷子哪里错了 / 出点同类型的题 / 举一反三」时使用。
---

# 错题分析报告（试卷 → 诊断 → 举一反三）

把一张批改过的卷子，做成家长能直接看懂、孩子能直接练的一份报告。

## 输出物

在工作区 `output/` 下产出两个同名文件：

| 文件 | 用途 |
|---|---|
| `错题分析与举一反三_<年级><科目>.html` | 交互版，单文件（截图 base64 内嵌），手机上可看，复习表可点着打钩 |
| `错题分析与举一反三_<年级><科目>（含答案）.pdf` | 打印版，A4，直接打印或发微信 |

## 六步流程

### Step 1　收料
用户给的通常是扫描 PDF 或几张照片。先落到工作区 `input/`。

```bash
python <skill>/scripts/prep_sheet.py 卷子.pdf -o input/pages --dpi 170
```
- 优先 PyMuPDF 整页渲染；不可用时自动退化为「抽取 PDF 内嵌 JPEG」。
- 两种都失败 → 直接告诉用户：这份 PDF 读不出来，请导出成图片或重新拍照。**不要凭想象猜题。**

### Step 2　判读卷面（最关键，别跳）
逐张看页面图。判读顺序：

1. **先找扣分数字**（页边/题号旁的 `−1 −2 −5 −10 −7`）→ 这些就是错题，最可靠。
2. **再找红叉 `✗`** → 有时老师只打叉不写分数。
3. **红色 `?`** → 孩子留白没写（不是算错，是没思路）。
4. **长弧线 `✓`** → 对，别当错题。
5. **自己把每道可疑题重算一遍**，确认「孩子答案」和「正确答案」两个都拿到手。

细节见 `references/grader-marks.md`。

判读时逐题记录四件事：**题号 / 孩子写了什么 / 正确答案 / 扣几分**。看不清的地方放大到 5～8 倍再看（`crop.py --grid` 先出带坐标网格的图，方便量框）。

### Step 3　裁证据图
每道错题裁一张「只含这道题」的小图，宽度 900px 左右。

```bash
python <skill>/scripts/crop.py input/pages/page_01.png 860,872,1400,940 input/evidence/e1.jpg --grid   # 先看网格
python <skill>/scripts/crop.py input/pages/page_01.png 860,872,1400,940 input/evidence/e1.jpg --width 900
```
裁完**一定回看一次**：图里有没有把关键行切掉半截、有没有混进别的题。截图是这份报告的可信度来源，切歪了家长一眼就看出来。

### Step 4　写 `report.json`
按 `references/report-schema.md` 填。核心几条：

- `meta.graded_date`：**必填**，老师批改那天（不知道就问用户，或按扫描件日期）。复习表从这天起算。
- 每道错题 `diagnosis` 要分三层写：**知识漏洞 / 思维断点 / 习惯问题**，别只写「粗心」。
- `teach_steps` 是给孩子的动作（"先…再…最后…"），不是知识讲解。
- `practice` 3～4 题，且要真的「同类型」：同一模型换情境、换数字、换问法，**不要出同一题的数字微调**。
- `answers` 和 `practice` 一一对应，写在**最后一页**，正文里绝不出现答案。

### Step 5　生成

```bash
python <skill>/scripts/build_report.py report.json -o output/错题分析与举一反三_四年级上册数学.html
python <skill>/scripts/make_pdf.py output/xxx.html -o "output/错题分析与举一反三_四年级上册数学（含答案）.pdf"
```

### Step 6　自检后再交付
用 Playwright 截几张图（或 `pymupdf` 渲染 PDF 页）看一遍：
- 失分条的红色进度条有没有显示（`.fill` 必须 `display:block`）
- 每张证据图是不是对得上这道题
- **最后一页答案是不是完整、没有截断**
- 打印版有没有把卡片切成两半（分页规则在模板 `@media print` 里）

确认无误后 `present_files` 两个文件一起给。

## 铁律

1. **答案只在最后一页**。正文错题卡里只出现「举一反三」的题目，配一句「答案在最后一页 · 先做完再看」。这是本技能的固定设计，不要改回每题折叠。
2. **不臆造卷面**。看不清的因数、数字，按孩子笔迹推断后必须在报告里注明「按推断还原，以原卷为准」，并把不确定点告诉用户。
3. **日期三件套**：封面写「批改日期 / 报告生成 / 复习起点」，复习表从**批改日期**起算，不用今天。
4. **复习表 5 轮**：+1、+3、+7、+15、+30 天。每轮一个打钩方框（HTML 可点、打印可手写）。没打钩不补，按下一轮日期继续。
5. **扣分要对得上**：`sum(deduct) + 得分 = 满分`，写完自己核一遍。
6. **诚实结论**。如果孩子计算板块其实很稳、分全丢在审题上，就明说「不用加练计算题」——家长最怕的是笼统地说"基础不牢"。

## 常见坑

| 现象 | 处理 |
|---|---|
| 扫描件是纯图片 PDF，`workbuddy-pdf` 读不出 | 用 `prep_sheet.py` 的抽取内嵌图路径，纯 Python 正则找 `DCTDecode` 流 |
| bash 里传中文路径给 python -c 出错 | 一律写成 `.py` 脚本文件再执行，别用 `-c` 塞中文路径 |
| `/Subtype/Image` 抓到的图尺寸太小是图标 | 过滤掉小于 20KB 的流 |
| PDF 导出后某页大片空白 | `@media print` 里给 `.card` 用 `break-inside:auto`，只在 `.qbox/.abox/.diag/.teach/.prac/figure.ev` 上 `avoid` |
| 条形图没颜色 | `.track` / `.fill` 是 `span`，必须显式 `display:block` |

## 文件

```
exam-mistake-analysis/
├─ SKILL.md
├─ assets/report-template.html      报告模板（改版式只改这里）
├─ scripts/prep_sheet.py            卷子 → 页面图
├─ scripts/crop.py                  页面图 → 证据小图 / 网格参考图
├─ scripts/build_report.py          report.json → HTML（含复习表、答案页）
├─ scripts/make_pdf.py              HTML → A4 PDF
├─ references/report-schema.md      report.json 字段说明
├─ references/grader-marks.md       批改符号判读 + 错因分类
└─ examples/四年级数学_report.json   完整样例（可直接照着改）
```
