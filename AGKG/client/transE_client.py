import numpy as np
import pickle
import asyncio
from tqdm import tqdm  # 用于显示进度条
from neo4j import AsyncGraphDatabase

from AGKG.client.neo4j_client import Neo4jClient


class TransEClient:
    def __init__(self, embedding_dim=100, margin=1.0, learning_rate=0.01):
        self.neo4j_client = Neo4jClient()
        self.embedding_dim = embedding_dim
        self.margin = margin
        self.learning_rate = learning_rate
        self.entities = {}  # 实体ID到嵌入向量的映射
        self.relations = {}  # 关系到嵌入向量的映射

    async def initialize_embeddings(self):
        """初始化嵌入向量"""
        print("Initializing embeddings...")
        entities = await self.neo4j_client.get_all_entities()
        relations = await self.neo4j_client.get_all_relations()
        # 使用正态分布初始化实体嵌入
        for entity in entities:
            self.entities[entity] = np.random.randn(self.embedding_dim).astype(np.float32)
        # 初始化关系嵌入
        for relation in relations:
            self.relations[relation] = np.random.randn(self.embedding_dim).astype(np.float32)
        print(f"Initialized {len(self.entities)} entities and {len(self.relations)} relations.")

    async def train(self, num_epochs=100, batch_size=1024):
        """训练模型"""
        total_triplets = await self.neo4j_client.get_triplet_count()
        print(f"Total triplets: {total_triplets}")
        print(f"Starting training for {num_epochs} epochs...")

        for epoch in range(num_epochs):
            print(f"\nEpoch {epoch + 1}/{num_epochs}")
            total_loss = 0.0
            # 使用 tqdm 显示批次进度
            with tqdm(total=total_triplets, desc=f"Epoch {epoch + 1}", unit="triplet") as pbar:
                for offset in range(0, total_triplets, batch_size):
                    batch = await self.neo4j_client.get_triplets_batch(offset, batch_size)
                    batch_loss = 0.0
                    for h, r, t in batch:
                        # 正样本
                        h_vec = self.entities[h]
                        r_vec = self.relations[r]
                        t_vec = self.entities[t]
                        pos_distance = np.linalg.norm(h_vec + r_vec - t_vec, ord=2)

                        # 生成负样本
                        if np.random.rand() < 0.5:
                            neg_h = np.random.choice(list(self.entities.keys()))
                            neg_t = t
                        else:
                            neg_h = h
                            neg_t = np.random.choice(list(self.entities.keys()))
                        neg_h_vec = self.entities[neg_h]
                        neg_t_vec = self.entities[neg_t]
                        neg_distance = np.linalg.norm(neg_h_vec + r_vec - neg_t_vec, ord=2)

                        # 计算损失
                        loss = max(0, self.margin + pos_distance - neg_distance)
                        if loss > 0:
                            # 计算梯度
                            grad_pos = (h_vec + r_vec - t_vec) / (pos_distance + 1e-8)
                            grad_neg = (neg_h_vec + r_vec - neg_t_vec) / (neg_distance + 1e-8)

                            # 更新正样本参数
                            self.entities[h] -= self.learning_rate * grad_pos
                            self.relations[r] -= self.learning_rate * grad_pos
                            self.entities[t] += self.learning_rate * grad_pos

                            # 更新负样本参数
                            self.entities[neg_h] += self.learning_rate * grad_neg
                            self.relations[r] += self.learning_rate * grad_neg
                            self.entities[neg_t] -= self.learning_rate * grad_neg

                            batch_loss += loss

                    total_loss += batch_loss / len(batch)
                    pbar.update(len(batch))  # 更新进度条
                    pbar.set_postfix(loss=total_loss / (offset // batch_size + 1))  # 显示当前平均损失

            print(f"Epoch {epoch + 1} completed. Average loss: {total_loss / (total_triplets // batch_size)}")

            # 保存临时检查点
            self.save_checkpoint(f"checkpoint_epoch_{epoch + 1}.pkl")
            print(f"Checkpoint saved for epoch {epoch + 1}.")

    def save_checkpoint(self, file_path):
        """保存临时检查点"""
        with open(file_path, 'wb') as f:
            pickle.dump({
                'entities': self.entities,
                'relations': self.relations,
                'config': {
                    'embedding_dim': self.embedding_dim,
                    'margin': self.margin,
                    'learning_rate': self.learning_rate
                }
            }, f)
        print(f"Checkpoint saved to {file_path}.")

    def save_embeddings(self, file_path):
        """保存最终的嵌入向量文件"""
        with open(file_path, 'wb') as f:
            pickle.dump({
                'entities': self.entities,
                'relations': self.relations,
                'config': {
                    'embedding_dim': self.embedding_dim,
                    'margin': self.margin,
                    'learning_rate': self.learning_rate
                }
            }, f)
        print(f"Final embeddings saved to {file_path}.")

    def load_embeddings(self, file_path):
        """加载嵌入向量文件"""
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
            self.entities = data['entities']
            self.relations = data['relations']
            config = data.get('config', {})
            self.embedding_dim = config.get('embedding_dim', 100)
            self.margin = config.get('margin', 1.0)
            self.learning_rate = config.get('learning_rate', 0.01)
        print(f"Embeddings loaded from {file_path}.")

    def validate(self, sample_triplets):
        """验证嵌入向量的合理性"""
        print("\nValidating embeddings...")
        for h, r, t in sample_triplets:
            if h in self.entities and r in self.relations and t in self.entities:
                h_vec = self.entities[h]
                r_vec = self.relations[r]
                t_vec = self.entities[t]
                distance = np.linalg.norm(h_vec + r_vec - t_vec, ord=2)
                print(f"Triplet ({h}, {r}, {t}): Distance = {distance:.4f}")
            else:
                print(f"Triplet ({h}, {r}, {t}): Missing entity or relation.")

    async def predict_tail(self, head, relation, top_k=5):
        """使用TransE预测尾实体（异步方法）"""
        try:
            if head not in self.entities or relation not in self.relations:
                return []
                
            head_vec = self.entities[head]
            relation_vec = self.relations[relation]
            
            # 计算 head + relation 向量
            target_vec = head_vec + relation_vec
            
            # 计算所有实体与目标向量的距离
            distances = []
            for entity, entity_vec in self.entities.items():
                distance = np.linalg.norm(target_vec - entity_vec, ord=2)
                distances.append((entity, distance))
                
            # 按距离排序并返回top-k个结果
            return sorted(distances, key=lambda x: x[1])[:top_k]
            
        except Exception as e:
            print(f"Error in predict_tail: {e}")
            return []
            
    def predict_tail_sync(self, head, relation, top_k=5):
        """使用TransE预测尾实体（同步方法）"""
        try:
            if head not in self.entities or relation not in self.relations:
                return []
                
            head_vec = self.entities[head]
            relation_vec = self.relations[relation]
            
            # 计算 head + relation 向量
            target_vec = head_vec + relation_vec
            
            # 计算所有实体与目标向量的距离
            distances = []
            for entity, entity_vec in self.entities.items():
                distance = np.linalg.norm(target_vec - entity_vec, ord=2)
                distances.append((entity, distance))
                
            # 按距离排序并返回top-k个结果
            return sorted(distances, key=lambda x: x[1])[:top_k]
            
        except Exception as e:
            print(f"Error in predict_tail_sync: {e}")
            return []


async def main():
    # 初始化客户端
    client = TransEClient(embedding_dim=100, margin=1.0, learning_rate=0.01)

    # 初始化嵌入向量
    await client.initialize_embeddings()

    # 训练模型
    await client.train(num_epochs=10, batch_size=1024)  # 根据需要调整 epoch 和 batch_size

    # 保存最终的嵌入向量文件
    client.save_embeddings("final_embeddings.pkl")

    # 验证嵌入向量的合理性
    sample_triplets = [
        (1, "RELATION_A", 2),  # 替换为实际的三元组
        (3, "RELATION_B", 4),  # 替换为实际的三元组
    ]
    client.validate(sample_triplets)

    # 关闭 Neo4j 连接
    await client.neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(main())