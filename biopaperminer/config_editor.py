"""BioPaperMiner — 配置编辑工具（供 TUI / GUI 共享）

提供 user_config.json 的读写能力，UI 修改配置后调用 save() 持久化。
"""

import os
import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "user_config.json"

# 可编辑的配置项定义：
#   (键名, 显示标签, 类型, 默认值, 显示条件, *选择项)
#   显示条件: "*" = 总是显示, "agnes"/"deepseek"/"ollama"/"openai_compatible" = 仅该提供商时显示
EDITABLE_FIELDS = [
    ("LLM_PROVIDER",        "LLM 提供商",         "select", "agnes",   "*",
     ["agnes", "deepseek", "ollama", "openai_compatible"]),
    ("AGNES_API_KEY",       "Agnes API Key",       "secret", "",        "agnes"),
    ("DEEPSEEK_API_KEY",    "DeepSeek API Key",    "secret", "",        "deepseek"),
    ("OPENAI_COMPAT_API_KEY", "OpenAI 兼容 Key",   "secret", "",        "openai_compatible"),
    ("OLLAMA_BASE_URL",     "Ollama 地址",         "text",   "http://localhost:11434", "ollama"),
    ("OLLAMA_MODEL",        "Ollama 模型名",       "text",   "gemma4:26b", "ollama"),
    ("MINERU_API_TOKEN",    "MinerU API Token",     "secret", "",       "*"),
    ("LLM_MAX_TOKENS",      "最大输出 Tokens",      "number", "8192",   "*"),
    ("MAX_TEXT_LENGTH",     "最大文本长度(字符)",    "number", "300000", "*"),
    ("MAX_WORKERS",         "并发处理数",           "number", "2",      "*"),
    ("FONT_SCALE",          "字体大小",            "select", "1.0",    "*",
     ["0.8", "0.9", "1.0", "1.1", "1.2", "1.3", "1.5", "2.0"]),
]


def load() -> dict:
    """从 user_config.json 读取当前用户配置（不存在则返回空字典）"""
    if _CONFIG_PATH.exists():
        try:
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def get(key: str, default: str = "") -> str:
    """按 key 获取用户配置值（优先 user_config.json，其次 os.environ）"""
    cfg = load()
    if key in cfg and cfg[key]:
        return cfg[key]
    return os.environ.get(key, default)


def save(entries: dict) -> None:
    """保存配置到 user_config.json，同时写入 os.environ 立即生效

    Args:
        entries: { "AGNES_API_KEY": "sk-xxx", "LLM_PROVIDER": "agnes", ... }
    """
    # 合并现有配置（避免覆盖未修改的字段）
    existing = load()
    existing.update(entries)

    # 只保存非空值（用户主动清空的字段保留空串标记）
    _CONFIG_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 立即写入 os.environ，当前进程后续 import config 可读到
    for key, value in entries.items():
        if isinstance(value, str):
            os.environ[key] = value

    print(f"  ✅ 配置已保存到 {_CONFIG_PATH}")
