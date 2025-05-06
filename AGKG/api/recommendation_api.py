import logging
from flask import Blueprint, request, jsonify
import traceback
import uuid

from AGKG.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)
recommendation_service = RecommendationService()

recommendation_api = Blueprint('recommendation_api', __name__, url_prefix='/api/recommendations')

@recommendation_api.route('/user/<user_id>', methods=['GET'])
def get_user_recommendations(user_id):
    """获取用户的推荐内容"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        source = request.args.get('source', default='all')
        
        # 验证user_id格式
        try:
            uuid_obj = uuid.UUID(user_id)
        except ValueError:
            return jsonify({
                "status": "error", 
                "message": "无效的用户ID格式"
            }), 400
            
        logger.info(f"获取用户 {user_id} 的推荐内容，来源 {source}，限制 {limit} 项")
        
        if source == 'transe':
            # 获取最近查看的实体作为种子
            recent_entities = recommendation_service._get_user_recent_entities(user_id, limit=1)
            if not recent_entities:
                recommendations = []
            else:
                recommendations = recommendation_service.get_similar_entities_by_transe(recent_entities[0], top_k=limit)
                # TransE推荐的结果已经包含了source和source_text，不需要额外添加
        elif source == 'kg':
            # 获取基于知识图谱的推荐
            recommendations = recommendation_service.get_recommendations_from_history(user_id, top_k=limit)
            for rec in recommendations:
                rec["source"] = "KG"
                rec["source_text"] = "基于您的浏览历史推荐"
        elif source == 'popular':
            # 获取热门推荐
            recommendations = recommendation_service.get_popular_recommendations(limit)
            for rec in recommendations:
                rec["source"] = "Popular"
                rec["source_text"] = "热门浏览内容"
        else:
            # 获取混合推荐
            recommendations = recommendation_service.get_user_recommendations(user_id, limit)
        
        return jsonify({
            "status": "success",
            "data": {
                "recommendations": recommendations,
                "count": len(recommendations)
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户推荐时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"获取推荐时发生错误: {str(e)}"
        }), 500

@recommendation_api.route('/popular', methods=['GET'])
def get_popular_recommendations():
    """获取热门推荐内容"""
    try:
        limit = request.args.get('limit', default=10, type=int)
            
        logger.info(f"获取热门推荐内容，限制 {limit} 项")
        recommendations = recommendation_service.get_popular_recommendations(limit)
        
        return jsonify({
            "status": "success",
            "data": {
                "recommendations": recommendations,
                "count": len(recommendations)
            }
        })
        
    except Exception as e:
        logger.error(f"获取热门推荐时出错: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": f"获取推荐时发生错误: {str(e)}"
        }), 500