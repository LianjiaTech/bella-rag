# -*- coding:utf-8 -*-
# @Time: 2024/5/6 21:00
# @Author: dongmenghui
# @Email: dongmenghui001@ke.com
# @File: htmlReader.py
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from llama_index.legacy.readers.base import BaseReader
from llama_index.legacy.schema import Document

if TYPE_CHECKING:
    from bs4 import Tag

class HTMLReader(BaseReader):
    """
    Read HTML files and extract text from the entire document structure.
    """

    def __init__(self, ignore_no_id: bool = False) -> None:
        self._ignore_no_id = ignore_no_id
        super().__init__()

    def load_data(self, file: Path, extra_info: Optional[Dict] = None) -> List[Document]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("bs4 is required to read HTML files.")

        with open(file, encoding="utf-8") as html_file:
            soup = BeautifulSoup(html_file, "html.parser")

        # Extract text from the entire document
        docs = []
        doc_text, metadata = self._extract_text_from_soup(soup, extra_info)

        metadata.update({
            "file_path": str(file),
        })

        doc = Document(
            text=doc_text,
            metadata=metadata,
        )
        docs.append(doc)
        return docs

    def _extract_text_from_soup(self, soup: "Tag", extra_info: Optional[Dict] = None) -> (str, Dict):
        texts = []
        for tag in soup.find_all(True, recursive=True):
            tag_id = tag.get("id")
            if self._ignore_no_id and not tag_id:
                continue
            if tag.name != "script" and tag.name != "style":  # Ignore script and style tags
                tag_text = tag.get_text(separator=" ", strip=True)
                if tag_text:
                    texts.append(tag_text)
        return "\n".join(texts), {"tags": extra_info or {}}

    def _extract_text_from_tag(self, tag: "Tag") -> str:
        # This method is not used in the structured reader, but could be used for specific tag extraction
        try:
            from bs4 import NavigableString
        except ImportError:
            raise ImportError("bs4 is required to read HTML files.")

        texts = []
        for elem in tag.children:
            if isinstance(elem, NavigableString) and elem.strip():
                texts.append(elem.strip())
            elif elem.name != self._tag:  # Ignore the same tag type we are extracting from
                texts.append(elem.get_text().strip())
        return "\n".join(texts)