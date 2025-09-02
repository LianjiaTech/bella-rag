from init.settings import OPENAPI, FILE_API
from bella_rag.llm.openapi import FileAPIClient

file_api_client = FileAPIClient(ak=OPENAPI["AK"], base_url=FILE_API['url'] if FILE_API['url'] else OPENAPI['URL'])
