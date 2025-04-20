from neo4j import GraphDatabase
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection

# Neo4j连接配置
neo4j_uri = "bolt://localhost:7687"
neo4j_user = "neo4j"
neo4j_password = "password"

# Milvus连接配置
milvus_host = "localhost"
milvus_port = "19530"

# 连接到Neo4j
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

def fetch_entities_from_neo4j():
    query = """
    MATCH (n)
    RETURN id(n) AS id, n.name AS name, n.embedding AS embedding
    """
    with driver.session() as session:
        result = session.run(query)
        return [record for record in result]

# 连接到Milvus
connections.connect("default", host=milvus_host, port=milvus_port)

# 定义Milvus集合的schema
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=128)
]
schema = CollectionSchema(fields, "Neo4j Entities Collection")

# 创建或加载集合
collection = Collection("neo4j_entities", schema)

# 从Neo4j中获取实体数据
entities = fetch_entities_from_neo4j()

# 准备数据以插入到Milvus
ids = [entity["id"] for entity in entities]
embeddings = [entity["embedding"] for entity in entities]

# 插入数据到Milvus
entities_to_insert = [ids, embeddings]
collection.insert(entities_to_insert)

# 创建索引（如果需要）
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
}
collection.create_index("embedding", index_params)

# 加载集合到内存
collection.load()

# 关闭Neo4j连接
driver.close()

print("数据导入完成")