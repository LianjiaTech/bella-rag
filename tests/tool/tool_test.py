from common.tool.chubaofs_tool import ChuBaoFSTool


def test_chubao_tool():
    file_path = "ait-raw-data/1000000020018632/app_data/belle/其他/专利Q&A.pdf"
    chubao = ChuBaoFSTool()
    stream = chubao.read_file(file_path)
    read_all(stream)
    info = chubao.client.info(file_path)
    print(info)



def read_all(stream):
    while True:
        data = stream.read(1024)
        print(data)
        if not data:
            break

