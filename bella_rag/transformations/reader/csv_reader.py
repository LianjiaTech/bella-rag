import io
from io import IOBase
from typing import List, Any, Dict

import pyexcel

from bella_rag.schema.document import Document, CSVDocument
from bella_rag.transformations.reader import read_all
from bella_rag.transformations.reader.base import BaseReader
from bella_rag.utils.file_util import detect_encoding
from init.settings import user_logger

logger = user_logger


def load_qa(sheet: List[Dict[str, Any]]):
    text = ""
    for line in sheet:
        text = text + "question: " + str(line["question"]) + "\n"
        text = text + "answer: " + str(line["answer"]) + "\n"
        text = text + "\n\n"
    return text


class CsvReader(BaseReader):

    def load_data(self, stream: IOBase) -> List[Document]:
        """
        reader负责将数据都先读出来，不做任何处理，parse的时候在做处理
        """

        # 1.读取文档
        content_bytes = read_all(stream)
        byte_stream = io.BytesIO(content_bytes)
        py_sheet = None
        try:
            py_sheet = pyexcel.get_sheet(file_stream=byte_stream, file_type='csv',
                                         encoding=detect_encoding(content_bytes),
                                         name_columns_by_row=0)
        # 上述解析出的encoding不一定100%正确，如果发送异常则使用gbk解析尝试
        except Exception:
            logger.info("csv解析失败，尝试使用gbk编码进行解析")
            py_sheet = pyexcel.get_sheet(file_stream=byte_stream, file_type='csv',
                                         encoding='gbk',
                                         name_columns_by_row=0)

        # 通常 CSV 文件被视为单个工作表的数据源，而不是包含多个工作表的 Excel 文件
        headers = py_sheet.colnames
        data_rows = [dict(zip(headers, row)) for row in py_sheet.row]

        sheet: List[Dict[str, Any]] = []
        for data_row in data_rows:
            sheet.append(data_row)

        document = CSVDocument(sheet=sheet, text=load_qa(sheet))
        stream.close()
        return [document]
