from peewee import CharField, IntegerField, DateTimeField, BooleanField, fn, UUIDField
from .base import BaseModel, AGKG_DATABASE
import datetime

class User(BaseModel):
    username = CharField(max_length=50, unique=True, verbose_name='用户名')
    password = CharField(max_length=100, verbose_name='密码') # Store hashed password
    status = IntegerField(default=1, verbose_name='状态：0-禁用，1-正常')
    deleted = BooleanField(default=False, verbose_name='删除标志：0-未删除，1-已删除')
    id = UUIDField(verbose_name='用户ID', primary_key=True)


    class Meta:
        table_name = 'user'
        database = AGKG_DATABASE

    def save(self, *args, **kwargs):
        self.update_time = datetime.datetime.now()
        return super(User, self).save(*args, **kwargs)

# Example usage (optional, for testing)
if __name__ == '__main__':
    try:
        AGKG_DATABASE.connect()
        User.create_table()
        print("User table created successfully.")
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        if not AGKG_DATABASE.is_closed():
            AGKG_DATABASE.close()
