from typing import List, Any, Dict, Tuple

import pandas as pd
from llama_index.core import Document as LlamaDocument
from typing import Optional


class Document(LlamaDocument):
    stream: Optional[bytes] = None


class CSVDocument(Document):
    """
     通常 CSV 文件被视为单个工作表的数据源，而不是包含多个工作表的 Excel 文件,所以sheet是个List
    """
    sheet: List[Dict[str, Any]]


class ExcelDocument(Document):
    # sheet key：文件名+sheet名
    sheet: Tuple[str, pd.DataFrame]

    class Config:
        arbitrary_types_allowed = True
