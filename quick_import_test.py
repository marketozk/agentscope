import sys
print("Python версия:", sys.version)

try:
    import agentscope
    print("AgentScope загружен")
except Exception as e:
    print("Ошибка AgentScope:", str(e))

try:
    from agentscope.model import GeminiChatModel
    print("GeminiChatModel доступен")
except Exception as e:
    print("Ошибка GeminiChatModel:", str(e))
    try:
        from agentscope.model import DashScopeChatModel
        print("DashScopeChatModel доступен")
    except Exception as e2:
        print("Ошибка DashScopeChatModel:", str(e2))
