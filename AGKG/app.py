from flask import Flask, jsonify, request
import os
import logging
from AGKG.api.qa_api import qa_api
from AGKG.api.knowledge_graph_api import knowledge_graph_api
from AGKG.router import init_app as init_router

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app')

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# 注册蓝图
app.register_blueprint(qa_api, url_prefix='/api')
app.register_blueprint(knowledge_graph_api)

# 初始化路由
init_router(app)

@app.errorhandler(404)
def page_not_found(e):
    """处理404错误"""
    logger.warning(f"404错误: {request.path}")
    return jsonify({"status": "error", "message": "请求的资源不存在"}), 404

@app.errorhandler(500)
def internal_server_error(e):
    """处理500错误"""
    logger.error(f"500错误: {str(e)}")
    return jsonify({"status": "error", "message": "服务器内部错误，请稍后再试"}), 500


if __name__ == '__main__':
    try:
        logger.info("应用程序启动...")
        app.run(debug=True)
    except Exception as e:
        logger.error(f"启动应用程序时发生错误: {str(e)}")
