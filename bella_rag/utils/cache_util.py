from collections import OrderedDict
from typing import List

from llama_index.core.schema import NodeWithScore

from init.settings import user_logger
from bella_rag.schema.nodes import BaseNode


class NodeLRUCache:
    """
    使用lru缓存记录热点文件节点关系
    """
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.node_count = 0

    def file_cached(self, file_id: str) -> bool:
        user_logger.warn(f'file exist in cache:{file_id}')
        return file_id in self.cache

    def get(self, file_id: str, node_id: str):
        if file_id in self.cache and node_id in self.cache[file_id]:
            node = self.cache[file_id][node_id]
            self.cache.move_to_end(file_id)
            return node
        return None

    def put(self, file_id: str, nodes: List[BaseNode]):
        user_logger.info(f'put file nodes into cache:{file_id}, count:{len(nodes)}')
        if nodes and len(nodes) > self.capacity:
            user_logger.warn(f'file nodes too much to put cache:{file_id}, count:{len(nodes)}')
            return

        if file_id in self.cache:
            self.node_count -= len(self.cache[file_id])

        node_map = {node.node_id: node for node in nodes}
        self.cache[file_id] = node_map
        self.node_count += len(nodes)
        self.cache.move_to_end(file_id)

        # 如果节点数量超出容量限制，则删除最久未使用的文件
        while self.node_count > self.capacity:
            oldest_file_id, oldest_nodes = self.cache.popitem(last=False)

            self.node_count -= len(oldest_nodes)

    def remove(self, file_id: str):
        if file_id in self.cache:
            user_logger.info(f'remove file from cache : {file_id}')
            removed_nodes = self.cache.pop(file_id)
            self.node_count -= len(removed_nodes)

    def __str__(self):
        return str(self.cache)
