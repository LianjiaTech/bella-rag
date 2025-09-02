from typing import Optional, List, Any

from llama_index.core import StorageContext, VectorStoreIndex, Settings
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.callbacks import CallbackManager
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.schema import TransformComponent, Document


class ManyVectorStoreIndex:

    @staticmethod
    def from_documents(
            documents: Optional[List[Document]] = None,
            storage_context: Optional[StorageContext] = None,
            show_progress: bool = False,
            callback_manager: Optional[CallbackManager] = None,
            transformations: Optional[List[TransformComponent]] = None,
            embed_model: BaseEmbedding = None,
            insert_batch_size: int = 2048,
            **kwargs: Any
    ):
        if callback_manager is None:
            callback_manager = Settings.callback_manager

        pipeline = IngestionPipeline(transformations=transformations)
        nodes = pipeline.run(documents=documents, show_progress=show_progress, **kwargs)

        vector_stores = storage_context.vector_stores.values() if storage_context.vector_stores else [
            storage_context.vector_store]

        for vector_store in vector_stores:
            VectorStoreIndex(nodes=nodes,
                             show_progress=show_progress,
                             embed_model=embed_model,
                             storage_context=StorageContext.from_defaults(vector_store=vector_store),
                             callback_manager=callback_manager,
                             insert_batch_size=insert_batch_size)
