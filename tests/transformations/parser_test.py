import io

from bella_rag.transformations.factory import TransformationFactory
from bella_rag.transformations.parser.txt_parser import TxtParser
from tests import TEST_PATH


def test_txt_parser():
    file_path = TEST_PATH + "/resources/测试.txt"

    with open(file_path, 'rb') as file:
        file_bytes = file.read()
        reader = TransformationFactory.get_reader('txt')
        docs = reader.load_data(io.BytesIO(file_bytes))
        parser = TxtParser()
        parsed_docs = parser.get_nodes_from_documents(docs)
        assert len(parsed_docs) > 0
