import json
import re
import logging
import traceback

import requests
from zhipuai import ZhipuAI
import settings

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('zhipu_client')

qa_system_content = """
# 任务目标
    对农业领域用户提问进行结构化解析，实现：
    1. 双重分类：问题类型识别 + 咨询意图识别
    2. 实体抽取：精准提取农业领域实体
    3. 知识三元组构建：为知识图谱检索提供结构化输入

# 输入规范
    用户原始提问文本（需保持原貌不作任何改写）

# 处理流程
    1. 问题分类 -> 从【问题类型枚举】选择最匹配的类型
    2. 实体提取 -> 识别问题中的具体农业实体
    3. 意图识别 -> 从【意图标签枚举】选择最匹配的意图
    4. 构建三元组 -> 按规则生成知识检索结构，不要有缺失

# 约束条件
    1. 禁止任何形式的提问改写或补充
    2. 禁止实体联想或假设推理
    3. 当问题存在逻辑依赖时（需前序答案），使用Qn标记建立关联

# 枚举定义
## 问题类型
    {
        "多跳推理": "后续问题依赖前序问题答案",
        "关系推理": "探索实体间关系",
        "实体推理": "通过头实体和关系反推尾实体", 
        "是非推理": "验证实体关系正确性"
    }

## 意图标签枚举
    [
        "作者", "关键字", "别称", "包含",
        "危害作物", "发生规律", "学名",
        "形态特征", "摘要", "期刊", "父类",
        "生活习性", "病害", "症状", "研究文献",
        "简介", "网址", "虫害", "防治方法"
    ]

# 输出规范
    {
        "question": "原始用户问题",
        "analysis": {
            "question_type": "问题类型",
            "core_entities": ["实体1", "实体2"],
            "query_intent": "意图标签"
        },
        "knowledge_graph": [
            {
                "head": "实体/Qn",
                "relation": "意图标签",
                "tail": "实体/Qn"
            }
        ],
        "dependency_chain": ["Qn"]  // 存在依赖关系时显示调用链
    }

# 示例输出
    {
        "question": "稻瘟病的症状表现有哪些？它的防治方法是谁提出的？",
        "analysis": {
            "question_type": "多跳推理",
            "core_entities": ["稻瘟病"],
            "query_intent": "症状"
        },
        "knowledge_graph": [
            {"head": "稻瘟病", "relation": "症状", "tail": "Q1"},
            {"head": "Q1", "relation": "作者", "tail": "Q2"}
        ],
        "dependency_chain": ["Q1", "Q2"]
    }
"""

format_prompt = """
    # 任务
        根据提供的信息，生成一个完整、专业且易于理解的答案。
    # 要求
        1. 回答的内容不要脱离给出的信息
        2. 输出内容通过换行区分，不需要#
        3. 内容做一个大致的概况即可
"""

# 创建ZhipuClient客户端的单例实例
_zhipu_client_instance = None

class ZhipuClient:
    def __new__(cls):
        global _zhipu_client_instance
        if _zhipu_client_instance is None:
            _zhipu_client_instance = super(ZhipuClient, cls).__new__(cls)
            _zhipu_client_instance._initialized = False
        return _zhipu_client_instance
    
    def __init__(self):
        if self._initialized:
            return
            
        try:
            self.client = ZhipuAI(api_key=settings.Config.ZHIPUAI_API_KEY)
            self.model = "glm-4v-flash"
            logger.info("ZhipuClient初始化成功")
            self._initialized = True
        except Exception as e:
            logger.error(f"ZhipuClient初始化失败: {str(e)}")
            raise

    def chat_completion(self, user_content, top_p=0.01, temperature=0.01, max_tokens=1024, stream=False):
        """
        调用智谱AI进行对话，解析用户问题
        """
        logger.info(f"发送请求到智谱AI，问题: {user_content[:50]}...")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": qa_system_content},
                    {"role": "user", "content": user_content}
                ],
                top_p=top_p,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream
            )

            text = response.choices[0].message.content
            logger.info(f"收到智谱AI响应: {text[:100]}...")

            pattern = r'\{.*\}'
            match = re.search(pattern, text, re.DOTALL)

            if match:
                json_str = match.group(0)
                # 将字符串解析为 JSON 对象
                json_data = json.loads(json_str)
                return json_data
            
            return None
        except Exception as e:
            logger.error(f"调用智谱AI时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def process_multiple_results(self, prompt: str) -> str:
        """
        处理多个查询结果，生成一个综合的答案
        
        Args:
            prompt: 包含问题类型、核心实体、查询意图和查询结果的提示信息
            
        Returns:
            str: 处理后的综合答案
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": format_prompt},
                    {"role": "user", "content": prompt}
                ],
                top_p=0.01,
                temperature=0.01,
                max_tokens=1024
            )
            
            answer = response.choices[0].message.content
            return answer.strip()
            
        except Exception as e:
            logger.error(f"处理多个结果时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return None

if __name__ == "__main__":
    client = ZhipuClient()
    response = client.chat_completion("小麦有什么病？")
    print(response)



