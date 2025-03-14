import time
from peewee import MySQLDatabase, Model, BigIntegerField


AGKG_DATABASE = MySQLDatabase(
    'agkg',  # 数据库名称
    user='root',  # 用户名
    password='123456',  # 密码
    host='localhost',  # 主机地址
    port=3306,  # 端口
    charset='utf8mb4'  # 字符集
)

class BaseModel(Model):
    id = BigIntegerField(primary_key=True)
    created_at = BigIntegerField(
        default=int(time.time()*1000),
        db_column='created_at'
    )
    updated_at = BigIntegerField(
        default=int(time.time()*1000),
        db_column='updated_at'
    )