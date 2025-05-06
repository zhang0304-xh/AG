import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from collections import Counter
import uuid

from AGKG.repository.db.record import Record
from AGKG.core.client_manager import get_client_manager
from AGKG.services.record_history_service import RecordHistoryService

logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self):
        """初始化推荐服务"""
        client_manager = get_client_manager()
        self.neo4j_client = client_manager.get_neo4j_client()

    def get_popular_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取热门推荐内容
        
        Args:
            limit: 返回的推荐数量
            
        Returns:
            List[Dict]: 热门实体列表，每个实体包含name, score, frequency, reason字段
        """
        try:
            # 从所有搜索记录中统计最受欢迎的实体
            records = Record.select(
                Record.rewritten_query
            ).order_by(
                Record.created_at.desc()
            ).limit(1000)  # 限制查询范围
            
            entity_counter = Counter()
            for record in records:
                if record.rewritten_query:
                        entities = eval(record.rewritten_query)
                        entity_counter.update(entities)

            # 获取最热门的实体
            popular_entities = entity_counter.most_common(limit)
            max_count = max(entity_counter.values()) if entity_counter else 1
            
            # 格式化返回结果
            return [{
                "name": entity,
                "score": count / max_count,  # 归一化得分
                "frequency": count,
                "reason": "热门浏览内容"
            } for entity, count in popular_entities]

        except Exception as e:
            logger.error(f"获取热门推荐失败: {str(e)}")
            return []

    def get_recommendations_from_neo4j(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        结合Neo4j图数据和用户历史记录的混合推荐方法

        Args:
            user_id: 用户ID
            limit: 返回的推荐数量

        Returns:
            List[Dict]: 推荐实体列表，包含实体名称、得分和推荐原因
        """
        try:
            # 1. 获取用户历史记录中的实体
            records = RecordHistoryService().search_history(user_id)
            history_entity_names = []

            for record in records:
                if record.rewritten_query:
                    try:
                        entities = json.loads(record.rewritten_query)
                        history_entity_names.extend(entities)
                    except:
                        continue

            if not history_entity_names:
                return []

            # 2. 使用Neo4j查询与历史实体相关的实体
            related_entities = []
            for entity in set(history_entity_names):  # 去重
                result = self.neo4j_client.get_entity_and_neighbors(entity_name=entity, limit=limit)
                if result and len(result) > 0:
                    nodes = result[0]  # 第一个元素是节点列表
                    for node in nodes:
                        if node['name'] != entity:  # 排除查询实体本身
                            related_entities.append(node['name'])

            # 3. 统计相关实体出现频率并排序
            entity_counter = Counter(related_entities)
            most_common = entity_counter.most_common(limit)
            max_count = max(entity_counter.values()) if entity_counter else 1

            return [{
                "name": entity,
                "score": count / max_count,  # 归一化得分
                "frequency": count,
                "reason": f"与您查询的'{history_entity_names[0]}'等相关"  # 简单示例，实际可更详细
            } for entity, count in most_common]

        except Exception as e:
            logger.error(f"获取Neo4j推荐失败: {str(e)}")
            return []

    def get_user_recommendations(self, user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        获取用户的综合推荐内容，包括基于知识图谱的推荐和热门推荐
        
        Args:
            user_id: 用户ID
            limit: 返回的推荐数量
            
        Returns:
            List[Dict]: 推荐内容列表
        """
        try:
            # 获取基于知识图谱的推荐
            kg_recommendations = self.get_recommendations_from_neo4j(user_id, limit=int(limit/2))
            for rec in kg_recommendations:
                rec["source"] = "KG"
                rec["source_text"] = rec.get("reason", "基于您的浏览历史推荐")
            
            # 如果知识图谱推荐不足，补充热门推荐

            popular_recommendations = self.get_popular_recommendations(limit=int(limit/2))
            for rec in popular_recommendations:
                rec["source"] = "Popular"
                rec["source_text"] = "热门浏览内容"

            # 合并推荐结果
            recommendations = kg_recommendations + popular_recommendations

            return recommendations
            
        except Exception as e:
            logger.error(f"获取用户推荐失败: {str(e)}")
            return []

if __name__ == "__main__":
    print(RecommendationService().get_recommendations_from_neo4j("11c59305ecb247d598e6fd01b496888f"))