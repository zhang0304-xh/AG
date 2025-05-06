import logging
from AGKG.client.neo4j_client import Neo4jClient
from AGKG.client.zhipu_client import ZhipuClient

# 配置日志
logger = logging.getLogger('client_manager')


class ClientManager:
    """
    客户端管理器，集中管理和初始化所有外部服务客户端
    使用单例模式确保系统中只有一个管理器实例
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        """获取ClientManager单例实例"""
        if cls._instance is None:
            cls._instance = ClientManager()
        return cls._instance

    def __new__(cls):
        # 注意：不再在__new__中处理单例，而是通过get_instance方法获取
        instance = super(ClientManager, cls).__new__(cls)
        instance._initialized = False
        return instance

    def __init__(self):
        if self._initialized:
            return

        logger.info("初始化客户端管理器...")

        # 初始化所有客户端
        self._neo4j_client = None
        self._zhipu_client = None

        # 标记为已初始化
        self._initialized = True

    def get_neo4j_client(self):
        """获取Neo4j客户端实例"""
        if self._neo4j_client is None:
            logger.info("首次请求Neo4j客户端，开始初始化...")
            self._neo4j_client = Neo4jClient()
        return self._neo4j_client

    def get_zhipu_client(self):
        """获取智谱AI客户端实例"""
        if self._zhipu_client is None:
            logger.info("首次请求智谱AI客户端，开始初始化...")
            self._zhipu_client = ZhipuClient()
        return self._zhipu_client


# 不再在模块级创建实例
# 而是通过get_instance方法获取
def get_client_manager():
    return ClientManager.get_instance()