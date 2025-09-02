from app.models.chunk_content_attached_model import ChunkContentAttachedMapper
from app.services import chunk_service


def test_chunk_add(test_file_id):
    file_id = test_file_id("md")
    chunk = {
        "source_id": file_id,
        "source_name": "test source name",
        "chunk_type": "text",
        "content_title": "test chunk title",
        "content_data": "test chunk content",
        "chunk_pos": 1,
        "extra": {
            "city_list": ["beijing", "shanghai", "guangzhou"]
        }
    }
    chunk_id = chunk_service.add_chunk(**chunk)
    assert chunk_id is not None


def test_chunk_update(test_file_id):
    file_id = test_file_id("md")
    chunk_id = f'{file_id}-0'
    chunk = {
        "content_title": "test chunk title-update",
        "content_data": "test chunk content-update",
        "extra": {
            "city_list": ["beijing", "shanghai", "guangzhou"],
            "hidden": True
        }
    }
    chunk_service.update_chunk(chunk_id, **chunk)
    chunk = chunk_service.chunk_list_by_ids([chunk_id])
    assert chunk[0].get("content_title") == "test chunk title-update"
    assert chunk[0].get("content_data") == "test chunk content-update"
    assert chunk[0].get("extra") is not None


def test_chunk_list(test_file_id):
    file_id = test_file_id("md")
    chunk_ids = [f'{file_id}-0', f'{file_id}-1', f'{file_id}-2', f'{file_id}-3']
    chunks = chunk_service.chunk_list_by_ids(chunk_ids)
    assert len(chunks) == 4
    assert chunks[0].get("source_id") == file_id
    assert chunks[0].get("chunk_type") is not None

    source_chunks = chunk_service.chunk_list_by_source_id(file_id, 10, 0, False)
    assert len(source_chunks) == 10
    assert source_chunks[0].get("source_id") == file_id
    assert source_chunks[0].get("chunk_type") is not None


def test_chunk_delete(test_file_id):
    file_id = test_file_id("md")
    chunk_id = f'{file_id}-0'
    chunk_service.delete_chunk(chunk_id)
    chunk = chunk_service.chunk_list_by_ids([chunk_id])
    assert len(chunk) == 0


def test_chunk_pos_incr(test_file_id):
    file_id = test_file_id("md")
    ChunkContentAttachedMapper.chunk_pos_increment(file_id, 0)


def test_chunk_pos_decr(test_file_id):
    file_id = test_file_id("md")
    ChunkContentAttachedMapper.chunk_pos_decrement(file_id, 0)
