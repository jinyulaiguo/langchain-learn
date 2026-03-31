import os
from dotenv import load_dotenv
from router_qa.system import RouterQASystem

def main():
    print("="*60)
    print("欢迎使用 LangChain 多模板问答路由器系统 (纯 Chain 显式调用)")
    print("="*60)

    # 读取 .env 环境设置
    load_dotenv()
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("警告: 尚未检测到 OPENAI_API_KEY，如果您在 .env 中未设置，程序可能会在调用阶段抛错。")
        print("请在 .env 中配置 `OPENAI_API_KEY` 及 `OPENAI_BASE_URL` (如需使用 DeepSeek 等兼容服务)。\n")
        
    # 获取环境变量
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    # 如果在使用 DeepSeek
    model_name = os.environ.get("OPENAI_MODEL_NAME", "gpt-3.5-turbo")

    try:
        # 当作基础的 ChatGPT，但支持代理地址、不同模型名
        system = RouterQASystem(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url if base_url else None
        )
    except Exception as e:
        print(f"系统初始化失败，请检查依赖或配置，报错截图: {e}")
        return

    test_queries = [
        "请结合你的理解，帮我翻译这段英文字符文本：The future belongs to those who learn more skills and combine them in creative ways.",
        "帮我看看这段代码有什么作用: \ndef bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n-i-1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]",
        "今天的天气真不错，我和朋友去公园玩了一下午，感觉很放松。然后我们去吃了好吃的火锅，晚上还看了一部温馨的电影。帮我提炼一下摘要吧！"
    ]

    print("【开始内建测例演示】\n")
    for idx, query in enumerate(test_queries, 1):
        print(f"------------\n[{idx}] 模拟用户请求: {query}")
        try:
            result = system.run(query)
            print("🚀 Pydantic 解析结果:")
            print(result.model_dump_json(indent=2))
        except Exception as e:
            print(f"执行失败: {e}")

    print("\n" + "="*60)
    print("您可以尝试手工输入请求 (输入 'exit' 或 'quit' 退出):")
    while True:
        try:
            user_input = input("\n👤 你的输入: ")
            if user_input.lower() in ('exit', 'quit'):
                break
            if not user_input.strip():
                continue
            
            result = system.run(user_input)
            print("🤖 解析结果:\n", result.model_dump_json(indent=2))
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()
