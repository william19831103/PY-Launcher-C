import json
import os

# 配置文件路径
CONFIG_FILE = "server_config.json"

# 默认配置
DEFAULT_CONFIG = {
    "server_host": "0.0.0.0",
    "server_port": 8080,
    "server_debug": True,
    "wow_ip": "127.0.0.1",
    "wow_port": "3724",
    "server_title": "无限魔兽",
    "gameserver_online": 0,
    "online_count": 0,
    "force_wow": 1,
    "force_mpq": 1,
    "check_update_before_play": 1,
    "soap_ip": "127.0.0.1", 
    "soap_port": "7878",
    "soap_username": "1",
    "soap_password": "1",
    "jwt_secret": "your-secret-key",
    "token_expire_minutes": 60,
    "max_login_attempts": 5,
    "mysql_host": "127.0.0.1",
    "mysql_port": 3306,
    "mysql_user": "root",
    "mysql_password": "root",
    "mysql_database": "realmd"
}

def save_config(config_data):
    """保存配置到文件"""
    try:
        # 确保所有必需的配置项都存在
        final_config = DEFAULT_CONFIG.copy()
        final_config.update(config_data)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_config, f, indent=4, ensure_ascii=False)
        print(f"配置已保存: {final_config}")
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False

def load_config():
    """加载配置文件"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # 确保所有默认配置项都存在
                config = DEFAULT_CONFIG.copy()
                config.update(loaded_config)
                print(f"已加载配置: {config}")
                return config
    except Exception as e:
        print(f"加载配置失败: {e}")
    
    # 如果加载失败或文件不存在，保存并返回默认配置
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()

# 全局配置对象
CONFIG = load_config()