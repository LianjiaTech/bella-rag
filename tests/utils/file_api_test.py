from bella_rag.transformations.factory import TransformationFactory


def test_load_file_api_file(test_file_id):
    file_id = test_file_id('txt')
    reader = TransformationFactory.get_reader('txt')
    documents = reader.load_file(file_id)
    print(file_id)

    # 断言
    assert len(documents) == 1
    assert documents[0].text == '西红柿是绿色的'

