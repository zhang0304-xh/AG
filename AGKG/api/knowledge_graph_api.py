from flask import Blueprint, jsonify, request
from AGKG.services.knowledge_graph_service import KnowledgeGraphService
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建蓝图
knowledge_graph_api = Blueprint('knowledge_graph_api', __name__)
graph_service = KnowledgeGraphService()

@knowledge_graph_api.route('/api/knowledge_graph/search_node_by_name', methods=['GET'])
def search_node_by_name():
    """
    获取知识图谱可视化数据
    
    Query Parameters:
        entity_name: 可选，如果提供，则返回该实体及相关节点
        limit: 可选，限制返回的节点数量，默认为10
    
    Returns:
        JSON对象，包含节点和连接数据
    """
    try:
        # 从查询参数获取实体名称和限制数量
        entity_name = request.args.get('entity_name')
        limit = int(request.args.get('limit', 10))
        
        # 使用服务获取图谱数据
        graph_data = graph_service.search_node_by_name(entity_name, limit)
        
        # 检查是否有错误信息
        if 'error' in graph_data:
            logger.warning(f"获取知识图谱数据有错误: {graph_data['error']}")
            # 移除错误消息并返回其他数据
            error_message = graph_data.pop('error')
            return jsonify({'error': error_message, **graph_data})
            
        return jsonify(graph_data)
    except Exception as e:
        logger.error(f"获取知识图谱数据失败: {str(e)}")
        return jsonify({'error': str(e), 'nodes': [], 'links': []}), 500

@knowledge_graph_api.route('/api/knowledge_graph/search', methods=['GET'])
def search_entity():
    """
    搜索实体
    
    Query Parameters:
        q: 搜索关键词
        
    Returns:
        JSON对象，包含匹配的节点和连接
    """
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify({'error': '搜索关键词不能为空', 'nodes': [], 'links': []}), 400
            
        # 使用服务搜索实体
        results = graph_service.search_entity(query)
        
        # 检查是否有错误信息
        if 'error' in results:
            logger.warning(f"搜索实体有错误: {results['error']}")
            # 移除错误消息并返回其他数据
            error_message = results.pop('error')
            return jsonify({'error': error_message, **results})
            
        return jsonify(results)
    except Exception as e:
        logger.error(f"搜索实体失败: {str(e)}")
        return jsonify({'error': str(e), 'nodes': [], 'links': []}), 500

@knowledge_graph_api.route('/api/knowledge_graph/node/<node_id>/expand', methods=['GET'])
def expand_node(node_id):
    """
    展开节点，获取相关实体
    
    Path Parameters:
        node_id: 要展开的节点ID
    
    Query Parameters:
        limit: 可选，限制返回的节点数量，默认为10
        
    Returns:
        JSON对象，包含相关的节点和连接
    """
    try:
        # 使用服务展开节点
        results = graph_service.expand_node(node_id)
        
        # 检查是否有错误信息
        if 'error' in results:
            logger.warning(f"展开节点有错误: {results['error']}")
            # 移除错误消息并返回其他数据
            error_message = results.pop('error')
            return jsonify({'error': error_message, **results})
            
        return jsonify(results)
    except Exception as e:
        logger.error(f"展开节点失败: {str(e)}")
        return jsonify({'error': str(e), 'nodes': [], 'links': []}), 500

@knowledge_graph_api.route('/api/knowledge_graph/statistics', methods=['GET'])
def get_statistics():
    """
    获取知识图谱统计信息
    
    Returns:
        JSON对象，包含实体数量、关系数量等统计信息
    """
    try:
        # 使用服务获取统计信息
        statistics = graph_service.get_statistics()
        
        # 检查是否有错误信息
        if 'error' in statistics:
            logger.warning(f"获取统计信息有错误: {statistics['error']}")
            # 移除错误消息并返回其他数据
            error_message = statistics.pop('error')
            # 如果数据库连接失败，返回空数据
            if "数据库连接失败" in error_message:
                logger.info("数据库连接失败")
                return jsonify({'error': error_message, 'total_nodes': 0, 'total_relations': 0, 'entities': [], 'relations': []})
            return jsonify({'error': error_message, **statistics})
            
        return jsonify(statistics)
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        # 返回空数据
        return jsonify({'error': str(e), 'total_nodes': 0, 'total_relations': 0, 'entities': [], 'relations': []})

def init_app(app):
    """注册API蓝图到应用"""
    app.register_blueprint(knowledge_graph_api) 