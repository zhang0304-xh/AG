import logging
from flask import Blueprint, request, jsonify
from AGKG.services.user_service import register_user, login_user
import traceback

logger = logging.getLogger(__name__)

user_api = Blueprint('user_api', __name__, url_prefix='/auth')

@user_api.route('/register', methods=['POST'])
def register():
    """API endpoint for user registration."""
    try:
        data = request.json
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"status": "error", "message": "请提供用户名和密码"}), 400

        username = data['username']
        password = data['password']
        
        # Basic validation (can be enhanced)
        if not username or not password:
             return jsonify({"status": "error", "message": "用户名和密码不能为空"}), 400
        if len(password) < 6: # Example: minimum password length
             return jsonify({"status": "error", "message": "密码长度不能少于6位"}), 400

        logger.info(f"Registration request received for username: {username}")
        result = register_user(username, password)

        if result["success"]:
            return jsonify({"status": "success", "message": result["message"], "user_id": result["user_id"]}), 201
        else:
            return jsonify({"status": "error", "message": result["message"]}), 400 # Use 409 for conflict? Maybe 400 is fine.

    except Exception as e:
        logger.error(f"Error during registration endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": f"注册过程中发生服务器错误: {str(e)}"}), 500

@user_api.route('/login', methods=['POST'])
def login():
    """API endpoint for user login."""
    try:
        data = request.json
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({"status": "error", "message": "请提供用户名和密码"}), 400

        username = data['username']
        password = data['password']

        if not username or not password:
             return jsonify({"status": "error", "message": "用户名和密码不能为空"}), 400

        logger.info(f"Login request received for username: {username}")
        result = login_user(username, password)

        if result["success"]:
            # In a real app, generate and return a JWT token here
            # session['user_id'] = result['user_id'] # Example using Flask session
            return jsonify({"status": "success", "message": result["message"], "user_id": result["user_id"]}), 200
        else:
            # Return 401 Unauthorized for login failures
            return jsonify({"status": "error", "message": result["message"]}), 401

    except Exception as e:
        logger.error(f"Error during login endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": f"登录过程中发生服务器错误: {str(e)}"}), 500
