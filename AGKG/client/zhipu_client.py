import asyncio
import json
import re

import requests
from zhipuai import ZhipuAI
import setting

system_content = """
# 任务
    农业相关问题的命名实体识别以及意图识别，并构建出包含问题的三元组，在后续知识图谱中进行检索。

# 输入
    用户输入的问题

# 步骤
    1. 分析用户提出的问题的类型
    2. 提取用户咨询的实体
    3. 提取用户咨询的意图
    4. 将问题提取为三元组用户咨询的问题用Qn表示(n为问题的序号)
    5. 多用户提出多个问题且后一个问题需要用到前一个问题的答案，将Qn-1作为实体输入

# 要求
    1. 只能用户输入的问题提取，不要对问题进行扩充
    2. 不要进行任何假设、猜想或推断，提取用户的表层问题即可

# 问题类型枚举值
    1. 多跳推理：后一问题需要用到前一个问题的答案
    2. 关系推理：获取实体之间的关系
    3. 实体推理：通过实体和关系获取另一实体
    4. 是非推理：找到了两个实体，判断它们之间的关系是否正确

# 意图枚举值
    作者、关键字、别称、包含、危害作物、发生规律、学名、形态特征、摘要、期刊、父类、生活习性、病害、症状、研究文献、简介、网址、虫害、防治方法

# 输出格式要求
    可以json.loads()的格式，确保输出的是三元组，不要输出额外内容

# 输出示例
{
    ”question": "用户问题"
    "result": [{"多跳推理" : [("实体", "意图", "Q1"), ("Q1", "意图", "Q2")]}, {"关系推理" : [("实体", "Q3", "实体")]}}], 
    "thinking_process": "思考过程"
}
"""


class ZhipuClient:
    def __init__(self):
        self.client = ZhipuAI(api_key=setting.Config.ZHIPUAI_API_KEY)
        self.model = "glm-4v-flash"

    async def chat_completion(self, user_content, top_p=0.1, temperature=0.1, max_tokens=1024, stream=False):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            top_p=top_p,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        text = response.choices[0].message.content
        print(text)
        pattern = r'\{\s*"question":\s*"(.*?)",\s*"result":\s*\[(.*?)\],\s*"thinking_process":\s*"(.*?)"\s*\}'
        match = re.search(pattern, text, re.DOTALL)

        if match:
            # 提取匹配的内容
            question = match.group(1)
            result = match.group(2)
            thinking_process = match.group(3)

            # 提取 result 中的内容
            result_pattern = r'\{"(.*?)":\s*\[(.*?)\]\}'
            result_matches = re.findall(result_pattern, result)

            # 构建 result 字典
            result_dict = {}
            for key, value in result_matches:
                # 提取三元组
                triples = re.findall(r'\("(.*?)", "(.*?)", "(.*?)"\)', value)
                result_dict[key] = [list(triple) for triple in triples]

            # 构建最终的 JSON 对象
            result_json = {
                "question": question,
                "result": result_dict,
                "thinking_process": thinking_process
            }

            return result_json

        return []



if __name__ == "__main__":
   # client = ZhipuClient()
   # response = asyncio.run(client.chat_completion("小麦有什么病"))
   # print(response)

   url = "https://api.siliconflow.cn/v1/chat/completions"

   payload = {
       "model": "Qwen/QwQ-32B",
       "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": "小麦有什么病"}
            ],
       "stream": False,
       "max_tokens": 512,
       "stop": None,
       "temperature": 0.7,
       "top_p": 0.7,
       "top_k": 50,
       "frequency_penalty": 0.5,
       "n": 1,
       "response_format": {"type": "text"},
   }
   headers = {
       "Authorization": "Bearer sk-civvagzcjzaqvaycxkximwxgbnepnukayfnxjlvuyljcumlu",
       "Content-Type": "application/json"
   }

   response = requests.request("POST", url, json=payload, headers=headers)

   print(response.text)



