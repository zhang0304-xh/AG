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

    def __del__(self):
        # 在对象销毁时自动关闭 Neo4j 客户端
        if hasattr(self, 'neo4j_client') and self.neo4j_client:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
            else:
                loop.run_until_complete(self.close())

    async def close(self):
        if hasattr(self, 'neo4j_client') and self.neo4j_client:
            await self.neo4j_client.close()

    async def initialize_embeddings(self, small_dataset):
        """初始化嵌入向量（小规模数据集）"""
        print("Initializing embeddings for small dataset...")
        for h, r, t in small_dataset:
            if h not in self.entities:
                self.entities[h] = np.random.randn(self.embedding_dim).astype(np.float32)
            if t not in self.entities:
                self.entities[t] = np.random.randn(self.embedding_dim).astype(np.float32)
            if r not in self.relations:
                self.relations[r] = np.random.randn(self.embedding_dim).astype(np.float32)
        print(f"Initialized {len(self.entities)} entities and {len(self.relations)} relations.")

    async def train(self, small_dataset, num_epochs=10, batch_size=2):
        """在小规模数据集上训练"""
        print(f"Starting training for {num_epochs} epochs...")
        num_triplets = len(small_dataset)

        for epoch in range(num_epochs):
            print(f"\nEpoch {epoch + 1}/{num_epochs}")
            total_loss = 0.0
            # 使用 tqdm 显示批次进度
            with tqdm(total=num_triplets, desc=f"Epoch {epoch + 1}", unit="triplet") as pbar:
                for i in range(0, num_triplets, batch_size):
                    batch = small_dataset[i:i + batch_size]
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
                    pbar.set_postfix(loss=total_loss / (i // batch_size + 1))  # 显示当前平均损失

            print(f"Epoch {epoch + 1} completed. Average loss: {total_loss / (num_triplets // batch_size)}")

            # 保存临时检查点
            self.save_checkpoint(f"checkpoint_epoch_{epoch + 10}.pkl")
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

    def validate(self, small_dataset):
        """验证嵌入向量的合理性"""
        print("\nValidating embeddings...")
        for h, r, t in small_dataset:
            h_vec = self.entities[h]
            r_vec = self.relations[r]
            t_vec = self.entities[t]
            distance = np.linalg.norm(h_vec + r_vec - t_vec, ord=2)
            print(f"Triplet ({h}, {r}, {t}): Distance = {distance:.4f}")

    async def predict_tail(self, head, relation, top_k=5):
        """预测尾实体，并返回实体名字"""
        if head not in self.entities or relation not in self.relations:
            return []
        head_vec = self.entities[head]
        relation_vec = self.relations[relation]
        target = head_vec + relation_vec
        # 计算所有实体的距离
        distances = [(entity, np.linalg.norm(target - entity_vec, 2)) for entity, entity_vec in self.entities.items()]
        # 返回距离最小的 top_k 个实体
        top_entities = sorted(distances, key=lambda x: x[1])[:top_k]
        # 将实体 ID 转换为名字
        top_entities_with_names = []
        for entity, distance in top_entities:
            entity_name = await self.neo4j_client.get_entity_name(entity)
            if entity_name:
                top_entities_with_names.append((entity_name, distance))
        return top_entities_with_names

async def main():
    # 初始化客户端
    client = TransEClient(embedding_dim=10, margin=1.0, learning_rate=0.01)  # 使用较小的嵌入维度
    # 保存最终的嵌入向量文件
    client.load_embeddings("checkpoint_epoch_8.pkl")

    print(await client.predict_tail(1, "病害", top_k=3))
    # 验证嵌入向量的合理性
    # client.validate(small_dataset)

    # 关闭 Neo4j 连接
    # await client.neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(main())