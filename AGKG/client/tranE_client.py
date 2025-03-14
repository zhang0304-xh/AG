import os
import numpy as np
import random
import pickle
from AGKG.client.neo4j_client import Neo4jClient
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer


class TransEClient:
    def __init__(self, embedding_dim=100, margin=1.0, learning_rate=0.01):
        self.neo4j_client = Neo4jClient()
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.learning_rate = learning_rate
        self.entities = {}
        self.relations = {}

    async def initialize_embeddings(self):
        """初始化实体和关系的嵌入向量"""
        # 获取所有实体
        entities = await self.neo4j_client.get_nodes_by_label("Entity")
        for entity in entities:
            entity_id = entity["id"]
            self.entities[entity_id] = {
                "name": entity["name"],
                "embedding": np.random.uniform(-1, 1, self.embedding_dim)
            }

        # 获取所有关系类型
        relationships = await self.neo4j_client.get_relationships(None)
        for rel in relationships:
            if rel["type"] not in self.relations:
                self.relations[rel["type"]] = np.random.uniform(-1, 1, self.embedding_dim)

    async def train(self, epochs=100, batch_size=1000):
        """训练TransE模型"""
        for epoch in range(epochs):
            print(f"Epoch {epoch + 1}/{epochs}")
            
            # 获取一批三元组
            relationships = await self.neo4j_client.get_relationships(None)
            batch = relationships[:batch_size]

            for rel in batch:
                head = rel["start_id"]
                relation = rel["type"]
                tail = rel["end_id"]

                # 获取正样本的嵌入
                h = self.entities[head]["embedding"]
                r = self.relations[relation]
                t = self.entities[tail]["embedding"]

                # 计算正样本的距离
                pos_distance = np.linalg.norm(h + r - t)

                # 获取负样本
                neg_head, neg_tail = self.get_negative_sample(head, tail)

                # 计算负样本的距离
                neg_distance = np.linalg.norm(self.entities[neg_head]["embedding"] + r - self.entities[neg_tail]["embedding"])

                # 计算损失
                loss = max(0, pos_distance - neg_distance + self.margin)

                # 更新嵌入
                if loss > 0:
                    grad = h + r - t
                    self.entities[head]["embedding"] -= self.learning_rate * grad
                    self.relations[relation] -= self.learning_rate * grad
                    self.entities[tail]["embedding"] += self.learning_rate * grad

                    grad = self.entities[neg_head]["embedding"] + r - self.entities[neg_tail]["embedding"]
                    self.entities[neg_head]["embedding"] += self.learning_rate * grad
                    self.relations[relation] += self.learning_rate * grad
                    self.entities[neg_tail]["embedding"] -= self.learning_rate * grad

    def get_negative_sample(self, head, tail):
        """随机选择一个实体作为负样本的头或尾"""
        entities = list(self.entities.keys())
        neg_head = random.choice(entities)
        neg_tail = random.choice(entities)
        return neg_head, neg_tail

    def save_embeddings(self, entity_file="entity_embeddings.pkl", relation_file="relation_embeddings.pkl"):
        """保存实体和关系的嵌入向量"""
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transE_data"
        )
        os.makedirs(data_dir, exist_ok=True)

        entity_path = os.path.join(data_dir, entity_file)
        relation_path = os.path.join(data_dir, relation_file)

        # 保存实体嵌入和名称
        with open(entity_path, "wb") as f:
            pickle.dump(self.entities, f)

        # 保存关系嵌入
        with open(relation_path, "wb") as f:
            pickle.dump(self.relations, f)

    def load_embeddings(self, entity_file="entity_embeddings.pkl", relation_file="relation_embeddings.pkl"):
        """加载实体和关系的嵌入向量"""
        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "transE_data"
        )
        entity_path = os.path.join(data_dir, entity_file)
        relation_path = os.path.join(data_dir, relation_file)

        if not os.path.exists(entity_path) or not os.path.exists(relation_path):
            raise FileNotFoundError("Embedding files not found. Please train the model first.")

        # 加载实体嵌入
        with open(entity_path, "rb") as f:
            self.entities = pickle.load(f)

        # 加载关系嵌入
        with open(relation_path, "rb") as f:
            self.relations = pickle.load(f)

    async def map_external_entity_by_name(self, external_entity_name):
        """通过名称映射外部实体到知识图谱中的实体"""
        # 获取所有实体
        entities = await self.neo4j_client.get_nodes_by_label("Entity")
        
        # 创建文本向量化器
        vectorizer = CountVectorizer()
        entity_names = [entity["name"] for entity in entities]
        entity_vectors = vectorizer.fit_transform(entity_names)
        
        # 计算外部实体名称的向量
        external_vector = vectorizer.transform([external_entity_name])
        
        # 计算相似度
        similarities = cosine_similarity(external_vector, entity_vectors)[0]
        
        # 获取最相似的实体
        most_similar_idx = np.argmax(similarities)
        most_similar_entity = entities[most_similar_idx]
        
        return most_similar_entity if similarities[most_similar_idx] > 0.5 else None


if __name__ == "__main__":
    transE = TransEClient()

    try:
        transE.load_embeddings()
    except FileNotFoundError:
        transE.initialize_embeddings()
        transE.train(epochs=50)
        transE.save_embeddings()

