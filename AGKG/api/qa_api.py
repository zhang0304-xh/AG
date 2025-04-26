import json
import logging
from flask import Blueprint, request, jsonify
import traceback
from ..services.qa_service import QAService

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
        logger.info(f"收到问题: {question}")
        
        # 调用服务层处理问题
        result = qa_service.process_question(question)
        
        if result.get('status') == 'error':
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'处理请求时发生错误: {str(e)}'
        }), 500 