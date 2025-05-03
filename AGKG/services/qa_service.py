import json
import logging
import traceback
from typing import Dict, List, Any
from AGKG.core.client_manager import get_client_manager

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('qa_service')


class QAService:
    def __init__(self):
        # 从客户端管理器获取客户端实例
        client_manager = get_client_manager()
        self.zhipu_client = client_manager.get_zhipu_client()
        self.neo4j_client = client_manager.get_neo4j_client()

    def process_question(self, question: str, user_id: str = None) -> Dict[str, Any]:
        """
        处理用户问题，返回答案
        
        Args:
            question: 用户问题
            user_id: 用户ID，可选
        """
        try:
            # 1. 调用智谱API获取分析结果和知识图谱三元组
            llm_result = self.zhipu_client.chat_completion(question)
            logger.info(f"智谱AI返回结果: {json.dumps(llm_result, ensure_ascii=False)}")

            # 如果没有返回有效结果
            if not llm_result or 'knowledge_graph' not in llm_result:
                return {
                    'status': 'error',
                    'message': '处理问题时出错，无法识别问题结构'
                }

            # 2. 从返回结果中获取知识图谱三元组
            triplets = llm_result.get('knowledge_graph', [])
            logger.info(f"提取的三元组: {json.dumps(triplets, ensure_ascii=False)}")

            # 3. 按依赖顺序处理三元组，动态查询知识图谱
            kg_results = []
            q_values = {}

            for triplet in triplets:
                head = triplet.get('head', '')
                relation = triplet.get('relation', '')
                tail = triplet.get('tail', '')

                # 如果head是Q值，尝试替换
                if head.startswith('Q') and head in q_values:
                    # 限制为前10个值
                    limited_values = q_values[head][:10]
                    logger.info(f"限制为前10个Q值: {limited_values}")
                    # 为Q值的每个结果生成新三元组
                    for value in limited_values:
                        new_triplet = {'head': value, 'relation': relation, 'tail': tail}
                        logger.info(f"动态生成三元组: {json.dumps(new_triplet, ensure_ascii=False)}")
                        result = self.neo4j_client.query_kg_triplets([new_triplet])
                        kg_results.extend(result)
                else:
                    # 直接查询当前三元组
                    logger.info(f"查询三元组: {json.dumps(triplet, ensure_ascii=False)}")
                    result = self.neo4j_client.query_kg_triplets([triplet])
                    kg_results.extend(result)

                # 更新q_values
                for res in result:
                    triplet_res = res.get('triplet', {})
                    query_result = res.get('result', [])
                    if triplet_res.get('tail', '').startswith('Q') and query_result:
                        q_id = triplet_res['tail']
                        q_values[q_id] = [r.get('tail', '') for r in query_result]
                        logger.info(f"更新q_values[{q_id}]: {q_values[q_id]}")

            logger.info(f"知识图谱查询结果: {json.dumps(kg_results, ensure_ascii=False)}")

            # 4. 构建最终答案
            answer = self._construct_answer(llm_result, kg_results)
            logger.info(f"构建的答案: {answer}")

            # 5. 构建重写后的查询
            rewritten_query = []
            if triplets:
                # 收集所有相关的实体和Q值
                entities = set()
                for triplet in triplets:
                    head = triplet.get('head', '')
                    tail = triplet.get('tail', '')
                    if head and not head.startswith('Q'):
                        entities.add(head)
                    if tail and not tail.startswith('Q'):
                        entities.add(tail)
                
                # 添加所有Q值对应的实际值
                for q_id, values in q_values.items():
                    entities.update(values)
                
                # 构建重写后的查询
                if entities:
                    rewritten_query = json.dumps(list(entities), ensure_ascii=False)
                    logger.info(f"重写后的查询: {rewritten_query}")

            return {
                'status': 'success',
                'question': question,
                'analysis': llm_result.get('analysis', {}),
                'knowledge_graph': triplets,
                'kg_results': kg_results,
                'answer': answer,
                'rewritten_query': rewritten_query
            }

        except Exception as e:
            logger.error(f"处理问题时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'处理问题时发生错误: {str(e)}'
            }

    def _construct_answer(self, llm_result: Dict[str, Any], kg_results: List[Dict[str, Any]]) -> str:
        """
        根据LLM分析结果和知识图谱查询结果构建最终答案
        """
        try:
            analysis = llm_result.get('analysis', {})
            question_type = analysis.get('question_type', '')
            query_intent = analysis.get('query_intent', '')

            answer_parts = []
            q_values = {}  # 存储Q值对应的实际内容

            # 处理查询结果，只保留完整三元组
            for result in kg_results:
                triplet = result.get('triplet', {})
                query_result = result.get('result', [])

                # 处理Q值替换
                if triplet.get('tail', '').startswith('Q'):
                    q_id = triplet['tail']
                    if query_result:
                        q_values[q_id] = [res.get('tail', '') for res in query_result]

                # 格式化当前三元组的结果
                answer_part = self._format_triplet_result(triplet, query_result, q_values, question_type)
                # 只保留非空且非"未找到"结果
                if answer_part and not answer_part.startswith("未找到"):
                    answer_parts.append(answer_part)

            # 如果没有找到任何结果
            if not answer_parts:
                return "抱歉，未能找到与您问题相关的信息。"

            # 如果是多跳推理、实体推理或有多个结果，调用智谱AI整合
            if question_type in ['多跳推理', '实体推理'] or len(answer_parts) > 1:
                try:
                    # 构建提示信息
                    prompt = (
                            f"查询结果：\n" + "\n".join(answer_parts) + ""
                    )
                    logger.info(f"整合答案提示: {prompt}")
                    # 调用智谱AI处理
                    processed_result = self.zhipu_client.process_multiple_results(prompt)
                    if processed_result:
                        return processed_result
                except Exception as e:
                    logger.error(f"调用智谱AI处理多个结果时发生错误: {str(e)}")
                    logger.error(traceback.format_exc())

            return "\n".join(answer_parts)
        except Exception as e:
            logger.error(f"构建答案时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return "抱歉，处理答案时发生错误。"

    def _format_triplet_result(self, triplet: Dict[str, str], results: List[Dict[str, str]],
                               q_values: Dict[str, Any] = None, question_type: str = '') -> str:
        """
        格式化单个三元组查询结果
        """
        try:
            if q_values is None:
                q_values = {}

            head = triplet.get('head', '')
            relation = triplet.get('relation', '')
            tail = triplet.get('tail', '')

            # 替换Q值
            if head.startswith('Q') and head in q_values:
                head = q_values[head][0] if isinstance(q_values[head], list) else q_values[head]
            if tail.startswith('Q') and tail in q_values:
                tail = q_values[tail][0] if isinstance(q_values[tail], list) else q_values[tail]

            if not results:
                return f"未找到{head}的{relation}信息。"

            # 是非推理问题
            if question_type == '是非推理' and head and relation and tail and not tail.startswith('Q'):
                if results:
                    return f"是的，{head}的{relation}是{tail}。"
                else:
                    return f"不是，{head}的{relation}不是{tail}。"

            # 实体关系查询（包括多跳推理和实体推理）
            if head and relation:
                tails = [result.get('tail') for result in results if result.get('tail')]
                if tails:
                    return f"{head}的{relation}有：" + "、".join(tails) + "。"

            # 实体信息查询
            if head:
                relation_results = {}
                for result in results:
                    rel = result.get('relation')
                    val = result.get('tail')
                    if rel and val:
                        if rel not in relation_results:
                            relation_results[rel] = []
                        relation_results[rel].append(val)

                if relation_results:
                    answer = f"关于{head}的信息：\n"
                    for rel, vals in relation_results.items():
                        answer += f"- {rel}：" + "、".join(vals) + "\n"
                    return answer

            return "未能解析查询结果。"
        except Exception as e:
            logger.error(f"格式化三元组结果时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return None