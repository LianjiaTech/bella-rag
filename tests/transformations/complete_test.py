import io

from bella_rag.transformations.factory import TransformationFactory
from bella_rag.transformations.parser.pdf_parser import PdfParser
from bella_rag.utils import schema_util
from bella_rag.utils.complete_util import _complete_table, small2big, Small2BigModes


def test_complete():
    loader = TransformationFactory.get_reader('pdf')
    with open("../resources/测试.pdf", 'rb') as file:
        byte_stream = file.read()
    docs = loader.load_data(io.BytesIO(byte_stream))

    parser = PdfParser()
    domtree = parser._parse_pdf(documents=docs)
    print(domtree)

    nodes = schema_util.dom2nodes(domtree)

    print("开始补全")
    added_nodes = []
    complete_table = _complete_table(table_node=nodes[200], chunk_max_length=5000,
                                     has_process_node=added_nodes, model="gpt-4")
    print(complete_table)

    print("开始补全")
    complete_res = small2big(nodes=[nodes[8]], chunk_max_length=5000, model="gpt-4", mode=Small2BigModes.MORE_INFO)
    print(complete_res)
