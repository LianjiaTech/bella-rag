from bella_rag.utils.file_util import detect_encoding



def file_to_byte_stream(file_path):
    with open(file_path, 'rb') as file:
        byte_stream = file.read()
    return byte_stream


def test_detect_encoding():
    print(detect_encoding(file_to_byte_stream("../resources/测试.csv")))
