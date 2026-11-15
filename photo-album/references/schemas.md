# 分组与导出格式

## 逐页稿

`plan_album.py` 接受 JSON 的 `pages` 数组。顺序就是阅读顺序，`page` 从 1 连续递增。每页有 `photos` 数组，每张照片有 `id` 和原片 `path`；诗句可用 `poem` 字符串，或原稿格式 `quote: {"quote": "原文"}`。若存在 `photo_ids`，必须与该页照片顺序一致；若存在 `sha256`，会验证。

```json
{"pages":[
  {"page":1,"photos":[{"id":"p1","path":"originals/one.jpg"}],"poem":"第一组诗句"},
  {"page":2,"photos":[{"id":"p2","path":"originals/two.jpg"}],"quote":{"quote":"第二组诗句"}}
]}
```

路径相对逐页稿目录。脚本不移动照片、不重新选片；相同照片跨页出现只记录重复，不擅自删除。奇数页不能静默补空白页。

```bash
python scripts/plan_album.py manuscript.json --out work/pairing.json
```

输出保留每页照片和诗句、实际原片 SHA-256，并按相邻两组配对。`photos[].path` 为原片来源，不改用 `preview_file`。

## PDF 页面清单

```json
{"page_mm":[210,285],"images":["pages/01.png","pages/02.png"]}
```

路径相对清单。单页清单按阅读顺序列出左右页；跨页清单按跨页顺序列图，`page_mm` 改为 `[420,285]`。图片比例必须匹配页面，默认无损嵌入，不拉伸错比例图片。

```bash
python scripts/export_pdf.py pages.json --out book.pdf
python scripts/export_pdf.py opening-pages.json --append-pdf old-book.pdf --out new-book.pdf
```

旧 PDF 页面尺寸须一致，输出不能覆盖输入或现有文件。插页后报告总页数，验证旧页内容和图像流未改变。调用者按 PDF 技能在首次创建/编辑前执行操作标记；脚本不伪造渲染审阅结果。
