from bella_rag.config.registry import Registry
from bella_rag.transformations.reader.file_loader import FileApiLoader
from bella_rag.utils.file_api_tool import file_api_client

file_loader = FileApiLoader(client=file_api_client)
Registry.register_loader(file_loader)