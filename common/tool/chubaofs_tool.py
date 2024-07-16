import io

from common.tool.webdav3.client import Client


class ChuBaoFSTool:

    def __init__(self):
        options = {
            "webdav_hostname": "http://i.webdav.arch.ke.com",
            "webdav_login": "rwq3RBrBxxCYQRg",
            "webdav_password": "FI4NudbkaGaCM",
            "webdav_disable_check": True
        }

        client = Client(options)
        client.webdav.disable_check = False
        # To not check SSL certificates (Default = True)
        client.verify = False
        self.client = client

    def get_client(self):
        return self.client

    def read_file(self, file_path):
        resource = self.client.resource(file_path)
        stream = io.BytesIO()
        resource.write_to(stream)
        stream.seek(0)
        return stream

    def download_file(self, file_path, local_path):
        self.client.download(file_path, local_path)