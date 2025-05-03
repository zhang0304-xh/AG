from flask import Flask, jsonify, request
import os
import logging
from AGKG.api.qa_api import qa_api
from AGKG.api.knowledge_graph_api import knowledge_graph_api
from AGKG.api.user_api import user_api
from AGKG.api.recommendation_api import recommendation_api
from AGKG.router import main_routes

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app')

def create_app():
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # API
    app.register_blueprint(qa_api)
    app.register_blueprint(knowledge_graph_api)
    app.register_blueprint(user_api)
    app.register_blueprint(recommendation_api)

    # 前端WEB
    app.register_blueprint(main_routes)

    @app.errorhandler(404)
    def page_not_found(e):
        logger.warning(f"404错误: {request.path}")
        return jsonify({"status": "error", "message": "请求的资源不存在"}), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"500错误: {str(e)}")
        return jsonify({"status": "error", "message": "服务器内部错误，请稍后再试"}), 500

    return app

app = create_app()

if __name__ == '__main__':
    try:
        logger.info("应用程序启动...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        logger.error(f"启动应用程序时发生错误: {str(e)}")