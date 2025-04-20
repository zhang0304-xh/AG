from neo4j import AsyncGraphDatabase

class Neo4jClient:
    def __init__(self):
        self.uri = "neo4j://localhost:7687"
        self.user = "neo4j"
        self.password = "123456"
        self.driver = None

    async def connect(self):
        """初始化 Neo4j 驱动"""
        if not self.driver:
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def close(self):
        """关闭 Neo4j 驱动"""
        if self.driver:
            await self.driver.close()
            self.driver = None

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

    async def query_by_entity_name(self, entity_name):
        """根据实体名称查询相关的所有三元组"""
        if not self.driver:
            await self.connect()
        query = """
        MATCH (h)-[r]->(t)
        WHERE h.name = $entity_name OR t.name = $entity_name
        RETURN h.name AS head, type(r) AS relation, t.name AS tail
        """
        result = await self.driver.execute_query(query, entity_name=entity_name)
        return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                for record in result.records]

    async def query_by_head_relation(self, head, relation):
        """根据头实体和关系查询尾实体"""
        if not self.driver:
            await self.connect()
        query = """
        MATCH (h)-[r]->(t)
        WHERE h.name = $head AND type(r) = $relation
        RETURN h.name AS head, type(r) AS relation, t.name AS tail
        """
        result = await self.driver.execute_query(query, head=head, relation=relation)
        return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                for record in result.records]

    async def query_triplet(self, head, relation, tail):
        """查询特定的三元组是否存在"""
        if not self.driver:
            await self.connect()
        query = """
        MATCH (h)-[r]->(t)
        WHERE h.name = $head AND type(r) = $relation AND t.name = $tail
        RETURN h.name AS head, type(r) AS relation, t.name AS tail
        """
        result = await self.driver.execute_query(query, head=head, relation=relation, tail=tail)
        return [{"head": record["head"], "relation": record["relation"], "tail": record["tail"]} 
                for record in result.records]

    async def query_kg_triplets(self, triplets):
        """根据知识图谱三元组列表查询数据库信息"""
        results = []
        for triplet in triplets:
            head = triplet.get("head")
            relation = triplet.get("relation")
            tail = triplet.get("tail")
            
            # 根据三元组的完整性选择查询方式
            if head and relation and tail:
                # 完整三元组，验证是否存在
                query_result = await self.query_triplet(head, relation, tail)
            elif head and relation:
                # 头实体和关系，查找尾实体
                query_result = await self.query_by_head_relation(head, relation)
            elif head:
                # 只有头实体，查找所有相关三元组
                query_result = await self.query_by_entity_name(head)
            else:
                query_result = []
                
            results.append({
                "triplet": triplet,
                "result": query_result
            })
            
        return results