"""word-master 内容包解析器

解析 `.word-content.md` → ContentPackage 数据结构
供 renderer 使用
"""

from __future__ import annotations

import re
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================
# 数据结构
# ============================================================

@dataclass
class CoverInfo:
    title: str = ""
    subtitle: str = ""
    version: str = ""
    date: str = ""
    confidential: bool = False


@dataclass
class HeaderFooter:
    left: str = ""
    center: str = ""
    right: str = ""


@dataclass
class TocSettings:
    enabled: bool = True
    max_level: int = 3
    include_heading: bool = False


@dataclass
class SourceRef:
    path: str = ""
    type: str = ""


@dataclass
class ContentPackage:
    # 元数据
    title: str = ""
    project: str = ""
    client: str = ""
    type: str = "proposal"
    template: str = ""
    date: str = ""
    author: str = ""

    # 封面
    cover: Optional[CoverInfo] = None

    # 页眉页脚
    header: Optional[HeaderFooter] = None
    footer: Optional[HeaderFooter] = None

    # 目录
    toc: Optional[TocSettings] = None

    # 素材引用
    sources: list[SourceRef] = field(default_factory=list)

    # 格式覆盖（响应招标格式要求）
    # format_overrides = {
    #   "font": {"body": "宋体", "heading": "黑体", "size": 12},
    #   "margins": {"top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17},
    #   "page": {"size": "A4", "orientation": "portrait"},
    # }
    format_overrides: dict = field(default_factory=dict)

    # 章节列表
    chapters: list[Chapter] = field(default_factory=list)

    # 原始路径
    source_path: str = ""


@dataclass
class TableData:
    table_type: str = "default-table"
    header: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    column_widths: list[int] = field(default_factory=list)


@dataclass
class Chapter:
    heading_text: str = ""
    heading_level: int = 1  # 1=heading-1, 2=heading-2, etc.
    page_break: bool = False

    # 内容列表
    paragraphs: list[str] = field(default_factory=list)
    list_items: list[list[str]] = field(default_factory=list)  # 嵌套列表
    ordered_list_items: list[list[str]] = field(default_factory=list)
    tables: list[TableData] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)

    # 子章节（只有 heading-1 可以有子章节）
    sub_chapters: list[Chapter] = field(default_factory=list)


# ============================================================
# 解析器
# ============================================================

