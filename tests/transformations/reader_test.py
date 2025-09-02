import io

from bella_rag.transformations.factory import TransformationFactory
from tests import TEST_PATH


def test_pdf_reader():
    file_path = TEST_PATH + "/resources/测试.pdf"

    with open(file_path, 'rb') as file:
        file_bytes = file.read()
        reader = TransformationFactory.get_reader('pdf')
        docs = reader.load_data(io.BytesIO(file_bytes))
        assert len(docs) > 0


def test_txt_reader():
    file_path = TEST_PATH + "/resources/测试.txt"

    with open(file_path, 'rb') as file:
        file_bytes = file.read()
        reader = TransformationFactory.get_reader('txt')
        docs = reader.load_data(io.BytesIO(file_bytes))
        assert len(docs) > 0
