from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
import json
from network_opcodes import Opcodes

app = FastAPI(title="无限魔兽服务器")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class RegisterRequest(BaseModel):
    account: str
    password: str
    security_password: str

class ChangePasswordRequest(BaseModel):
    account: str
    old_password: str
    new_password: str

class UnlockCharacterRequest(BaseModel):
    account: str
    character_name: str

# 模拟数据库
class Database:
    def __init__(self):
        self.accounts = {}
        self.characters = {}
        self.online_count = 0
        self.announcements = [
            "欢迎来到无限魔兽！",
            "新服务器将于下周开放",
            "当前版本: 3.3.5a"
        ]
        
    def add_account(self, account: str, password: str, security_pwd: str) -> bool:
        if account in self.accounts:
            return False
        self.accounts[account] = {
            "password": password,
            "security_password": security_pwd,
            "create_time": datetime.now()
        }
        return True

db = Database()

# API路由
@app.post("/api")
async def handle_request(opcode: int, data: dict = None):
    try:
        if opcode == Opcodes.REGISTER_ACCOUNT:
            account = data["account"]
            password = data["password"]
            security_pwd = data["security_password"]
            
            if db.add_account(account, password, security_pwd):
                return {"success": True, "message": "注册成功"}
            else:
                raise HTTPException(status_code=400, detail="账号已存在")

        elif opcode == Opcodes.LOGIN_ACCOUNT:
            account = data["account"]
            password = data["password"]
            
            if account in db.accounts and db.accounts[account]["password"] == password:
                return {"success": True, "message": "登录成功"}
            else:
                raise HTTPException(status_code=401, detail="账号或密码错误")

        elif opcode == Opcodes.SERVER_STATUS:
            return {
                "status": "正常运行",
                "online_count": db.online_count,
                "announcements": db.announcements
            }

        elif opcode == Opcodes.CHECK_VERSION:
            return {
                "needs_update": False,
                "current_version": "3.3.5a",
                "patch_list": []
            }

        elif opcode == Opcodes.UNLOCK_CHARACTER:
            account = data["account"]
            character_name = data["character_name"]
            
            if account in db.accounts:
                return {"success": True, "message": f"角色 {character_name} 已解锁"}
            else:
                raise HTTPException(status_code=404, detail="账号不存在")

        elif opcode == Opcodes.CHANGE_PASSWORD:
            account = data["account"]
            old_password = data["old_password"]
            new_password = data["new_password"]
            
            if account in db.accounts and db.accounts[account]["password"] == old_password:
                db.accounts[account]["password"] = new_password
                return {"success": True, "message": "密码修改成功"}
            else:
                raise HTTPException(status_code=400, detail="原密码错误")

        else:
            raise HTTPException(status_code=400, detail="未知的操作码")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True) 