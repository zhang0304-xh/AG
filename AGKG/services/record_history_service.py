from AGKG.repository.db.record import Record
import logging
import uuid

logger = logging.getLogger(__name__)

class RecordHistoryService:
    def insert_record(self, search_query, answer, user_id, is_satisfied=None, rewritten_query=None):
        try:
            # 确保user_id是UUID类型
            if user_id is not None:
                try:
                    # 如果是字符串形式的UUID，转换为UUID对象
                    if not isinstance(user_id, uuid.UUID):
                        user_id = uuid.UUID(user_id)
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error(f"user_id无法转换为UUID: {user_id}, 类型: {type(user_id)}, 错误: {e}")
                    return None

            logger.info(f"尝试插入记录: query={search_query}, user_id={user_id}")

            # 创建并保存新记录
            new_record = Record.create(
                search_query=search_query,
                answer=answer,
                user_id=user_id,
                is_satisfied=is_satisfied,
                rewritten_query=rewritten_query
            )
            logger.info(f"记录插入成功, ID: {new_record.id}")
            return new_record.id
        except Exception as e:
            logger.error(f"插入数据时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


    def search_history(self, user_id):
        user_uuid = uuid.UUID(user_id)

        # 获取用户的搜索历史记录
        records = Record.select().where(
            Record.user_id == user_uuid,
        ).order_by(Record.created_at.desc())

        return list(records)


if __name__ == '__main__':
   test_uuid = uuid.uuid4()
   #insert_record("AAA", "BBB", test_uuid, True, "DDD")