class Parser:
    """解析 `.word-content.md` → ContentPackage"""

    YAML_PATTERN = re.compile(r"^---\s*$", re.MULTILINE)

    # 匹配 ```yaml ... ``` 块
    YAML_BLOCK_PATTERN = re.compile(
        r"^```yaml\s*\n(.*?)```",
        re.DOTALL | re.MULTILINE,
    )

    # 匹配标题行
    HEADING_PATTERN = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

    # 匹配 Markdown 图片
    IMAGE_PATTERN = re.compile(r"!\[(.*?)\]\((.*?)\)")

    # 匹配无序列表项
    UNORDERED_LIST_PATTERN = re.compile(r"^(\s*)[-*+]\s+(.+)$", re.MULTILINE)

    # 匹配有序列表项
    ORDERED_LIST_PATTERN = re.compile(r"^(\s*)\d+\.\s+(.+)$", re.MULTILINE)

    def parse(self, path: str | Path) -> ContentPackage:
        """解析 .word-content.md 文件"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"内容包文件不存在: {path}")

        raw = path.read_text(encoding="utf-8")
        pkg = ContentPackage(source_path=str(path))

        # 1. 解析 frontmatter
        frontmatter, body = self._split_frontmatter(raw)
        if frontmatter:
            self._parse_frontmatter(pkg, frontmatter)

        # 2. 解析章节
        pkg.chapters = self._parse_chapters(body)

        return pkg

    def _split_frontmatter(self, raw: str) -> tuple[str | None, str]:
        """分离 YAML frontmatter 和正文"""
        matches = list(self.YAML_PATTERN.finditer(raw))
        if len(matches) >= 2:
            start = matches[0].end()
            end = matches[1].start()
            frontmatter = raw[start:end].strip()
            body = raw[matches[1].end():].strip()
            return frontmatter, body
        return None, raw

    def _parse_frontmatter(self, pkg: ContentPackage, frontmatter: str):
        """解析 YAML frontmatter"""
        try:
            data = yaml.safe_load(frontmatter)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML frontmatter 解析失败: {e}")

        if not data or not isinstance(data, dict):
            return

        # 元数据
        pkg.title = data.get("title", pkg.title)
        pkg.project = data.get("project", pkg.project)
        pkg.client = data.get("client", pkg.client)
        pkg.type = data.get("type", pkg.type)
        pkg.template = data.get("template", pkg.template)
        pkg.date = data.get("date", pkg.date)
        pkg.author = data.get("author", pkg.author)

        # 封面
        if "cover" in data and isinstance(data["cover"], dict):
            cv = data["cover"]
            pkg.cover = CoverInfo(
                title=cv.get("title", ""),
                subtitle=cv.get("subtitle", ""),
                version=cv.get("version", ""),
                date=cv.get("date", ""),
                confidential=cv.get("confidential", False),
            )

        # 页眉
        if "header" in data and isinstance(data["header"], dict):
            h = data["header"]
            pkg.header = HeaderFooter(
                left=h.get("left", ""),
                center=h.get("center", ""),
                right=h.get("right", ""),
            )

        # 页脚
        if "footer" in data and isinstance(data["footer"], dict):
            f = data["footer"]
            pkg.footer = HeaderFooter(
                left=f.get("left", ""),
                center=f.get("center", ""),
                right=f.get("right", ""),
            )

        # 目录
        if "toc" in data and isinstance(data["toc"], dict):
            t = data["toc"]
            pkg.toc = TocSettings(
                enabled=t.get("enabled", True),
                max_level=t.get("max_level", 3),
                include_heading=t.get("include_heading", False),
            )

        # 素材引用
        if "sources" in data and isinstance(data["sources"], list):
            pkg.sources = [
                SourceRef(path=s.get("path", ""), type=s.get("type", ""))
                for s in data["sources"]
                if isinstance(s, dict)
            ]

        # 格式覆盖
        if "format_overrides" in data and isinstance(data["format_overrides"], dict):
            pkg.format_overrides = data["format_overrides"]

    def _parse_chapters(self, body: str) -> list[Chapter]:
        """解析正文中的章节"""
        chapters: list[Chapter] = []
        lines = body.split("\n")

        current_chapter: Chapter | None = None
        current_sub: Chapter | None = None
        in_yaml_block = False
        yaml_buffer = ""
        content_buffer: list[str] = []
        in_list_block = False
        in_ordered_list_block = False
        list_buffer: list[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 跳过空注释行
            if stripped.startswith("<!--"):
                while i < len(lines) and not stripped.endswith("-->"):
                    i += 1
                    if i < len(lines):
                        stripped = lines[i].strip()
                i += 1
                continue

            # YAML 块开始
            if stripped.startswith("```yaml"):
                in_yaml_block = True
                yaml_buffer = ""
                i += 1
                continue

            # YAML 块结束
            if in_yaml_block and stripped.startswith("```"):
                in_yaml_block = False
                # 应用到当前子节（如果存在），否则应用到当前章
                target = current_sub or current_chapter
                if target and yaml_buffer.strip():
                    self._apply_yaml_to_chapter(target, yaml_buffer)
                i += 1
                continue

            if in_yaml_block:
                yaml_buffer += line + "\n"
                i += 1
                continue

            # 标题行
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                md_level = len(heading_match.group(1))
                text = heading_match.group(2).strip()

                # 内容包规范：## → 章(heading-1), ### → 节(heading-2), #### → 小节(heading-3)
                # 但还要看 YAML style 字段可能覆盖
                semantic_level = max(1, md_level - 1)  # ## → 1, ### → 2, #### → 3

                # 先刷新上一章的缓存段落
                if (current_chapter or current_sub) and content_buffer:
                    target = current_sub or current_chapter
                    if target:
                        self._parse_content_buffer(target, content_buffer)
                    content_buffer = []

                # 创建新的章节节点
                new_chapter = Chapter(
                    heading_text=text,
                    heading_level=semantic_level,
                )

                if semantic_level == 1:
                    # 新章
                    chapters.append(new_chapter)
                    current_chapter = new_chapter
                    current_sub = None
                else:
                    # 子节，挂到当前章下
                    if current_chapter is not None:
                        current_chapter.sub_chapters.append(new_chapter)
                    else:
                        # 无父章时作为独立章
                        chapters.append(new_chapter)
                        current_chapter = new_chapter
                    current_sub = new_chapter

                i += 1
                continue

            # 空行 → 刷新缓存段落
            if stripped == "":
                target = current_sub or current_chapter
                if target and content_buffer:
                    self._parse_content_buffer(target, content_buffer)
                    content_buffer = []
                i += 1
                continue

            # 普通文本行 → 缓存
            content_buffer.append(line)
            i += 1

        # 最后一段缓存
        target = current_sub or current_chapter
        if target and content_buffer:
            self._parse_content_buffer(target, content_buffer)

        return chapters

    def _apply_yaml_to_chapter(self, chapter: Chapter, yaml_text: str):
        """将 YAML 块的配置应用到章节"""
        try:
            data = yaml.safe_load(yaml_text)
        except yaml.YAMLError:
            return

        if not data or not isinstance(data, dict):
            return

        # style 字段覆盖 heading_level
        if "style" in data:
            style_val = data["style"]
            if isinstance(style_val, str) and style_val.startswith("heading-"):
                try:
                    chapter.heading_level = int(style_val.split("-")[1])
                except (IndexError, ValueError):
                    pass

        # 分页控制
        if data.get("page_break"):
            chapter.page_break = True

        # 如果有 table 字段，创建表格
        if "table" in data and "table_data" in data:
            td = data["table_data"]
            if td and isinstance(td, dict):
                table = TableData(
                    table_type=data["table"],
                    header=td.get("header", []),
                    rows=td.get("rows", []),
                    column_widths=td.get("column_widths", []),
                )
                chapter.tables.append(table)

        # 如果有 image 字段
        if "image" in data:
            chapter.images.append(data["image"])

    def _parse_content_buffer(self, chapter: Chapter, lines: list[str]):
        """解析非 YAML 缓存的内容"""
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 图片
            img_match = self.IMAGE_PATTERN.search(stripped)
            if img_match:
                chapter.images.append({
                    "alt": img_match.group(1),
                    "path": img_match.group(2),
                })
                continue

            # 无序列表
            ul_match = self.UNORDERED_LIST_PATTERN.match(stripped)
            if ul_match:
                indent = len(ul_match.group(1))
                text = ul_match.group(2)
                chapter.list_items.append([text])
                continue

            # 有序列表
            ol_match = self.ORDERED_LIST_PATTERN.match(stripped)
            if ol_match:
                text = ol_match.group(2)
                chapter.ordered_list_items.append([text])
                continue

            # 普通段落
            chapter.paragraphs.append(stripped)


def parse_content_package(path: str | Path) -> ContentPackage:
    """便捷函数：解析内容包"""
    return Parser().parse(path)