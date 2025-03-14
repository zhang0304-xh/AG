import asyncio

from AGKG.repository.db.record import Record


async def insert_record(search_query, answer, user_id, optimized_result, is_satisfied, rewritten_query):
    try:
        # 创建并保存新记录
        new_record = Record.create(
            search_query=search_query,
            answer=answer,
            user_id=user_id,
            optimized_result=optimized_result,
            is_satisfied=is_satisfied,
            rewritten_query=rewritten_query
        )
        return new_record.id
    except Exception as e:
        print(f"插入数据时出错: {e}")
        return None


if __name__ == '__main__':
    asyncio.run(insert_record("AAA", "BBB", 1, "CCC", True, "DDD"))