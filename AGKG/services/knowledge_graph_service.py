import logging
from typing import Dict, List, Any, Optional
import time
from AGKG.core.client_manager import get_client_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('knowledge_graph_service')

class KnowledgeGraphService:
    """
    知识图谱服务类，处理知识图谱相关的业务逻辑
    """
    
    def __init__(self, retry_delay=1):
        """
        初始化知识图谱服务
        
        Args:
            max_retries: 连接数据库重试最大次数
            retry_delay: 重试延迟时间(秒)
        """
        # 从客户端管理器获取Neo4j客户端实例
        client_manager = get_client_manager()
        self.neo4j_client = client_manager.get_neo4j_client()
        self.retry_delay = retry_delay
        self.connected = True  # Neo4jClient已经在其自身的__init__中连接了数据库
        # 不需要再次调用connect()，避免重复连接和日志
        
    def get_graph_visualization_data(self, entity_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        获取知识图谱可视化数据
        
        Args:
            entity_name: 可选，实体名称，用于获取特定实体及其邻居
            limit: 限制返回的节点数量，默认为10
            
        Returns:
            dict: 包含节点和连接的字典
        """
        if not self.connected:
            logger.warning("未连接到Neo4j数据库，返回空数据")
            return {'nodes': [], 'links': []}
        
        try:
            # 如果没有提供实体名称，默认使用"桃树"
            if not entity_name:
                entity_name = "桃树"
                
            logger.info(f"获取实体 '{entity_name}' 及其邻居")
            nodes, links = self.neo4j_client.get_entity_and_neighbors(entity_name, limit)
            
            # 转换为前端所需的格式
            return self._format_graph_data(nodes, links)
        except Exception as e:
            logger.error(f"获取图谱数据失败: {str(e)}")
            # 返回空数据而不是抛出异常，让前端可以处理
            return {'nodes': [], 'links': [], 'error': str(e)}
    
    def search_entity(self, query: str) -> Dict[str, Any]:
        """
        搜索实体
        
        Args:
            query: 搜索关键词
            
        Returns:
            dict: 包含匹配的节点和连接
        """
        if not self.connected:
            logger.warning("未连接到Neo4j数据库，无法搜索实体")
            return {'nodes': [], 'links': [], 'error': '数据库连接失败'}
        
        try:
            logger.info(f"搜索实体: '{query}'")
            entities = self.neo4j_client.search_entities(query)
            
            if entities:
                # 获取这些实体及其邻居形成的子图
                entity_ids = [entity['id'] for entity in entities]
                nodes, links = self.neo4j_client.get_subgraph_from_nodes(entity_ids)
                return self._format_graph_data(nodes, links)
            else:
                return {'nodes': [], 'links': []}
        except Exception as e:
            logger.error(f"搜索实体失败: {str(e)}")
            return {'nodes': [], 'links': [], 'error': f"搜索失败: {str(e)}"}
    
    def expand_node(self, node_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        展开节点，获取相关实体
        """
        try:
            # 添加类型转换处理
            node_id = int(node_id)  # 将字符串ID转换为整数
            logger.info(f"展开节点: {node_id}")
            nodes, links = self.neo4j_client.get_entity_neighbors_by_id(node_id, limit)
            return self._format_graph_data(nodes, links)
        except ValueError as e:
            logger.error(f"节点ID格式错误: {node_id}")
            return {'nodes': [], 'links': [], 'error': f"无效的节点ID格式: {node_id}"}
        except Exception as e:
            logger.error(f"展开节点失败: {str(e)}")
            return {'nodes': [], 'links': [], 'error': f"展开失败: {str(e)}"}
    
    def _format_graph_data(self, nodes, links):
        # 格式化节点时统一转换为字符串
        formatted_nodes = []
        for node in nodes:
            formatted_node = {
                'id': str(node.get('id')),  # 确保转换为字符串
                'name': node.get('name', '未命名节点'),
                'symbolSize': 20,
                'category': node.get('category', 0)
            }
            
            # 添加额外属性
            properties = node.get('properties', {})
            formatted_node['properties'] = properties
            
            # 添加描述文本
            description = properties.get('description', '')
            if description:
                formatted_node['description'] = description
            
            formatted_nodes.append(formatted_node)
        
        # 格式化连接
        formatted_links = []
        for link in links:
            formatted_link = {
                'source': str(link.get('source')),
                'target': str(link.get('target')),
                'value': link.get('name', '')
            }
            formatted_links.append(formatted_link)
        
        # 提取类别
        categories = []
        category_set = set()
        
        for node in nodes:
            category = node.get('category')
            if category is not None and category not in category_set:
                category_set.add(category)
                categories.append({
                    'name': category
                })
        
        # 如果没有类别，添加一个默认类别
        if not categories:
            categories.append({ 'name': '默认类别' })
        
        return {
            'nodes': formatted_nodes,
            'links': formatted_links,
            'categories': categories
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识图谱统计信息
        
        Returns:
            dict: 包含实体数量、关系数量等统计信息
        """
        if not self.connected:
            logger.warning("未连接到Neo4j数据库，返回模拟统计数据")
            # 返回模拟的统计数据，而不是抛出异常
            return {
                '总实体数': 0,
                '总关系数': 0,
                '实体类型数': 0,
                '关系类型数': 0,
                '实体类型分布': {},
                '关系类型分布': {},
                'error': '数据库连接失败'
            }
        
        try:
            logger.info("获取知识图谱统计信息")
            node_stats = self.neo4j_client.get_node_statistics()
            relation_stats = self.neo4j_client.get_relation_statistics()
            
            # 计算总节点数和总关系数
            total_nodes = sum(item['count'] for item in node_stats) if node_stats else 0
            total_relationships = sum(item['count'] for item in relation_stats) if relation_stats else 0
            
            # 处理节点标签统计
            node_label_counts = {}
            for item in node_stats:
                if 'label' in item and 'count' in item:
                    node_label_counts[item['label']] = item['count']
            
            # 处理关系类型统计
            relation_type_counts = {}
            for item in relation_stats:
                if 'type' in item and 'count' in item:
                    relation_type_counts[item['type']] = item['count']
            
            return {
                '总实体数': total_nodes,
                '总关系数': total_relationships,
                '实体类型数': len(node_label_counts),
                '关系类型数': len(relation_type_counts),
                '实体类型分布': node_label_counts,
                '关系类型分布': relation_type_counts
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            # 返回模拟数据，避免前端错误
            return {
                '总实体数': 0,
                '总关系数': 0,
                '实体类型数': 0,
                '关系类型数': 0,
                '实体类型分布': {},
                '关系类型分布': {},
                'error': f"获取统计信息失败: {str(e)}"
            }