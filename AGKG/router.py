from flask import Flask, render_template, send_from_directory, Blueprint

# 页面路由
main_routes = Blueprint('main_routes', __name__)

@main_routes.route('/')
def index():
    """主页，显示问答页面"""
    return render_template('crop_qa.html')

@main_routes.route('/knowledge-graph')
def knowledge_graph():
    """知识图谱可视化页面"""
    return render_template('knowledge_graph.html')

@main_routes.route('/knowledge-dashboard')
def knowledge_dashboard():
    """知识图谱统计大屏"""
    return render_template('knowledge_dashboard.html')


@main_routes.route('/static/<path:path>')
def serve_static(path):
    """提供静态文件服务"""
    return send_from_directory('static', path)

def init_app(app):
    """初始化路由"""
    app.register_blueprint(main_routes) 