# wiki_fetch - 中文维基百科抓取工具

使用 MediaWiki Action API 抓取维基百科页面的结构化数据。

## 功能

抓取并保存 3 份 JSON 文件：

| 文件 | 内容 | 用途 |
|------|------|------|
| `*.parse.json` | 渲染 HTML、sections、links、images、categories | RAG 文本处理 |
| `*.imageinfo.json` | 图片 URL、MIME、尺寸 | 多模态方案 |
| `*.pageprops.json` | wikibase_item 等属性 | KG 实体对齐 |

## 安装依赖

```bash
uv add requests
```

## 使用方法

```bash
# 基本用法
uv run python src/utils/wiki_fetch/fetch_wiki_page.py --page "火影忍者"

# 指定输出目录
uv run python src/utils/wiki_fetch/fetch_wiki_page.py --page "火影忍者" --outdir "data/raw/wiki"

# 调整批量大小（默认 40）
uv run python src/utils/wiki_fetch/fetch_wiki_page.py --page "火影忍者" --batch-size 20

# 抓取英文维基
uv run python src/utils/wiki_fetch/fetch_wiki_page.py --page "Naruto" --lang en
```

## 输出示例

```
data/raw/wiki/
├── zhwiki_火影忍者.parse.json
├── zhwiki_火影忍者.imageinfo.json
└── zhwiki_火影忍者.pageprops.json
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--page` | (必填) | 维基百科页面标题 |
| `--outdir` | `data/raw/wiki` | 输出目录 |
| `--batch-size` | `40` | ImageInfo 批量请求大小 |
| `--lang` | `zh` | 维基百科语言代码 |
