import json
import logging
from flask import Blueprint, request, jsonify
import traceback
from ..services.qa_service import QAService
from ..services.record_history_service import insert_record

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('qa_api')

qa_api = Blueprint('qa_api', __name__)
qa_service = QAService()

@qa_api.route('/qa', methods=['POST'])
def question_answering():
    """问答API入口，处理用户问题并返回答案"""
    try:
        data = request.json
        if not data or 'question' not in data:
            return jsonify({
                'status': 'error',
                'message': '请提供问题内容'
            }), 400

        question = data['question']
        # 从请求中获取用户ID，如果未提供则为None
        user_id = data.get('user_id')
        if user_id:
            logger.info(f"收到问题: {question}, 用户ID: {user_id}")
        else:
            logger.info(f"收到匿名用户问题: {question}")
        
        # 调用服务层处理问题
        result = qa_service.process_question(question, user_id)
        
        if result.get('status') == 'error':
            return jsonify(result), 400
        
        # 记录搜索历史（仅当提供了用户ID时）
        if user_id:
            try:
                logger.info(f"准备保存搜索记录，user_id: {user_id}, 类型: {type(user_id)}")
                answer = result.get('answer', '')
                rewritten_query = result.get('rewritten_query')  # 从result中获取重写后的查询
                
                # 存储搜索记录
                record_id = insert_record(
                    search_query=question,
                    answer=answer,
                    user_id=user_id,
                    is_satisfied=None,  # 用户满意度需要后续更新
                    rewritten_query=rewritten_query
                )
                
                if record_id:
                    logger.info(f"搜索记录已保存，ID: {record_id}")
                else:
                    logger.error("搜索记录保存失败，insert_record返回None")
            except Exception as e:
                logger.error(f"保存搜索记录时发生错误: {str(e)}")
                logger.error(traceback.format_exc())
                # 不影响主流程，错误只记录不抛出
        else:
            logger.warning("未提供user_id，跳过搜索记录保存")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'处理请求时发生错误: {str(e)}'
        }), 500 