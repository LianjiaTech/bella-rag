from bella_rag.transformations.parser.csv_parser import CsvParser
from bella_rag.transformations.parser.excel_parser import ExcelParser
from bella_rag.transformations.parser.html_parser import HtmlParser
from bella_rag.transformations.parser.pdf_parser import PdfParser
from bella_rag.transformations.parser.txt_parser import TxtParser
from bella_rag.transformations.reader.csv_reader import CsvReader
from bella_rag.transformations.reader.doc_reader import DocReader, DocxReader
from bella_rag.transformations.reader.excel_reader import ExcelReader
from bella_rag.transformations.reader.html_reader import HtmlReader
from bella_rag.transformations.reader.pdf_reader import PdfReader
from bella_rag.transformations.reader.txt_reader import TxtReader


class TransformationFactory:
    # 自定义Parser注册表
    _business_parsers = {}

    @classmethod
    def register_business_parser(cls, file_type: str, parser_class, **kwargs):
        """
        注册自定义Parser
        Args:
            file_type: 文件类型，如 'csv'
            parser_class: Parser类
            **kwargs: Parser构造参数
        """
        cls._business_parsers[file_type] = {'class': parser_class, 'kwargs': kwargs}

    @classmethod
    def get_business_custom_parsers(cls, **extra_kwargs):
        """
        获取自定义Parser列表，用于传递给get_parser的custom_parser参数
        Args:
            **extra_kwargs: 额外的构造参数，格式为 {file_type: {param: value}}
        Returns:
            dict: custom_parser字典
        """
        custom_parsers = {}
        for file_type, parser_info in cls._business_parsers.items():
            parser_class = parser_info['class']
            # 合并默认参数和额外参数
            kwargs = parser_info['kwargs'].copy()
            if file_type in extra_kwargs:
                kwargs.update(extra_kwargs[file_type])

            # 创建Parser实例
            custom_parsers[file_type] = parser_class(**kwargs)

        return custom_parsers

    @staticmethod
    def get_reader(file_type: str):
        switcher = {
            "pdf": PdfReader(),
            "doc": DocReader(),
            "docx": DocxReader(),
            "txt": TxtReader(),
            "html": HtmlReader(),
            "csv": CsvReader(),
            "md": TxtReader(),
            "xlsx": ExcelReader(),
            "xls": ExcelReader(),
        }

        return switcher.get(file_type, None)

    @staticmethod
    def get_parser(file_type: str, custom_parser: dict = None):
        switcher = {
            "pdf": PdfParser(),
            # docx文件使用pdf解析
            "doc": PdfParser(),
            "docx": PdfParser(),
            "txt": TxtParser(),
            "html": HtmlParser(),
            "csv": CsvParser(),
            "md": TxtParser(),
            "xlsx": ExcelParser(),
            "xls": ExcelParser(),
        }
        if custom_parser:
            # 使用 update() 方法合并字典，如果 key 冲突，使用第二个字典的值
            switcher.update(custom_parser)

        return switcher.get(file_type, None)
