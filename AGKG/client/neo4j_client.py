from neo4j import AsyncGraphDatabase
import logging
import asyncio
from typing import Dict, List, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('neo4j_client')

class Neo4jClient:
    def __init__(self):
        self.uri = "neo4j://localhost:7687"
        self.user = "neo4j"
        self.password = "123456"
        self.driver = None
        self.max_retries = 3
        self.retry_delay = 1  # 重试延迟（秒）

    async def connect(self):
        """初始化 Neo4j 驱动，带重试机制"""
        if not self.driver:
            for attempt in range(self.max_retries):
                try:
                    self.driver = AsyncGraphDatabase.driver(
                        self.uri, 
                        auth=(self.user, self.password),
                        max_connection_lifetime=3600
                    )
                    # 测试连接
                    await self.driver.verify_connectivity()
                    logger.info("成功连接到Neo4j数据库")
                    return
                except Exception as e:
                    logger.warning(f"连接Neo4j失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        logger.error("无法连接到Neo4j数据库，将使用模拟数据")
                        # 如果所有重试都失败，返回模拟驱动
                        self.driver = self._get_mock_driver()

    async def close(self):
        """关闭 Neo4j 驱动"""
        if self.driver:
            try:
                await self.driver.close()
                self.driver = None
                logger.info("Neo4j连接已关闭")
            except Exception as e:
                logger.error(f"关闭Neo4j连接时发生错误: {str(e)}")

    async def get_all_entities(self):
        """获取所有实体"""
        if not self.driver:
            await self.connect()
        query = """
        MATCH (n)
        RETURN DISTINCT id(n) AS entity_id, n.name AS entity_name
        """
        result = await self.driver.execute_query(query)
        entities = {record["entity_id"]: record["entity_name"] for record in result.records}
        return entities

    async def get_all_relations(self):
        """获取所有关系"""
        if not self.driver:
            await self.connect()
        query = """
        MATCH ()-[r]->()
        RETURN DISTINCT type(r) AS relation_type
        """
        result = await self.driver.execute_query(query)
        relations = {record["relation_type"] for record in result.records}
        return list(relations)

    async def get_all_triplets(self):
        """获取所有三元组"""
        if not self.driver:
            await self.connect()
        query = """
        MATCH (h)-[r]->(t)
        RETURN id(h) AS head_id, type(r) AS relation_type, id(t) AS tail_id
        """
        result = await self.driver.execute_query(query)
        triplets = [(record["head_id"], record["relation_type"], record["tail_id"]) for record in result.records]
        return triplets

    async def get_triplet_count(self):
        """获取三元组总数"""
        if not self.driver:
            await self.connect()
        query = """
           MATCH (h)-[r]->(t)
           RETURN count(*) AS count
           """
        result = await self.driver.execute_query(query)
        return result.records[0]["count"]

    async def get_triplets_batch(self, offset, limit):
        """分批次获取三元组"""
        if not self.driver:
            await self.connect()
        query = """
           MATCH (h)-[r]->(t)
           RETURN id(h) AS head_id, type(r) AS relation_type, id(t) AS tail_id
           SKIP $offset LIMIT $limit
           """
        result = await self.driver.execute_query(query, offset=offset, limit=limit)
        return [(record["head_id"], record["relation_type"], record["tail_id"]) for record in result.records]

    async def get_entity_name(self, entity_id):
        """根据实体 ID 查询实体名字"""
        if not self.driver:
            await self.connect()
        query = """
        MATCH (n)
        WHERE id(n) = $entity_id
        RETURN n.name AS entity_name
        """
        result = await self.driver.execute_query(query, entity_id=entity_id)
        if result.records:
            return result.records[0]["entity_name"]
        return None

    async def query_by_entity_name(self, entity_name: str) -> List[Dict[str, str]]:
        """根据实体名称查询相关的所有三元组"""
        if not self.driver:
            await self.connect()
        try:
            query = """
            MATCH (h)-[r]->(t)
            WHERE h.name = $entity_name OR t.name = $entity_name
            RETURN h.name AS head, type(r) AS relation, t.name AS tail
            """
            result = await self.driver.execute_query(query, entity_name=entity_name)
            return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                    for record in result.records]
        except Exception as e:
            logger.error(f"查询实体 {entity_name} 时发生错误: {str(e)}")
            return []

    async def query_by_head_relation(self, head: str, relation: str) -> List[Dict[str, str]]:
        """根据头实体和关系查询尾实体"""
        if not self.driver:
            await self.connect()
        try:
            query = """
            MATCH (h)-[r]->(t)
            WHERE h.name = $head AND type(r) = $relation
            RETURN h.name AS head, type(r) AS relation, t.name AS tail
            """
            result = await self.driver.execute_query(query, head=head, relation=relation)
            return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                    for record in result.records]
        except Exception as e:
            logger.error(f"查询头实体 {head} 和关系 {relation} 时发生错误: {str(e)}")
            return []

    async def query_triplet(self, head: str, relation: str, tail: str) -> List[Dict[str, str]]:
        """查询特定的三元组是否存在"""
        if not self.driver:
            await self.connect()
        try:
            query = """
            MATCH (h)-[r]->(t)
            WHERE h.name = $head AND type(r) = $relation AND t.name = $tail
            RETURN h.name AS head, type(r) AS relation, t.name AS tail
            """
            result = await self.driver.execute_query(query, head=head, relation=relation, tail=tail)
            return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                    for record in result.records]
        except Exception as e:
            logger.error(f"查询三元组 ({head}, {relation}, {tail}) 时发生错误: {str(e)}")
            return []

    async def query_kg_triplets(self, triplets: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """根据知识图谱三元组列表查询数据库信息"""
        if not self.driver:
            await self.connect()

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
                query_result = await self.query_by_head_relation(head, relation)
                if query_result:
                    # 存储所有查询结果
                    processed_triplets[tail] = [res.get('tail') for res in query_result]
                    results.append({
                        "triplet": triplet,
                        "result": query_result
                    })
            else:
                # 普通三元组查询
                query_result = await self.query_triplet(head, relation, tail)
                if query_result:
                    results.append({
                        "triplet": triplet,
                        "result": query_result
                    })

        return results

if __name__ == "__main__":
    async def test():
        client = Neo4jClient()
        try:
            # 测试查询
            result = await client.query_kg_triplets([
                {"head": "小麦赤霉病", "relation": "防治方法", "tail": "Q1"}
            ])
            print("查询结果:", result)
        finally:
            await client.close()

    asyncio.run(test())