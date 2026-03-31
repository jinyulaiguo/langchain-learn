import asyncio
import httpx
import os

API_KEY=os.getenv("DEEPSEEK_API_KEY", "sk-f5")
API_URL=os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
prompt = "你好，请介绍你自己"

async def chat_to_deepseek():
    timeout = httpx.Timeout(30.0, connect=10.0)    
    async with httpx.AsyncClient(timeout=timeout) as client:
        headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
        payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个有10年经验的Python资深架构师。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
        print(f"🚀 [网络 I/O 开始] 正在异步发送请求: '{prompt}'...")
        try:
            response = await client.post(API_URL, headers=headers, json=payload, timeout=timeout)    
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.Timeout:
            return "请求超时，请检查网络连接或 API 地址。"
        except httpx.HTTPStatusError:
            return f"请求失败: {response.status_code}"
        except httpx.RequestException as e:
            return f"请求失败: {e}"
        
async def main():
    reply = await chat_to_deepseek()
    print(reply)


if __name__ == "__main__":
    # results = asyncio.run(main())
    results = asyncio.run(main())
    print(results)