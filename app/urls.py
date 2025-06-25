from django.conf.urls import url

from app.controllers import rag, chunk, file, qa

urlpatterns = [

    url(r'^file/indexing$', rag.file_indexing, name="file_indexing"),
    url(r'^rag/rag_query$', rag.rag_query, name="rag_query"),

    # file
    url(r'^file/indexing$', file.file_indexing, name="file_indexing"),
    url(r'^file/file_indexing_submit_task$', file.file_indexing_submit_task, name="file_indexing_submit_task"),
    url(r'^file/file_delete_submit_task$', file.file_delete_submit_task, name='file_delete_submit_task'),
    url(r'^file/rename$', file.file_rename, name='file_rename'),

    url(r'^file/update$', file.file_update, name='file_update'),
    url(r'^file/summary/query$', file.file_summary_query, name='file_summary_query'),
    url(r'^file/summaries$', file.file_summaries, name='file_summaries'),

    # chunk
    url(r'^chunk/add', chunk.add_chunk, name='add_chunk'),
    url(r'^chunk/update$', chunk.update_chunk, name='update_chunk'),
    url(r'^chunk/delete$', chunk.delete_chunk, name='delete_chunk'),
    url(r'^chunk/list$', chunk.chunk_list, name='chunk_list'),

    # qa
    url(r'^qa/add_qa_group$', qa.add_qa_group, name='add_qa_group'),
    url(r'^qa/coverage_group$', qa.coverage_group, name='coverage_group'),
    url(r'^qa/delete_by_group_id$', qa.delete_by_group_id, name='delete_by_group_id'),
    url(r'^qa/list$', qa.qa_list, name='qa_list'),


    # rag协议优化
    url(r'^rag/chat$', rag.chat, name="rag_chat"),
    url(r'^rag/search$', rag.search, name="rag_search"),

]
