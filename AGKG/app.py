from flask import Flask, render_template, send_from_directory, jsonify, request
import os
import logging
from AGKG.api.qa_api import qa_api
from AGKG.api.kg_api import kg_api  # 新增：知识图谱API
from AGKG.api.entity_api import entity_api  # 新增：实体API
from AGKG.api.relation_api import relation_api  # 新增：关系API
from AGKG.api.statistics_api import statistics_api  # 新增：统计API

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app')

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# 注册蓝图
app.register_blueprint(qa_api, url_prefix='/api/qa')  # 修改：添加qa前缀
app.register_blueprint(kg_api, url_prefix='/api/kg')  # 新增：知识图谱API
app.register_blueprint(entity_api, url_prefix='/api/entity')  # 新增：实体API
app.register_blueprint(relation_api, url_prefix='/api/relation')  # 新增：关系API
app.register_blueprint(statistics_api, url_prefix='/api/statistics')  # 新增：统计API

@app.route('/')
def index():
    """主页，显示问答页面"""
    return render_template('index.html')

@app.route('/visualization')
def visualization():
    """知识图谱可视化页面"""
    return render_template('visualization.html')

@app.route('/entity')
def entity():
    """实体查询页面"""
    return render_template('entity.html')

@app.route('/relation')
def relation():
    """关系查询页面"""
    return render_template('relation.html')

@app.route('/statistics')
def statistics():
    """数据统计页面"""
    return render_template('statistics.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """提供静态文件服务"""
    return send_from_directory('static', path)

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

@app.route('/health')
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    try:
        logger.info("应用程序启动...")
        app.run(debug=True)
    except Exception as e:
        logger.error(f"启动应用程序时发生错误: {str(e)}")
