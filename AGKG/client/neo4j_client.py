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
            
        self.url = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "123456")
        self.driver = None
        self.max_retries = 3
        self.retry_delay = 1  # 重试延迟（秒）
        
        # 自动连接数据库
        self.connect()
        self._initialized = True

    def connect(self):
        """连接到Neo4j数据库"""
        # 如果已经连接成功，直接返回True
        if self.driver:
            try:
                # 快速测试连接是否有效
                with self.driver.session() as session:
                    session.run("RETURN 1")
                return True
            except Exception:
                # 如果测试失败，继续尝试重新连接
                self.driver = None
        
        try:
            if not self.url or not self.username or not self.password:
                logger.error("未提供连接信息")
                self.driver = None
                return False

            self.driver = GraphDatabase.driver(
                self.url, 
                auth=(self.username, self.password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("成功连接到Neo4j数据库")
            return True
        except Exception as e:
            logger.error(f"连接到Neo4j数据库时出错: {e}")
            self.driver = None
            return False

    def close(self):
        """关闭 Neo4j 驱动"""
        if self.driver:
            try:
                self.driver.close()
                self.driver = None
                logger.info("Neo4j连接已关闭")
            except Exception as e:
                logger.error(f"关闭Neo4j连接时发生错误: {str(e)}")

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
                return [], []
            
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
                
                # 如果找不到实体，返回空数据
                if not nodes:
                    logger.warning(f"未能找到实体: {entity_name}")
                    return [], []
                
                logger.info(f"获取到实体'{entity_name}'及其{len(nodes)-1}个邻居和{len(edges)}条关系")
                return nodes, edges
        except Exception as e:
            logger.error(f"获取实体和邻居时出错: {e}")
            return [], []

    def get_entity_neighbors_by_id(self, node_id, limit=10):
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
                return [], []
            
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
                
                # 如果找不到指定节点，返回空数据
                if not nodes:
                    logger.warning(f"未能找到节点: {node_id}")
                    return [], []
                
                logger.info(f"获取到节点{node_id}及其{len(nodes)-1}个邻居和{len(edges)}条关系")
                return nodes, edges
        except Exception as e:
            logger.error(f"获取节点邻居时出错: {e}")
            return [], []

    def search_entities(self, search_term):
        """
        搜索实体
        
        Args:
            search_term (str): 搜索关键词
            
        Returns:
            list: 匹配的实体列表
        """
        if not self.driver:
            logger.error("数据库未连接")
            return []
        
        # 使用模糊匹配搜索实体
        cypher_query = """
        MATCH (n)
        WHERE toLower(COALESCE(n.name, n.title, '')) CONTAINS toLower($search_term)
        RETURN ID(n) AS id, 
               COALESCE(n.name, n.title, '') AS name, 
               LABELS(n)[0] AS category
        LIMIT 20
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(cypher_query, search_term=search_term)
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
