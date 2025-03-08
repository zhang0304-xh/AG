from zhipuai import ZhipuAI
import setting

class ZhipuClient:
    def __init__(self):
        self.client = ZhipuAI(api_key=setting.Config.ZHIPUAI_API_KEY)
        self.model = "glm-4v-flash"

    def chat_completion(self, messages, top_p=0.7, temperature=0.95, max_tokens=1024, stream=False):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            top_p=top_p,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )
        return response


# 使用示例
if __name__ == "__main__":
    client = ZhipuClient()
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "提取用户的意图"
                },
                {
                    "type": "text",
                    "text": "苹果有什么病"
                }
            ]
        }
    ]
    response = client.chat_completion(messages)
    print(response.choices[0].message.content)

