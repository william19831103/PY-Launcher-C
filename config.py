import json
import os

# 配置文件路径
CONFIG_FILE = "server_config.json"

# 默认配置
DEFAULT_CONFIG = {
    "server_port": 8080,
    "wow_ip": "127.0.0.1",
    "wow_port": 3724,
    "server_title": "无限魔兽",
    "soap_ip": "127.0.0.1",
    "soap_port": 7878,
    "soap_user": "1",
    "soap_pass": "1",
    "force_wow": 0,
    "force_mpq": 0
}

def save_config(config_data):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        print(f"配置已保存: {config_data}")
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"已加载配置: {config}")
                return config
    except Exception as e:
        print(f"加载配置失败: {e}")
    
    # 如果加载失败或文件不存在，返回默认配置
    return DEFAULT_CONFIG.copy()

# 全局配置对象
CONFIG = load_config()