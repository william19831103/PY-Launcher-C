from enum import IntEnum

class Opcodes(IntEnum):
    # 账号相关操作码 (1000-1999)
    REGISTER_ACCOUNT = 1001        # 注册账号
    LOGIN_ACCOUNT = 1002          # 登录账号
    CHANGE_PASSWORD = 1003        # 修改密码
    RESET_PASSWORD = 1004         # 重置密码
    
    # 角色相关操作码 (2000-2999)
    UNLOCK_CHARACTER = 2001       # 角色解卡
    CHARACTER_LIST = 2002         # 获取角色列表
    
    # 补丁相关操作码 (3000-3999)
    CHECK_VERSION = 3001          # 检查版本
    PATCH_LIST = 3002            # 获取补丁列表
    DOWNLOAD_PATCH = 3003        # 下载补丁
    
    # 服务器状态操作码 (4000-4999)
    SERVER_STATUS = 4001         # 服务器状态
    ONLINE_COUNT = 4002          # 在线人数
    SERVER_ANNOUNCEMENT = 4003   # 服务器公告 