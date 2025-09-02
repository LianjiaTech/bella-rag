"""
es存储初始化模块
"""
from init.settings import user_logger, get_elasticsearch_config

logger = user_logger

def init_elasticsearch_index():
    """初始化Elasticsearch索引"""
    try:
        # 延迟导入以避免循环导入
        from bella_rag.vector_stores.elasticsearch import create_elasticsearch_store
        from bella_rag.vector_stores.factory import register_index
        
        es_config = get_elasticsearch_config()
        if es_config and es_config.get('HOSTS'):
            # 创建标准的Elasticsearch存储
            es_store = create_elasticsearch_store(
                hosts=es_config['HOSTS'].split(',') if isinstance(es_config['HOSTS'], str) else [es_config['HOSTS']],
                index_name=es_config.get('INDEX_NAME', 'bella_rag')
                # ES客户端会使用默认的连接参数
            )
            
            # 注册ES索引
            register_index(
                "es_index", 
                es_store,
                description="Elasticsearch搜索索引"
            )
            logger.info(f"Elasticsearch索引注册成功 - hosts: {es_config['HOSTS']}, index: {es_config.get('INDEX_NAME', 'bella_rag')}")
            return True
        else:
            logger.info("未找到Elasticsearch配置，跳过ES索引注册")
            return False
    except Exception as e:
        logger.error(f"Elasticsearch索引注册失败: {e}")
        return False

# 注意：ES索引初始化由app/apps.py中的ready()方法调用，不在此处自动初始化
