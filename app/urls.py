from django.conf.urls import url

from app.controllers import rag, chunk, file, qa

urlpatterns = [
    # RAG接口
    url(r'^rag/chat$', rag.chat, name="rag_chat"),
    url(r'^rag/search$', rag.search, name="rag_search"),

    # file接口
    url(r'^file/indexing$', file.file_indexing, name="file_indexing"),
    url(r'^file/stream/indexing$', file.file_stream_indexing, name="file_stream_indexing"),
    url(r'^file/file_indexing_submit_task$', file.file_indexing_submit_task, name="file_indexing_submit_task"),
    url(r'^file/file_delete_submit_task$', file.file_delete_submit_task, name='file_delete_submit_task'),
    url(r'^file/rename$', file.file_rename, name='file_rename'),
    url(r'^file/update$', file.file_update, name='file_update'),
    url(r'^file/summary/query$', file.file_summary_query, name='file_summary_query'),
    url(r'^file/summaries$', file.file_summaries, name='file_summaries'),

    # chunk接口
    url(r'^chunk/add', chunk.add_chunk, name='add_chunk'),
    url(r'^chunk/update$', chunk.update_chunk, name='update_chunk'),
    url(r'^chunk/delete$', chunk.delete_chunk, name='delete_chunk'),
    url(r'^chunk/list$', chunk.chunk_list, name='chunk_list'),

    # qa接口
    url(r'^qa/add_qa_group$', qa.add_qa_group, name='add_qa_group'),
    url(r'^qa/coverage_group$', qa.coverage_group, name='coverage_group'),
    url(r'^qa/delete_by_group_id$', qa.delete_by_group_id, name='delete_by_group_id'),
    url(r'^qa/list$', qa.qa_list, name='qa_list'),
]
