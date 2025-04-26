from neo4j import GraphDatabase
import logging
from typing import Dict, List, Any, Optional
import os
from neo4j.exceptions import ServiceUnavailable, ClientError
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('neo4j_client')

# 创建Neo4j客户端的单例实例
_neo4j_client_instance = None

class Neo4jClient:
    def __new__(cls):
        global _neo4j_client_instance
        if _neo4j_client_instance is None:
            _neo4j_client_instance = super(Neo4jClient, cls).__new__(cls)
            _neo4j_client_instance._initialized = False
        return _neo4j_client_instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "123456")
        self.driver = None
        self.max_retries = 3
        self.retry_delay = 1  # 重试延迟（秒）
        
        # 自动连接数据库
        self.connect()
        self._initialized = True

    def connect(self):
        """初始化 Neo4j 驱动，带重试机制"""
        if not self.driver:
            for attempt in range(self.max_retries):
                try:
                    self.driver = GraphDatabase.driver(
                        self.uri, 
                        auth=(self.user, self.password),
                        max_connection_lifetime=3600
                    )
                    # 测试连接
                    self.driver.verify_connectivity()
                    logger.info(f"成功连接到Neo4j数据库: {self.uri}")
                    return
                except Exception as e:
                    logger.warning(f"连接Neo4j失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                    if attempt < self.max_retries - 1:
                        import time
                        time.sleep(self.retry_delay)
                    else:
                        logger.error("无法连接到Neo4j数据库，将使用模拟数据")
                        # 如果所有重试都失败，返回模拟驱动
                        self.driver = self._get_mock_driver()

    def close(self):
        """关闭 Neo4j 驱动"""
        if self.driver:
            try:
                self.driver.close()
                self.driver = None
                logger.info("Neo4j连接已关闭")
            except Exception as e:
                logger.error(f"关闭Neo4j连接时发生错误: {str(e)}")

    def get_all_entities(self):
        """获取所有实体"""
        if not self.driver:
            self.connect()
        with self.driver.session() as session:
            result = session.run("""
        MATCH (n)
        RETURN DISTINCT id(n) AS entity_id, n.name AS entity_name
            """)
            records = list(result)
            entities = {record["entity_id"]: record["entity_name"] for record in records}
        return entities

    def get_all_relations(self):
        """获取所有关系"""
        if not self.driver:
            self.connect()
        with self.driver.session() as session:
            result = session.run("""
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) AS relation_type
            """)
            records = list(result)
            relations = {record["relation_type"] for record in records}
        return list(relations)

    def get_all_triplets(self):
        """获取所有三元组"""
        if not self.driver:
            self.connect()
        with self.driver.session() as session:
            result = session.run("""
        MATCH (h)-[r]->(t)
        RETURN id(h) AS head_id, type(r) AS relation_type, id(t) AS tail_id
            """)
            records = list(result)
            triplets = [(record["head_id"], record["relation_type"], record["tail_id"]) for record in records]
        return triplets

    def get_triplet_count(self):
        """获取三元组总数"""
        if not self.driver:
            self.connect()
        with self.driver.session() as session:
            result = session.run("""
           MATCH (h)-[r]->(t)
           RETURN count(*) AS count
            """)
            records = list(result)
            return records[0]["count"]

    def get_triplets_batch(self, offset, limit):
        """分批次获取三元组"""
        if not self.driver:
            self.connect()
        with self.driver.session() as session:
            result = session.run("""
           MATCH (h)-[r]->(t)
           RETURN id(h) AS head_id, type(r) AS relation_type, id(t) AS tail_id
           SKIP $offset LIMIT $limit
            """, offset=offset, limit=limit)
            records = list(result)
            return [(record["head_id"], record["relation_type"], record["tail_id"]) for record in records]

    def get_entity_name(self, entity_id):
        """根据实体 ID 查询实体名字"""
        if not self.driver:
            self.connect()
        with self.driver.session() as session:
            result = session.run("""
        MATCH (n)
        WHERE id(n) = $entity_id
        RETURN n.name AS entity_name
            """, entity_id=entity_id)
            records = list(result)
            if records:
                return records[0]["entity_name"]
        return None

    def query_by_entity_name(self, entity_name: str) -> List[Dict[str, str]]:
        """根据实体名称查询相关的所有三元组"""
        if not self.driver:
            self.connect()
        try:
            with self.driver.session() as session:
                result = session.run("""
            MATCH (h)-[r]->(t)
            WHERE h.name = $entity_name OR t.name = $entity_name
            RETURN h.name AS head, type(r) AS relation, t.name AS tail
                """, entity_name=entity_name)
                records = list(result)
            return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                        for record in records]
        except Exception as e:
            logger.error(f"查询实体 {entity_name} 时发生错误: {str(e)}")
            return []

    def query_by_head_relation(self, head: str, relation: str) -> List[Dict[str, str]]:
        """根据头实体和关系查询尾实体"""
        if not self.driver:
            self.connect()
        try:
            with self.driver.session() as session:
                result = session.run("""
            MATCH (h)-[r]->(t)
            WHERE h.name = $head AND type(r) = $relation
            RETURN h.name AS head, type(r) AS relation, t.name AS tail
                """, head=head, relation=relation)
                records = list(result)
            return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                        for record in records]
        except Exception as e:
            logger.error(f"查询头实体 {head} 和关系 {relation} 时发生错误: {str(e)}")
            return []

    def query_triplet(self, head: str, relation: str, tail: str) -> List[Dict[str, str]]:
        """查询特定的三元组是否存在"""
        if not self.driver:
            self.connect()
        try:
            with self.driver.session() as session:
                result = session.run("""
            MATCH (h)-[r]->(t)
            WHERE h.name = $head AND type(r) = $relation AND t.name = $tail
            RETURN h.name AS head, type(r) AS relation, t.name AS tail
                """, head=head, relation=relation, tail=tail)
                records = list(result)
            return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                        for record in records]
        except Exception as e:
            logger.error(f"查询三元组 ({head}, {relation}, {tail}) 时发生错误: {str(e)}")
            return []

    def query_kg_triplets(self, triplets: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """根据知识图谱三元组列表查询数据库信息"""
        if not self.driver:
            self.connect()

        results = []
        processed_triplets = {}  # 用于存储已处理的Q值结果

        for triplet in triplets:
            head = triplet.get("head", "")
            relation = triplet.get("relation", "")
            tail = triplet.get("tail", "")

            # 处理包含Q值的三元组
            if head.startswith('Q'):
                if head in processed_triplets:
                    head = processed_triplets[head]
                else:
                    continue  # 跳过未知的Q值头实体

            # 如果尾实体是Q值，直接查询头实体和关系
            if tail.startswith('Q'):
                query_result = self.query_by_head_relation(head, relation)
                if query_result:
                    # 存储Q值对应结果
                    processed_triplets[tail] = [item["tail"] for item in query_result]
                    results.append({
                        "triplet": triplet,
                        "result": query_result
                    })
            # 普通三元组查询
            else:
                if head and relation and tail:
                    # 实体关系验证
                    query_result = self.query_triplet(head, relation, tail)
                    results.append({
                        "triplet": triplet,
                        "result": query_result
                    })
                elif head and relation:
                    # 实体关系查询
                    query_result = self.query_by_head_relation(head, relation)
                    results.append({
                        "triplet": triplet,
                        "result": query_result
                    })
                elif head:
                    # 实体查询
                    query_result = self.query_by_entity_name(head)
                    results.append({
                        "triplet": triplet,
                        "result": query_result
                    })

        return results

    def get_all_nodes_for_visualization(self):
        """获取所有节点，为可视化准备数据"""
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        query = """
        MATCH (n)
        RETURN ID(n) AS id, 
               COALESCE(n.name, n.title, '') AS name, 
               LABELS(n)[0] AS category, 
               SIZE((n)--()) AS degree
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query)
                nodes = [
                    {
                        "id": record["id"], 
                        "name": record["name"],
                        "category": record["category"],
                        "symbolSize": min(40 + record["degree"] * 5, 80)  # 节点大小根据连接度调整
                    } 
                    for record in result
                ]
                return nodes
            except Exception as e:
                logger.error(f"获取节点时出错: {e}")
                return []
    
    def get_all_edges_for_visualization(self):
        """获取所有关系，为可视化准备数据"""
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        query = """
        MATCH (source)-[r]->(target)
        RETURN ID(source) AS source, 
               ID(target) AS target, 
               TYPE(r) AS type
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query)
                edges = [
                    {
                        "source": record["source"], 
                        "target": record["target"],
                        "name": record["type"]
                    } 
                    for record in result
                ]
                return edges
            except Exception as e:
                logger.error(f"获取关系时出错: {e}")
                return []
    
    def get_all_categories(self):
        """获取所有节点类别"""
        try:
            if not self.driver:
                logger.error("数据库未连接")
                return self._get_mock_categories()
            
            query = """
            MATCH (n)
            WITH DISTINCT LABELS(n)[0] AS category
            RETURN category
            ORDER BY category
            """
            
            with self.driver.session() as session:
                result = session.run(query)
                categories = [{"name": record["category"]} for record in result]
                
                if not categories:
                    return self._get_mock_categories()
                    
                return categories
        except Exception as e:
            logger.error(f"获取类别时出错: {e}")
            return self._get_mock_categories()
    
    def get_node_statistics(self):
        """获取节点统计信息"""
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        query = """
        MATCH (n)
        WITH LABELS(n)[0] AS label, COUNT(n) AS count
        RETURN label, count
        ORDER BY count DESC
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query)
                stats = [{"label": record["label"], "count": record["count"]} for record in result]
                return stats
            except Exception as e:
                logger.error(f"获取节点统计时出错: {e}")
                return []
    
    def get_relation_statistics(self):
        """获取关系统计信息"""
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        query = """
        MATCH ()-[r]->()
        WITH TYPE(r) AS type, COUNT(r) AS count
        RETURN type, count
        ORDER BY count DESC
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query)
                stats = [{"type": record["type"], "count": record["count"]} for record in result]
                return stats
            except Exception as e:
                logger.error(f"获取关系统计时出错: {e}")
                return []

    def _get_mock_driver(self):
        """创建模拟驱动用于离线使用"""
        from unittest.mock import MagicMock
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value = mock_session
        
        # 模拟会话上下文管理器
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        
        # 返回模拟驱动
        return mock_driver
    
    def _get_mock_tree_data(self, entity_name="桃树"):
        """
        生成模拟的树状数据
        
        Args:
            entity_name: 中心节点名称
            
        Returns:
            tuple: (nodes, edges) 模拟节点和边
        """
        # 创建中心节点
        center_node = {
            "id": 1,
            "name": entity_name,
            "category": "农作物",
            "symbolSize": 50
        }
        
        # 创建周围节点
        neighbor_nodes = [
            {"id": 2, "name": "病害", "category": "分类", "symbolSize": 40},
            {"id": 3, "name": "虫害", "category": "分类", "symbolSize": 40},
            {"id": 4, "name": "种植方法", "category": "分类", "symbolSize": 40},
            {"id": 5, "name": "桃疮痂病", "category": "病害", "symbolSize": 40},
            {"id": 6, "name": "桃小食心虫", "category": "虫害", "symbolSize": 40},
            {"id": 7, "name": "桃树施肥", "category": "种植方法", "symbolSize": 40},
            {"id": 8, "name": "桃树修剪", "category": "种植方法", "symbolSize": 40}
        ]
        
        # 创建边
        edges = [
            {"id": 1, "source": 1, "target": 2, "name": "受影响于"},
            {"id": 2, "source": 1, "target": 3, "name": "受影响于"},
            {"id": 3, "source": 1, "target": 4, "name": "相关"},
            {"id": 4, "source": 2, "target": 5, "name": "包含"},
            {"id": 5, "source": 3, "target": 6, "name": "包含"},
            {"id": 6, "source": 4, "target": 7, "name": "包含"},
            {"id": 7, "source": 4, "target": 8, "name": "包含"}
        ]
        
        # 组合所有节点
        nodes = [center_node] + neighbor_nodes
        
        return nodes, edges
    
    def _get_mock_node_neighbors(self, node_id, center_name=None):
        """
        生成模拟的节点邻居数据
        
        Args:
            node_id: 中心节点ID
            center_name: 中心节点名称，如果不提供则使用默认值
            
        Returns:
            tuple: (nodes, edges) 模拟节点和边
        """
        if not center_name:
            center_name = f"节点-{node_id}"
            
        # 创建中心节点
        center_node = {
            "id": node_id,
            "name": center_name,
            "category": "分类",
            "symbolSize": 50
        }
        
        # 生成3-5个随机邻居节点
        import random
        num_neighbors = random.randint(3, 5)
        
        # 可能的类别
        categories = ["农作物", "病害", "虫害", "防治方法", "症状", "学名", "分类"]
        
        # 创建周围节点
        neighbor_nodes = []
        edges = []
        
        for i in range(num_neighbors):
            neighbor_id = 1000 + node_id + i
            category = random.choice(categories)
            
            neighbor_node = {
                "id": neighbor_id,
                "name": f"{center_name}的{category}-{i+1}",
                "category": category,
                "symbolSize": 40
            }
            
            edge = {
                "id": 1000 + i,
                "source": node_id,
                "target": neighbor_id,
                "name": "相关"
            }
            
            neighbor_nodes.append(neighbor_node)
            edges.append(edge)
        
        # 组合所有节点
        nodes = [center_node] + neighbor_nodes
        
        return nodes, edges

    def get_entity_and_neighbors(self, entity_name, limit=10):
        """
        获取指定实体及其相邻节点和关系，限制返回节点数量
        
        Args:
            entity_name (str): 实体名称
            limit (int): 返回节点的最大数量
            
        Returns:
            tuple: (nodes, edges) 节点和边的列表
        """
        try:
            if not self.driver:
                logger.error("数据库未连接")
                return self._get_mock_tree_data(entity_name)
            
            # 查询指定实体及其1跳内的所有相关节点
            query = """
            MATCH (center)
            WHERE toLower(center.name) = toLower($entity_name) OR toLower(center.title) = toLower($entity_name)
            WITH center LIMIT 1
            OPTIONAL MATCH (center)-[r]-(neighbor)
            WITH center, neighbor, r
            LIMIT $limit
            RETURN 
                ID(center) AS center_id, 
                COALESCE(center.name, center.title, '') AS center_name, 
                LABELS(center)[0] AS center_category,
                ID(neighbor) AS neighbor_id, 
                COALESCE(neighbor.name, neighbor.title, '') AS neighbor_name, 
                LABELS(neighbor)[0] AS neighbor_category,
                ID(r) AS rel_id,
                TYPE(r) AS rel_type,
                ID(startNode(r)) AS source_id,
                ID(endNode(r)) AS target_id
            """
            
            with self.driver.session() as session:
                result = session.run(query, entity_name=entity_name, limit=limit)
                
                # 用于存储所有唯一节点和关系
                nodes_dict = {}
                edges_dict = {}
                
                # 处理查询结果
                for record in result:
                    # 添加中心节点
                    center_id = record["center_id"]
                    if center_id not in nodes_dict:
                        nodes_dict[center_id] = {
                            "id": center_id,
                            "name": record["center_name"],
                            "category": record["center_category"],
                            "symbolSize": 50  # 中心节点大小
                        }
                    
                    # 只有当邻居节点存在时才添加
                    if record["neighbor_id"] is not None:
                        # 添加邻居节点
                        neighbor_id = record["neighbor_id"]
                        if neighbor_id not in nodes_dict:
                            nodes_dict[neighbor_id] = {
                                "id": neighbor_id,
                                "name": record["neighbor_name"],
                                "category": record["neighbor_category"],
                                "symbolSize": 40  # 邻居节点大小
                            }
                        
                        # 添加关系
                        rel_id = record["rel_id"]
                        if rel_id is not None and rel_id not in edges_dict:
                            edges_dict[rel_id] = {
                                "id": rel_id,
                                "source": record["source_id"],
                                "target": record["target_id"],
                                "name": record["rel_type"]
                            }
                
                # 将字典转换为列表
                nodes = list(nodes_dict.values())
                edges = list(edges_dict.values())
                
                # 如果找不到实体，返回模拟数据
                if not nodes:
                    logger.warning(f"未能找到实体: {entity_name}")
                    return self._get_mock_tree_data(entity_name)
                
                logger.info(f"获取到实体'{entity_name}'及其{len(nodes)-1}个邻居和{len(edges)}条关系")
                return nodes, edges
        except Exception as e:
            logger.error(f"获取实体和邻居时出错: {e}")
            return self._get_mock_tree_data(entity_name)

    def get_entity_neighbors(self, node_id, limit=10):
        """
        获取指定节点ID的邻居节点和关系
        
        Args:
            node_id (int): 节点ID
            limit (int): 返回邻居节点的最大数量
            
        Returns:
            tuple: (nodes, edges) 节点和边的列表
        """
        try:
            if not self.driver:
                logger.error("数据库未连接")
                return self._get_mock_node_neighbors(node_id)
            
            # 查询指定节点及其直接邻居
            query = """
            MATCH (center)
            WHERE ID(center) = $node_id
            OPTIONAL MATCH (center)-[r]-(neighbor)
            WITH center, neighbor, r
            LIMIT $limit
            RETURN 
                ID(center) AS center_id, 
                COALESCE(center.name, center.title, '') AS center_name, 
                LABELS(center)[0] AS center_category,
                ID(neighbor) AS neighbor_id, 
                COALESCE(neighbor.name, neighbor.title, '') AS neighbor_name, 
                LABELS(neighbor)[0] AS neighbor_category,
                ID(r) AS rel_id,
                TYPE(r) AS rel_type,
                ID(startNode(r)) AS source_id,
                ID(endNode(r)) AS target_id
            """
            
            with self.driver.session() as session:
                result = session.run(query, node_id=node_id, limit=limit)
                
                # 用于存储所有唯一节点和关系
                nodes_dict = {}
                edges_dict = {}
                center_name = None
                
                # 处理查询结果
                for record in result:
                    # 添加中心节点
                    center_id = record["center_id"]
                    center_name = record["center_name"]
                    if center_id not in nodes_dict:
                        nodes_dict[center_id] = {
                            "id": center_id,
                            "name": center_name,
                            "category": record["center_category"],
                            "symbolSize": 50  # 中心节点大小
                        }
                    
                    # 如果有邻居节点（可能是孤立节点）
                    if record["neighbor_id"] is not None:
                        # 添加邻居节点
                        neighbor_id = record["neighbor_id"]
                        if neighbor_id not in nodes_dict:
                            nodes_dict[neighbor_id] = {
                                "id": neighbor_id,
                                "name": record["neighbor_name"],
                                "category": record["neighbor_category"],
                                "symbolSize": 40  # 邻居节点大小
                            }
                        
                        # 添加关系
                        rel_id = record["rel_id"]
                        if rel_id is not None and rel_id not in edges_dict:
                            edges_dict[rel_id] = {
                                "id": rel_id,
                                "source": record["source_id"],
                                "target": record["target_id"],
                                "name": record["rel_type"]
                            }
                
                # 将字典转换为列表
                nodes = list(nodes_dict.values())
                edges = list(edges_dict.values())
                
                # 如果找不到节点或周围没有邻居，返回模拟数据
                if not nodes or len(nodes) <= 1:
                    logger.warning(f"无法找到ID为 {node_id} 的节点或其邻居")
                    return self._get_mock_node_neighbors(node_id, center_name)
                
                logger.info(f"获取到节点ID {node_id} 及其{len(nodes)-1}个邻居和{len(edges)}条关系")
                return nodes, edges
        except Exception as e:
            logger.error(f"获取节点邻居时出错: {e}")
            return self._get_mock_node_neighbors(node_id)

    def search_entities(self, query):
        """
        搜索实体
        
        Args:
            query (str): 搜索关键词
            
        Returns:
            list: 匹配的实体列表
        """
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        # 使用模糊匹配搜索实体
        cypher_query = """
        MATCH (n)
        WHERE toLower(COALESCE(n.name, n.title, '')) CONTAINS toLower($query)
        RETURN ID(n) AS id, 
               COALESCE(n.name, n.title, '') AS name, 
               LABELS(n)[0] AS category
        LIMIT 20
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(cypher_query, query=query)
                entities = [
                    {
                        "id": record["id"],
                        "name": record["name"],
                        "category": record["category"]
                    }
                    for record in result
                ]
                return entities
            except Exception as e:
                logger.error(f"搜索实体时出错: {e}")
                return []

    def get_top_connected_nodes(self, limit=10):
        """
        获取连接数最多的节点
        
        Args:
            limit (int): 返回的节点数量
            
        Returns:
            list: 连接最多的节点列表
        """
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        query = """
        MATCH (n)
        WITH n, SIZE((n)--()) AS degree
        ORDER BY degree DESC
        LIMIT $limit
        RETURN ID(n) AS id, 
               COALESCE(n.name, n.title, '') AS name, 
               LABELS(n)[0] AS category,
               degree
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(query, limit=limit)
                nodes = [
                    {
                        "id": record["id"], 
                        "name": record["name"],
                        "category": record["category"],
                        "symbolSize": min(40 + record["degree"] * 2, 80)  # 节点大小根据连接度调整
                    } 
                    for record in result
                ]
                logger.info(f"获取到{len(nodes)}个连接最多的节点")
                return nodes
            except Exception as e:
                logger.error(f"获取连接最多的节点时出错: {e}")
                return []
    
    def get_subgraph_from_nodes(self, node_ids, depth=1):
        """
        获取以特定节点为中心的子图
        
        Args:
            node_ids (list): 中心节点ID列表
            depth (int): 查询深度，默认为1跳
            
        Returns:
            tuple: (nodes, edges) 节点和边的列表
        """
        if not self.driver or not node_ids:
            logger.error("数据库未连接或节点ID列表为空")
            return [], []
        
        # Neo4j不允许在关系模式中使用参数，因此根据深度选择适当的查询
        if depth == 1:
            query = """
            MATCH (center)
            WHERE ID(center) IN $node_ids
            OPTIONAL MATCH path = (center)-[*1..1]-(neighbor)
            WITH COLLECT(center) + COLLECT(neighbor) AS nodes, 
                 COLLECT(RELATIONSHIPS(path)) AS rels
            UNWIND nodes AS n
            WITH DISTINCT n
            RETURN ID(n) AS id, 
                   COALESCE(n.name, n.title, '') AS name, 
                   LABELS(n)[0] AS category, 
                   SIZE((n)--()) AS degree
            """
        elif depth == 2:
            query = """
            MATCH (center)
            WHERE ID(center) IN $node_ids
            OPTIONAL MATCH path = (center)-[*1..2]-(neighbor)
            WITH COLLECT(center) + COLLECT(neighbor) AS nodes, 
                 COLLECT(RELATIONSHIPS(path)) AS rels
            UNWIND nodes AS n
            WITH DISTINCT n
            RETURN ID(n) AS id, 
                   COALESCE(n.name, n.title, '') AS name, 
                   LABELS(n)[0] AS category, 
                   SIZE((n)--()) AS degree
            """
        else:
            # 默认使用深度1
            logger.warning(f"不支持的深度值 {depth}，使用默认深度 1")
            query = """
            MATCH (center)
            WHERE ID(center) IN $node_ids
            OPTIONAL MATCH path = (center)-[*1..1]-(neighbor)
            WITH COLLECT(center) + COLLECT(neighbor) AS nodes, 
                 COLLECT(RELATIONSHIPS(path)) AS rels
            UNWIND nodes AS n
            WITH DISTINCT n
            RETURN ID(n) AS id, 
                   COALESCE(n.name, n.title, '') AS name, 
                   LABELS(n)[0] AS category, 
                   SIZE((n)--()) AS degree
            """
        
        with self.driver.session() as session:
            try:
                # 获取节点
                result = session.run(query, node_ids=node_ids)
                nodes = [
                    {
                        "id": record["id"], 
                        "name": record["name"],
                        "category": record["category"],
                        "symbolSize": min(40 + record["degree"] * 2, 80)  # 节点大小根据连接度调整
                    } 
                    for record in result
                ]
                
                # 如果没有获取到节点，返回空结果
                if not nodes:
                    logger.warning("未能获取到节点数据")
                    return [], []
                
                # 获取边
                # 使用OR条件而不是参数列表，避免参数过多的问题
                node_id_list = ", ".join([str(node_id) for node_id in node_ids])
                edge_query = f"""
                MATCH (n1)-[r]->(n2)
                WHERE ID(n1) IN [{node_id_list}] OR ID(n2) IN [{node_id_list}]
                RETURN ID(n1) AS source, ID(n2) AS target, TYPE(r) AS type
                """
                
                edge_result = session.run(edge_query)
                edges = [
                    {
                        "source": record["source"], 
                        "target": record["target"],
                        "name": record["type"]
                    } 
                    for record in edge_result
                ]
                
                # 过滤边，确保两端的节点都在节点列表中
                node_id_set = {node["id"] for node in nodes}
                edges = [edge for edge in edges 
                         if edge["source"] in node_id_set and edge["target"] in node_id_set]
                
                logger.info(f"获取到以{len(node_ids)}个节点为中心的子图，包含{len(nodes)}个节点和{len(edges)}条边")
                return nodes, edges
            except Exception as e:
                logger.error(f"获取子图时出错: {e}")
                return [], []

    def _get_mock_categories(self):
        """返回模拟的分类数据"""
        return [
            {"name": "农作物"},
            {"name": "病害"},
            {"name": "虫害"},
            {"name": "防治方法"},
            {"name": "症状"},
            {"name": "学名"},
            {"name": "分类"}
        ]

    def get_all_node_labels(self):
        """
        Get all node labels (entity types) from the database

        Returns:
            list: List of node label strings
        """
        try:
            with self.driver.session() as session:
                result = session.run("CALL db.labels()")
                return [record["label"] for record in result]
        except Exception as e:
            self.log.error(f"Error getting node labels: {str(e)}")
            # Return mock node labels as fallback
            return ['Researcher', 'Paper', 'Institution', 'Field', 'Venue']
    
    def get_sample_graph(self):
        """
        Get a sample graph with mock data when the database is unavailable
        
        Returns:
            tuple: (nodes, links) containing mock graph data
        """
        # Create mock nodes with different entity types
        nodes = [
            {"id": 1, "name": "John Smith", "category": "Researcher", "publications": 15, "citations": 320},
            {"id": 2, "name": "Neural Networks", "category": "Field", "papers_count": 1250},
            {"id": 3, "name": "MIT", "category": "Institution", "founded": 1861, "researchers": 1500},
            {"id": 4, "name": "Deep Learning Applications", "category": "Paper", "year": 2020, "citations": 45},
            {"id": 5, "name": "ICML 2023", "category": "Venue", "acceptance_rate": 0.22},
            {"id": 6, "name": "Jane Doe", "category": "Researcher", "publications": 22, "citations": 480},
            {"id": 7, "name": "Machine Learning", "category": "Field", "papers_count": 5600},
            {"id": 8, "name": "Stanford", "category": "Institution", "founded": 1885, "researchers": 2200},
            {"id": 9, "name": "Graph Neural Networks", "category": "Field", "papers_count": 850},
            {"id": 10, "name": "Advances in GNN", "category": "Paper", "year": 2021, "citations": 32},
            {"id": 11, "name": "Alice Johnson", "category": "Researcher", "publications": 8, "citations": 120},
            {"id": 12, "name": "Knowledge Graphs", "category": "Field", "papers_count": 750},
            {"id": 13, "name": "UC Berkeley", "category": "Institution", "founded": 1868, "researchers": 1800},
            {"id": 14, "name": "KG Applications", "category": "Paper", "year": 2022, "citations": 18},
            {"id": 15, "name": "AAAI 2023", "category": "Venue", "acceptance_rate": 0.25}
        ]
        
        # Create mock relationships between nodes
        links = [
            {"source": 1, "target": 2, "type": "RESEARCHES"},
            {"source": 1, "target": 3, "type": "AFFILIATED_WITH"},
            {"source": 1, "target": 4, "type": "AUTHORED"},
            {"source": 4, "target": 5, "type": "PUBLISHED_IN"},
            {"source": 6, "target": 7, "type": "RESEARCHES"},
            {"source": 6, "target": 8, "type": "AFFILIATED_WITH"},
            {"source": 6, "target": 1, "type": "COLLABORATES_WITH"},
            {"source": 9, "target": 2, "type": "IS_SUBFIELD_OF"},
            {"source": 6, "target": 9, "type": "RESEARCHES"},
            {"source": 6, "target": 10, "type": "AUTHORED"},
            {"source": 10, "target": 5, "type": "PUBLISHED_IN"},
            {"source": 11, "target": 12, "type": "RESEARCHES"},
            {"source": 11, "target": 13, "type": "AFFILIATED_WITH"},
            {"source": 11, "target": 14, "type": "AUTHORED"},
            {"source": 14, "target": 15, "type": "PUBLISHED_IN"},
            {"source": 11, "target": 6, "type": "COLLABORATES_WITH"},
            {"source": 12, "target": 7, "type": "IS_SUBFIELD_OF"}
        ]
        
        return nodes, links
    
    def get_sample_subgraph(self, limit=20):
        """
        获取样本子图，用于知识图谱可视化
        
        Args:
            limit: 限制返回的节点数量，默认为20
            
        Returns:
            tuple: (nodes, links) 包含节点和关系的元组
        """
        try:
            # 首先尝试从数据库获取数据
            if self.driver:
                try:
                    # 获取连接度最高的节点
                    top_nodes = self.get_top_connected_nodes(limit=limit//2)
                    if top_nodes and len(top_nodes) > 0:
                        node_ids = [node['id'] for node in top_nodes]
                        return self.get_subgraph_from_nodes(node_ids, depth=1)
                except Exception as e:
                    logger.warning(f"从数据库获取示例子图失败，将使用模拟数据: {str(e)}")
            
            # 如果数据库操作失败或没有连接，使用样本数据
            nodes, links = self.get_sample_graph()
            
            # 根据limit参数限制返回的节点数量
            if len(nodes) > limit:
                nodes = nodes[:limit]
                # 只保留与选定节点相关的链接
                node_ids = {node['id'] for node in nodes}
                links = [link for link in links if link['source'] in node_ids and link['target'] in node_ids]
            
            # 为节点添加类别信息，用于可视化
            for node in nodes:
                if 'category' in node:
                    # 保持category字段为每种类别的索引
                    node_categories = self._get_mock_categories()
                    category_name = node['category']
                    category_index = next((i for i, cat in enumerate(node_categories) if cat['name'] == category_name), 0)
                    node['category'] = category_index
            
            return nodes, links
        except Exception as e:
            logger.error(f"生成样本子图失败: {str(e)}")
            # 返回最小的有效图
            return [
                {"id": 1, "name": "示例节点A", "category": 0},
                {"id": 2, "name": "示例节点B", "category": 1}
            ], [
                {"source": 1, "target": 2, "type": "示例关系"}
            ]
        
    def find_shortest_paths(self, source_id, target_id, max_depth=3):
        """
        Find shortest paths between two nodes
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            max_depth: Maximum path length to consider
            
        Returns:
            list: List of paths, where each path is a list of nodes
        """
        try:
            query = """
            MATCH path = shortestPath((source)-[*1..{max_depth}]-(target))
            WHERE id(source) = $source_id AND id(target) = $target_id
            RETURN path
            LIMIT 5
            """
            
            with self.driver.session() as session:
                result = session.run(
                    query,
                    source_id=int(source_id),
                    target_id=int(target_id),
                    max_depth=max_depth
                )
                
                paths = []
                for record in result:
                    path = record["path"]
                    path_nodes = []
                    
                    for i, node in enumerate(path.nodes):
                        node_data = {
                            'id': node.id,
                            'name': node.get('name', ''),
                            'type': next(iter(node.labels), 'Unknown')
                        }
                        
                        # Add relation to next node if not the last node
                        if i < len(path.nodes) - 1:
                            relationship = path.relationships[i]
                            node_data['relation_to_next'] = relationship.type
                            
                        path_nodes.append(node_data)
                    
                    paths.append(path_nodes)
                
                return paths
        except Exception as e:
            self.log.error(f"Error finding paths between nodes {source_id} and {target_id}: {str(e)}")
            # Return empty list in case of error
            return []
