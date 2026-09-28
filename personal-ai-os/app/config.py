import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    GEMINI_MODEL = "gemini-3.5-flash-lite"
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def require_gemini_key() -> str:
    if not Config.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return Config.GEMINI_API_KEY


def require_github_token() -> str:
    if not Config.GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Add a GitHub Personal Access Token "
            "(repo/read scope) to .env as GITHUB_TOKEN=... to use the MCP "
            "GitHub connection."
        )
    return Config.GITHUB_TOKEN
