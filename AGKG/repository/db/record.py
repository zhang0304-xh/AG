from peewee import CharField, IntegerField, TextField, BigIntegerField, BooleanField, UUIDField, DateTimeField
from .base import BaseModel, AGKG_DATABASE
import datetime


class Record(BaseModel):
    class Meta:
        table_name = 'Record'
        database = AGKG_DATABASE

    search_query = CharField(max_length=255, verbose_name='搜索内容')
    answer = TextField(verbose_name='答案')
    user_id = UUIDField(verbose_name='用户ID')
    is_satisfied = BooleanField(null=True, verbose_name='是否满意')
    rewritten_query = TextField(null=True, verbose_name='重写后的查询')
    created_at = DateTimeField(default=datetime.datetime.now, verbose_name='创建时间')
