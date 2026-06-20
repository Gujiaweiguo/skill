"""word-master 包"""
from .parser import parse_content_package, ContentPackage
from .renderer import render

__all__ = ["parse_content_package", "ContentPackage", "render"]