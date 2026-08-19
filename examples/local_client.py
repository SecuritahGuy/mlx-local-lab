from local_mlx import LocalLLM

llm = LocalLLM()
print(llm.chat("Review this Python function for potential bugs: def div(a, b): return a / b"))
