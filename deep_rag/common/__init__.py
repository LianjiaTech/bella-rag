from app.services.chunk_content_attached_service import ChunkContentAttachedService
from deep_rag.common.file_tool import FileReader


def read_file_content(file_id):
    """默认文件内容读取方法"""
    content = ""
    chunks = ChunkContentAttachedService.get_all_chunks_by_source_id(file_id)
    for chunk in chunks:
        content += chunk.content_data
    return content

file_reader = FileReader(read_func=read_file_content)
