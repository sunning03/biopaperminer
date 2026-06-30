"""BioPaperMiner — 共享 HTTP Session 连接池"""

import requests


def get_session(host: str) -> requests.Session:
    """按域名获取或创建 requests.Session（连接池复用）。

    Args:
        host: 域名或 URL（自动提取域名作为缓存 key）
    """
    # 用域名作为 key
    key = host.split("//")[1].split("/")[0] if "//" in host else host

    if key not in _pool:
        _pool[key] = requests.Session()
    return _pool[key]


_pool: dict = {}
