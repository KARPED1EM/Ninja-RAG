"""
中文维基百科页面批量抓取工具

使用 MediaWiki Action API 抓取指定页面的：
- Parse 数据（渲染HTML、sections、links、images等）
- ImageInfo 数据（图片URL、MIME、尺寸）
- PageProps 数据（用于KG实体对齐的 wikibase_item 等）

从 targets.txt 读取词条列表，支持分类注释
"""

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
import requests

# 配置常量
TARGETS_FILE = Path(__file__).parent / "targets.txt"
OUTPUT_BASE_DIR = Path("data/raw/wiki")
WIKI_LANG = "zh"
API_ENDPOINT = f"https://{WIKI_LANG}.wikipedia.org/w/api.php"
USER_AGENT = "Ninja-RAG-WikiFetcher/1.0 (https://github.com/KARPED1EM/Ninja-RAG; educational project)"
IMAGEINFO_BATCH_SIZE = 40
DEFAULT_CATEGORY = "未分类"

# 统一的文件名
PARSE_FILE = "parse.json"
IMAGEINFO_FILE = "imageinfo.json"
PAGEPROPS_FILE = "pageprops.json"


@dataclass
class Target:
    """词条目标"""

    name: str
    category: str


def parse_targets(file_path: Path) -> list[Target]:
    """
    解析 targets.txt 文件，提取词条和分类

    格式规则：
    - 空行：忽略
    - // 开头：分类注释，影响后续词条
    - 其他：词条名称
    """
    if not file_path.exists():
        raise FileNotFoundError(f"目标文件不存在: {file_path}")

    targets = []
    current_category = DEFAULT_CATEGORY

    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # 忽略空行
            if not line:
                continue

            # 分类注释
            if line.startswith("//"):
                current_category = line[2:].strip()
                if not current_category:
                    current_category = DEFAULT_CATEGORY
                continue

            # 词条
            targets.append(Target(name=line, category=current_category))

    return targets


def sanitize_filename(title: str) -> str:
    """将页面标题转换为安全的文件名（跨平台兼容）"""
    sanitized = re.sub(r'[\\/:*?"<>|]', "_", title)
    sanitized = sanitized.strip().strip(".")
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized


def make_request(url: str, params: dict, max_retries: int = 3) -> dict:
    """发送 API 请求并返回 JSON 响应，支持重试"""
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)

            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")

            data = resp.json()

            if "error" in data:
                err = data["error"]
                raise RuntimeError(f"API Error [{err.get('code')}]: {err.get('info')}")

            return data

        except (requests.RequestException, RuntimeError) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2**attempt
            print(f"  请求失败，{wait_time}秒后重试... ({e})")
            time.sleep(wait_time)


def fetch_parse(page: str) -> dict:
    """抓取 action=parse 数据"""
    params = {
        "action": "parse",
        "page": page,
        "prop": "text|sections|links|images|categories|externallinks",
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
    }
    return make_request(API_ENDPOINT, params)


def fetch_imageinfo(image_files: list[str]) -> dict:
    """批量抓取图片信息"""
    all_pages = {}

    for i in range(0, len(image_files), IMAGEINFO_BATCH_SIZE):
        batch = image_files[i : i + IMAGEINFO_BATCH_SIZE]
        titles = "|".join(f"File:{img}" for img in batch)

        params = {
            "action": "query",
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "titles": titles,
            "format": "json",
            "formatversion": 2,
        }

        data = make_request(API_ENDPOINT, params)

        pages = data.get("query", {}).get("pages", [])
        for page in pages:
            all_pages[page.get("title", "")] = page

        if i + IMAGEINFO_BATCH_SIZE < len(image_files):
            time.sleep(0.2)

    return {"query": {"pages": list(all_pages.values())}}


def fetch_pageprops(page: str) -> dict:
    """抓取 action=query prop=pageprops 数据"""
    params = {
        "action": "query",
        "prop": "pageprops",
        "redirects": 1,
        "titles": page,
        "format": "json",
        "formatversion": 2,
    }
    return make_request(API_ENDPOINT, params)


