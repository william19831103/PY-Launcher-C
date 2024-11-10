import json
import os

# 默认配置
DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": True,
    },
    "serverinfo": {
        "ip": "127.0.0.1",
        "port": "3724",
        "title": "无限魔兽",
        "online_count": 0
    },
    "soap": {
        "ip": "127.0.0.1",
        "port": "7878",
        "username": "1",
        "password": "1",
    },
    "security": {
        "jwt_secret": "your-secret-key",
        "token_expire_minutes": 60,
        "max_login_attempts": 5
    }
}

CONFIG_FILE = "server_config.json"

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 合并默认配置和加载的配置
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(loaded_config)
                return merged_config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
    return DEFAULT_CONFIG

def save_config(config):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False

# 初始化配置
SERVER_CONFIG = load_config() 