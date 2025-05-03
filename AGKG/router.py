from flask import Blueprint, render_template

# 页面路由
main_routes = Blueprint('main_routes', __name__)

@main_routes.route('/')
def index():
    # Renders the main page (e.g., index.html)
    # We might need to create index.html later or modify this
    return render_template('crop_qa.html') # Assuming you have or will have an index.html

@main_routes.route('/login')
def login_page():
    """Serves the login page."""
    return render_template('login.html')

@main_routes.route('/register')
def register_page():
    """Serves the registration page."""
    return render_template('register.html')

@main_routes.route('/crop_qa')
def crop_qa():
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

@main_routes.route('/recommendations')
def recommendations():
    """推荐页面，基于用户搜索历史的推荐"""
    return render_template('recommendations.html') 