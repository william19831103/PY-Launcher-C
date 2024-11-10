# 服务器配置
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": True,
    
    # 数据库配置
    "database": {
        "type": "sqlite",  # 可以改为mysql或其他
        "path": "wow_server.db"
    },
    
    # 游戏版本配置
    "game": {
        "current_version": "3.3.5a",
        "min_version": "3.3.5a",
        "patch_server": "http://patches.yourserver.com"
    },
    
    # 安全配置
    "security": {
        "jwt_secret": "your-secret-key",
        "token_expire_minutes": 60,
        "max_login_attempts": 5
    }
} 