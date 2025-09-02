from threading import Lock

from django.apps import AppConfig as DjangoAppConfig

from init.settings import user_logger

logger = user_logger


# This is the place to import signals，不能删

class AppConfig(DjangoAppConfig):
    name = 'app'
    ready_lock = Lock()  # 类属性，用于线程同步
    ready_called = False

    def ready(self):

        with AppConfig.ready_lock:  # 进入锁定区域
            if AppConfig.ready_called:
                return
            AppConfig.ready_called = True  # 标记ready方法已被调用

            from app.workers import start_workers
            from app.tasks import start_schedulers
            logger.info('Starting Kafka consumer thread...')
            start_workers()
            logger.info('Starting Kafka consumer thread ok...')

            logger.info('Starting schedulers thread...')
            start_schedulers()
            logger.info('Starting schedulers thread ok...')

            logger.info('Initializing Elasticsearch index...')
            try:
                from app.stores import init_elasticsearch_index
                result = init_elasticsearch_index()
                if result:
                    logger.info('Elasticsearch index initialized successfully.')
                else:
                    logger.info('Elasticsearch index initialization skipped (no configuration).')
            except Exception as e:
                logger.error(f'Failed to initialize Elasticsearch index: {e}')
                import traceback
                traceback.print_exc()

            logger.info('Configuring API URL patterns...')
            try:
                from django.conf.urls import url, include
                import init.urls
                api_url_pattern = url(r'^api/', include(("app.urls", 'app'), namespace='app'))
                init.urls.urlpatterns.append(api_url_pattern)
                logger.info('API URL patterns configured successfully.')
            except Exception as e:
                logger.error(f'Failed to configure API URL patterns: {e}')
                import traceback
                traceback.print_exc()
