import uuid

import bcrypt
import logging
from peewee import DoesNotExist
from AGKG.repository.db.user import User

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def check_password(plain_password: str, hashed_password: str) -> bool:
    """Checks if the plain password matches the hashed password."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(username: str, password: str):
    """Registers a new user."""
    try:
        # Check if user already exists
        User.get(User.username == username, User.deleted == False)
        logger.warning(f"Registration attempt for existing username: {username}")
        return {"success": False, "message": "用户名已存在"}
    except DoesNotExist:
        # Hash the password
        hashed_pwd = hash_password(password)
        try:
            # Create the new user
            user = User.create(username=username, password=hashed_pwd, id=str(uuid.uuid4()))
            logger.info(f"User registered successfully: {username} (ID: {user.id})")
            # In a real application, you might return a user object or ID, 
            # but for simplicity, just success status.
            return {"success": True, "message": "注册成功", "user_id": user.id}
        except Exception as e:
            logger.error(f"Error creating user {username}: {e}")
            return {"success": False, "message": f"创建用户时出错: {e}"}
    except Exception as e:
        logger.error(f"Error during registration check for {username}: {e}")
        return {"success": False, "message": f"注册过程中发生错误: {e}"}

def login_user(username: str, password: str):
    """Logs in a user."""
    try:
        user = User.get(User.username == username, User.deleted == False)
        
        if user.status == 0:
            logger.warning(f"Login attempt for disabled user: {username}")
            return {"success": False, "message": "用户已被禁用"}
            
        # Check password
        if check_password(password, user.password):
            logger.info(f"User logged in successfully: {username}")
            # Here you would typically generate a token (e.g., JWT) 
            # and return it along with user info.
            # For now, just returning success and user ID.
            return {"success": True, "message": "登录成功", "user_id": user.id}
        else:
            logger.warning(f"Incorrect password attempt for user: {username}")
            return {"success": False, "message": "用户名或密码错误"}
            
    except DoesNotExist:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return {"success": False, "message": "用户名或密码错误"}
    except Exception as e:
        logger.error(f"Error during login for {username}: {e}")
        return {"success": False, "message": f"登录过程中发生错误: {e}"}
