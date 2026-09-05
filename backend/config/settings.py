"""BookPlay Agent 系统配置管理"""

from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    """全局配置"""
    
    # LLM API 配置（兼容 OpenAI 格式，使用 DeepSeek）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek-chat")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "2048"))
    
    # Agent 系统配置
    AGENT_RETRY_COUNT: int = int(os.getenv("AGENT_RETRY_COUNT", "3"))
    AGENT_TIMEOUT_SECONDS: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))


# 全局单例
settings = Settings()