def save_json(data: dict, filepath: Path) -> None:
    """保存 JSON 文件（UTF-8 编码，格式化输出）"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_target_fetched(output_dir: Path) -> bool:
    """
    检查词条是否已经抓取完整

    返回：如果三个文件都存在且非空，返回 True
    """
    parse_file = output_dir / PARSE_FILE
    imageinfo_file = output_dir / IMAGEINFO_FILE
    pageprops_file = output_dir / PAGEPROPS_FILE

    if not all([parse_file.exists(), imageinfo_file.exists(), pageprops_file.exists()]):
        return False

    # 检查文件是否非空（至少有基本的 JSON 结构）
    try:
        for file in [parse_file, imageinfo_file, pageprops_file]:
            if file.stat().st_size < 10:  # 基本 JSON 至少有 {} 或 []
                return False
        return True
    except Exception:
        return False


def fetch_target(target: Target) -> tuple[bool, bool]:
    """
    抓取单个目标词条

    返回：(成功/失败, 是否跳过)
    """
    try:
        # 构建输出目录
        safe_name = sanitize_filename(target.name)
        safe_category = sanitize_filename(target.category)
        output_dir = OUTPUT_BASE_DIR / safe_category / safe_name

        print(f"\n{'=' * 60}")
        print(f"[{target.category}] {target.name}")
        print(f"{'=' * 60}")
        print(f"输出目录: {output_dir}")

        # 检查是否已经抓取
        if is_target_fetched(output_dir):
            print("[跳过] 词条已存在完整数据")
            return True, True

        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. 抓取 Parse 数据
        print("[1/3] Parse 数据...", end=" ", flush=True)
        parse_data = fetch_parse(target.name)
        parse_file = output_dir / PARSE_FILE
        save_json(parse_data, parse_file)
        print("[OK]")

        # 2. 抓取 ImageInfo 数据
        print("[2/3] ImageInfo 数据...", end=" ", flush=True)
        images = parse_data.get("parse", {}).get("images", [])
        if images:
            imageinfo_data = fetch_imageinfo(images)
        else:
            imageinfo_data = {"query": {"pages": []}}
        imageinfo_file = output_dir / IMAGEINFO_FILE
        save_json(imageinfo_data, imageinfo_file)
        print(f"[OK] ({len(images)} 张图片)")

        # 3. 抓取 PageProps 数据
        print("[3/3] PageProps 数据...", end=" ", flush=True)
        pageprops_data = fetch_pageprops(target.name)
        pageprops_file = output_dir / PAGEPROPS_FILE
        save_json(pageprops_data, pageprops_file)
        print("[OK]")

        # 简要统计
        parse = parse_data.get("parse", {})
        sections = len(parse.get("sections", []))
        links = len(parse.get("links", []))
        categories = len(parse.get("categories", []))
        print(f"统计: {sections} 节 | {links} 链接 | {categories} 分类")

        return True, False

    except Exception as e:
        print(f"\n[失败] {e}")
        return False, False


def main():
    """批量抓取 targets.txt 中的所有词条"""
    print("=" * 60)
    print("中文维基百科批量抓取工具")
    print("=" * 60)
    print(f"目标文件: {TARGETS_FILE}")
    print(f"API 端点: {API_ENDPOINT}")
    print(f"输出目录: {OUTPUT_BASE_DIR.absolute()}")

    # 解析目标文件
    try:
        targets = parse_targets(TARGETS_FILE)
    except Exception as e:
        print(f"\n[错误] 解析目标文件失败: {e}")
        return

    if not targets:
        print("\n[错误] 没有找到任何词条")
        return

    print(f"\n共找到 {len(targets)} 个词条")

    # 统计分类
    categories = {}
    for target in targets:
        categories[target.category] = categories.get(target.category, 0) + 1

    print("\n分类统计:")
    for category, count in sorted(categories.items()):
        print(f"  - {category}: {count}")

    # 批量抓取
    success_count = 0
    skipped_count = 0
    failed_targets = []

    for i, target in enumerate(targets, 1):
        print(f"\n进度: {i}/{len(targets)}")
        success, skipped = fetch_target(target)

        if success:
            if skipped:
                skipped_count += 1
            else:
                success_count += 1
        else:
            failed_targets.append(target)

        # 防止请求过快（跳过的不需要延迟）
        if not skipped and i < len(targets):
            time.sleep(1)

    # 最终统计
    print("\n" + "=" * 60)
    print("批量抓取完成")
    print("=" * 60)
    print(f"新抓取: {success_count}/{len(targets)}")
    print(f"跳过: {skipped_count}/{len(targets)}")
    print(f"失败: {len(failed_targets)}/{len(targets)}")

    if failed_targets:
        print("\n失败词条:")
        for target in failed_targets:
            print(f"  - [{target.category}] {target.name}")

    print(f"\n数据已保存至: {OUTPUT_BASE_DIR.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
