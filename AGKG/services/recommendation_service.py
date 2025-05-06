import logging
from typing import List, Dict, Any, Optional
import numpy as np
from collections import Counter
import uuid

from AGKG.repository.db.record import Record
from AGKG.core.client_manager import get_client_manager
from AGKG.services.record_history_service import RecordHistorySevice

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
            List[Dict]: 热门实体列表
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
            
            # 格式化返回结果
            return [{
                "name": entity,
                "score": count / max(entity_counter.values()),  # 归一化得分
                "frequency": count,
                "reason": "热门浏览内容"
            } for entity, count in popular_entities]

        except Exception as e:
            logger.error(f"获取热门推荐失败: {str(e)}")
            return []


    def get_recommendations_from_history(self, user_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        基于用户搜索历史推荐实体
        
        Args:
            user_id: 用户ID
            top_k: 返回的推荐实体数量
            
        Returns:
            List[Dict]: 推荐实体列表
        """
        try:
            # 将字符串user_id转换为UUID对象
            records = RecordHistorySevice().search_history(user_id)
            # 从搜索历史中提取实体
            entity_counter = Counter()
            for record in records:
                if record.rewritten_query:
                    # 假设rewritten_query是一个实体列表的字符串表示
                    try:
                        entities = eval(record.rewritten_query)
                        entity_counter.update(entities)
                    except:
                        continue
            
            # 获取出现频率最高的实体
            most_common = entity_counter.most_common(top_k)
            
            return [{"name": entity, "frequency": count, "reason": "热门浏览内容"} for entity, count in most_common]
        except Exception as e:
            logger.error(f"获取历史推荐失败: {str(e)}")
            return []


            

if __name__ == "__main__":
    print(RecommendationService()._get_user_recent_entities("11c59305ecb247d598e6fd01b496888f"))