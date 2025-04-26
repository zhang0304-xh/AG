import json
import logging
import traceback
from typing import Dict, List, Any
from ..client.zhipu_client import ZhipuClient
from ..client.neo4j_client import Neo4jClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('qa_service')

class QAService:
    def __init__(self):
        self.zhipu_client = ZhipuClient()
        self.neo4j_client = Neo4jClient()
    
    def process_question(self, question: str) -> Dict[str, Any]:
        """
        处理用户问题，返回答案
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
            
            # 3. 调用Neo4j客户端查询三元组
            kg_results = self.neo4j_client.query_kg_triplets(triplets)
            logger.info(f"知识图谱查询结果: {json.dumps(kg_results, ensure_ascii=False)}")
            
            # 4. 构建最终答案
            answer = self._construct_answer(llm_result, kg_results)
            logger.info(f"构建的答案: {answer}")
            
            return {
                'status': 'success',
                'question': question,
                'analysis': llm_result.get('analysis', {}),
                'knowledge_graph': triplets,
                'kg_results': kg_results,
                'answer': answer
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
            
            # 根据问题类型和查询意图构建答案
            if question_type == '多跳推理':
                # 处理多跳推理问题
                for result in kg_results:
                    triplet = result.get('triplet', {})
                    query_result = result.get('result', [])
                    
                    # 处理Q值替换
                    if triplet.get('tail', '').startswith('Q'):
                        q_id = triplet['tail']
                        if query_result:
                            # 存储所有查询结果
                            q_values[q_id] = [res.get('tail', '') for res in query_result]
                    
                    # 构建该步骤的答案
                    if query_result:
                        answer_part = self._format_triplet_result(triplet, query_result, q_values)
                        if answer_part:
                            answer_parts.append(answer_part)
            else:
                # 处理普通问题
                for result in kg_results:
                    triplet = result.get('triplet', {})
                    query_result = result.get('result', [])
                    
                    if query_result:
                        answer_part = self._format_triplet_result(triplet, query_result, q_values)
                        if answer_part:
                            answer_parts.append(answer_part)
            
            # 如果没有找到任何结果
            if not answer_parts:
                return "抱歉，未能找到与您问题相关的信息。"
            
            # 如果有多个结果，调用智谱AI进行处理
            if len(answer_parts) > 1 or any('、' in part for part in answer_parts):
                try:
                    # 构建提示信息
                    prompt = f"问题类型：{question_type}\n核心实体：{analysis.get('core_entity', '')}\n查询意图：{query_intent}\n查询结果：\n" + "\n".join(answer_parts)
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
    
    def _format_triplet_result(self, triplet: Dict[str, str], results: List[Dict[str, str]], q_values: Dict[str, Any] = None) -> str:
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
                tail = q_values[tail][0] if isinstance(q_values[head], list) else q_values[tail]
            
            if not results:
                return f"未找到{head}的{relation}信息。"
            
            if head and relation and tail:
                # 如果tail是Q值，我们应该返回所有查询结果
                if tail.startswith('Q'):
                    tails = [result.get('tail') for result in results if result.get('tail')]
                    if tails:
                        return f"{head}的{relation}有：" + "、".join(tails) + "。"
                else:
                    # 是非推理问题
                    if results:
                        return f"是的，{head}的{relation}是{tail}。"
                    else:
                        return f"不是，{head}的{relation}不是{tail}。"
            
            elif head and relation:
                # 实体关系查询
                tails = [result.get('tail') for result in results if result.get('tail')]
                if tails:
                    return f"{head}的{relation}有：" + "、".join(tails) + "。"
            
            elif head:
                # 实体信息查询
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