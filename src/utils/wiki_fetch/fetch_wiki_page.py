#!/usr/bin/env python3
"""
中文维基百科页面抓取工具

使用 MediaWiki Action API 抓取指定页面的：
- Parse 数据（渲染HTML、sections、links、images等）
- ImageInfo 数据（图片URL、MIME、尺寸）
- PageProps 数据（用于KG实体对齐的 wikibase_item 等）
"""

import argparse
import json
import re
import time
from pathlib import Path

import requests

# API 端点模板
API_ENDPOINT_TEMPLATE = "https://{lang}.wikipedia.org/w/api.php"

# User-Agent（遵守维基媒体 API 礼仪）
USER_AGENT = "RACG-WikiFetch/1.0 (https://github.com/user/racg; educational project)"


def sanitize_filename(title: str) -> str:
    """
    将页面标题转换为安全的文件名（跨平台兼容）
    """
    # 替换 Windows/macOS/Linux 不允许的字符
    # Windows: \ / : * ? " < > |
    # macOS/Linux: / 和 NUL
    sanitized = re.sub(r'[\\/:*?"<>|]', "_", title)
    # 移除首尾空白和点（Windows 不允许文件名以点结尾）
    sanitized = sanitized.strip().strip(".")
    # 限制长度（保守起见限制 100 字符）
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized


def make_request(url: str, params: dict) -> dict:
    """
    发送 API 请求并返回 JSON 响应
    """
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, params=params, headers=headers, timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")

    data = resp.json()

    # 检查 API 级别错误
    if "error" in data:
        err = data["error"]
        raise RuntimeError(f"API Error [{err.get('code')}]: {err.get('info')}")

    return data


def fetch_parse(api_url: str, page: str) -> dict:
    """
    抓取 action=parse 数据
    """
    params = {
        "action": "parse",
        "page": page,
        "prop": "text|sections|links|images|categories|externallinks",
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
    }
    return make_request(api_url, params)


def fetch_imageinfo(api_url: str, image_files: list[str], batch_size: int) -> dict:
    """
    批量抓取图片信息
    """
    all_pages = {}

    # 分批处理
    for i in range(0, len(image_files), batch_size):
        batch = image_files[i : i + batch_size]
        # 构造 File:xxx 格式的标题
        titles = "|".join(f"File:{img}" for img in batch)

        params = {
            "action": "query",
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "titles": titles,
            "format": "json",
            "formatversion": 2,
        }

        data = make_request(api_url, params)

        # 合并结果
        pages = data.get("query", {}).get("pages", [])
        for page in pages:
            all_pages[page.get("title", "")] = page

        # 防限流
        if i + batch_size < len(image_files):
            time.sleep(0.2)

    return {"query": {"pages": list(all_pages.values())}}


def fetch_pageprops(api_url: str, page: str) -> dict:
    """
    抓取 action=query prop=pageprops 数据
    """
    params = {
        "action": "query",
        "prop": "pageprops",
        "redirects": 1,
        "titles": page,
        "format": "json",
        "formatversion": 2,
    }
    return make_request(api_url, params)


def save_json(data: dict, filepath: Path) -> None:
    """
    保存 JSON 文件（UTF-8 编码，格式化输出）
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def print_summary(parse_data: dict, imageinfo_data: dict, pageprops_data: dict) -> None:
    """
    打印抓取摘要统计
    """
    print("\n" + "=" * 50)
    print("抓取完成 - 摘要统计")
    print("=" * 50)

    # Parse 统计
    parse = parse_data.get("parse", {})
    sections = parse.get("sections", [])
    links = parse.get("links", [])
    images = parse.get("images", [])
    categories = parse.get("categories", [])
    externallinks = parse.get("externallinks", [])

    print(f"Sections:      {len(sections)}")
    print(f"Links:         {len(links)}")
    print(f"Images:        {len(images)}")
    print(f"Categories:    {len(categories)}")
    print(f"ExternalLinks: {len(externallinks)}")

    # ImageInfo 统计
    pages = imageinfo_data.get("query", {}).get("pages", [])
    url_count = sum(
        1
        for p in pages
        if p.get("imageinfo") and p["imageinfo"][0].get("url")
    )
    print(f"ImageInfo URL: {url_count}/{len(pages)}")

    # PageProps 统计
    props_pages = pageprops_data.get("query", {}).get("pages", [])
    if props_pages:
        pageprops = props_pages[0].get("pageprops", {})
        wikibase_item = pageprops.get("wikibase_item", "(无)")
        print(f"Wikibase Item: {wikibase_item}")

    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="抓取中文维基百科页面数据（Parse/ImageInfo/PageProps）"
    )
    parser.add_argument(
        "--page",
        required=True,
        help="维基百科页面标题，如 '火影忍者'",
    )
    parser.add_argument(
        "--outdir",
        default="data/raw/wiki",
        help="输出目录（默认: data/raw/wiki）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=40,
        help="ImageInfo 批量请求大小（默认: 40）",
    )
    parser.add_argument(
        "--lang",
        default="zh",
        help="维基百科语言代码（默认: zh）",
    )

    args = parser.parse_args()

    # 构造 API URL
    api_url = API_ENDPOINT_TEMPLATE.format(lang=args.lang)

    # 创建输出目录
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 文件名前缀
    safe_title = sanitize_filename(args.page)
    prefix = f"{args.lang}wiki_{safe_title}"

    print(f"正在抓取: {args.page}")
    print(f"API: {api_url}")
    print(f"输出目录: {outdir.absolute()}")

    # 1. 抓取 Parse 数据
    print("\n[1/3] 抓取 Parse 数据...")
    parse_data = fetch_parse(api_url, args.page)
    parse_file = outdir / f"{prefix}.parse.json"
    save_json(parse_data, parse_file)
    print(f"  -> {parse_file}")

    # 2. 抓取 ImageInfo 数据
    print("\n[2/3] 抓取 ImageInfo 数据...")
    images = parse_data.get("parse", {}).get("images", [])
    if images:
        imageinfo_data = fetch_imageinfo(api_url, images, args.batch_size)
    else:
        imageinfo_data = {"query": {"pages": []}}
    imageinfo_file = outdir / f"{prefix}.imageinfo.json"
    save_json(imageinfo_data, imageinfo_file)
    print(f"  -> {imageinfo_file} ({len(images)} images)")

    # 3. 抓取 PageProps 数据
    print("\n[3/3] 抓取 PageProps 数据...")
    pageprops_data = fetch_pageprops(api_url, args.page)
    pageprops_file = outdir / f"{prefix}.pageprops.json"
    save_json(pageprops_data, pageprops_file)
    print(f"  -> {pageprops_file}")

    # 打印摘要
    print_summary(parse_data, imageinfo_data, pageprops_data)


if __name__ == "__main__":
    main()
