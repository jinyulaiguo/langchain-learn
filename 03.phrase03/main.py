import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from rag_system.indexer import DocumentIndexer
from rag_system.retriever import RetrieverWrapper
from rag_system.memory import ConversationMemory
from rag_system.router import Router
from rag_system.chains import Chains
from rag_system.formatter import ResponseFormatter

class RAGSystem:
    def __init__(self):
        print("初始化系统中，请稍候...")
        # 1. 初始化索引器并确保文档被建立索引
        self.indexer = DocumentIndexer()
        self.indexer.build_index()
        
        # 2. 初始化核心组件
        self.retriever = RetrieverWrapper()
        self.memory = ConversationMemory()
        self.router = Router(retriever=self.retriever)
        self.chains = Chains()
        
        print("系统初始化完成！")
        print("你可以直接输入问题，或使用 `/search <内容>` 强制检索，使用 `/chat <内容>` 强制记忆。输入 `exit` 或 `quit` 退出。\n")

    def run(self):
        while True:
            try:
                user_input = input("\n👤 你的问题: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    print("👋 再见！")
                    break
                
                # 1. 路由并可能执行初步检索
                decision = self.router.determine_path(user_input)
                
                # 2. 分支执行 Chain
                if decision.path == "retrieval":
                    # 获取检索结果并拼装 context
                    retrieval_result = decision.retrieval_result
                    if retrieval_result and retrieval_result.documents:
                        context = "\n\n".join([doc.content for doc in retrieval_result.documents])
                    else:
                        context = "没有检索到相关文档内容。"
                        
                    raw_response = self.chains.run_retrieval_chain(
                        question=user_input, 
                        retrieved_context=context
                    )
                else: # memory path
                    # 获取历史记录
                    chat_history = self.memory.get_history()
                    raw_response = self.chains.run_memory_chain(
                        question=user_input,
                        chat_history=chat_history
                    )
                
                # 3. 记录纯净历史（核心隔离：无论走哪条路径，只把最终问答对存入 Memory）
                self.memory.add_turn(user_input, raw_response)
                
                # 4. 格式化并输出最终结果
                final_output = ResponseFormatter.format(raw_response, decision)
                print("\n" + final_output + "\n")
                print("-" * 60)
                
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {str(e)}")

if __name__ == "__main__":
    system = RAGSystem()
    system.run()
