from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import uvicorn
import threading
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from config import SERVER_CONFIG, save_config, load_config
from network_opcodes import Opcodes
import os
import base64
import http.client
import xml.etree.ElementTree as ET




# 将FastAPI应用命名为api_app而不是app
api_app = FastAPI(title="无限魔兽服务器")

# 允许跨域请求
api_app.add_middleware(
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

# 添加服务器信息数据模型
class ServerInfo(BaseModel):
    wow_ip: str
    wow_port: str
    login_title: str
    announcements: List[str]

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
@api_app.post("/api")
async def handle_request(request: Request):
    """处理客户端请求"""
    try:
        # 获取请求数据
        request_data = await request.json()
        print(f"收到请求数据: {request_data}")  # 调试信息
        
        opcode = request_data.get("opcode")
        data = request_data.get("data", {})
        
        print(f"操作码: {opcode}")  # 调试信息
        print(f"数据: {data}")  # 调试信息
        
        if not isinstance(opcode, int):
            return JSONResponse(
                status_code=400,
                content={"detail": "无效的操作码"}
            )
            
        if opcode == Opcodes.SERVER_STATUS:
            # 从G.txt重新读取公告
            try:
                with open('G.txt', 'r', encoding='utf-8') as f:
                    announcements = [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                announcements = ["暂无公告"]
                
            return JSONResponse(content={
                "status": "正常运行" if SERVER_CONFIG["serverinfo"]["gameserver_online"] else "离线",
                "online_count": SERVER_CONFIG["serverinfo"]["online_count"],
                "announcements": announcements  # 直接返回从文件读取的公告
            })
            
        elif opcode == Opcodes.REGISTER_ACCOUNT:
            account = data["account"]
            password = data["password"]
            security_pwd = data["security_password"]
            
            if db.add_account(account, password, security_pwd):
                return JSONResponse(content={"success": True, "message": "注册成功"})
            else:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "账号已存在"}
                )

        elif opcode == Opcodes.LOGIN_ACCOUNT:
            account = data["account"]
            password = data["password"]
            
            if account in db.accounts and db.accounts[account]["password"] == password:
                return JSONResponse(content={"success": True, "message": "登录成功"})
            else:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "账号或密码错误"}
                )

        elif opcode == Opcodes.CHECK_VERSION:
            return JSONResponse(content={
                "needs_update": False,
                "current_version": "3.3.5a",
                "patch_list": []
            })

        elif opcode == Opcodes.UNLOCK_CHARACTER:
            account = data["account"]
            character_name = data["character_name"]
            
            if account in db.accounts:
                return JSONResponse(content={
                    "success": True,
                    "message": f"角色 {character_name} 已解锁"
                })
            else:
                return JSONResponse(
                    status_code=404,
                    content={"detail": "账号不存在"}
                )

        elif opcode == Opcodes.CHANGE_PASSWORD:
            account = data["account"]
            old_password = data["old_password"]
            new_password = data["new_password"]
            
            if account in db.accounts and db.accounts[account]["password"] == old_password:
                db.accounts[account]["password"] = new_password
                return JSONResponse(content={
                    "success": True,
                    "message": "密码修改成功"
                })
            else:
                return JSONResponse(
                    status_code=400,
                    content={"detail": "原密码错误"}
                )

        else:
            return JSONResponse(
                status_code=400,
                content={"detail": "未知的操作码"}
            )

    except Exception as e:
        print(f"处理请求异常: {str(e)}")  # 调试信息
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )

@api_app.get("/server_info")
async def get_server_info():
    """获取服务器信息"""
    try:
        # 从G.txt读取公告
        try:
            with open('G.txt', 'r', encoding='utf-8') as f:
                announcements = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            announcements = ["暂无公告"]
            
        server_info = {
            "wow_ip": SERVER_CONFIG["serverinfo"]["ip"],
            "wow_port": SERVER_CONFIG["serverinfo"]["port"],
            "login_title": SERVER_CONFIG["serverinfo"]["title"],
            "gameserver_online": SERVER_CONFIG["serverinfo"]["gameserver_online"],
            "online_count": SERVER_CONFIG["serverinfo"]["online_count"],
            "announcements": announcements  # 使用统一的格式
        }
        return JSONResponse(content=server_info)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ServerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.server_running = False
        self.setup_ui()
        self.load_saved_config()
        self.load_announcements()
        self.setup_announcement_monitor()
        self.setup_server_status_monitor()
        
    def setup_ui(self):
        # 设置窗口基本属性
        self.setWindowTitle("无限魔兽服务器管理")
        self.setFixedSize(800, 600)
        
        # 设���窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3498db;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #666;
            }
            QTextEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3498db;
                border-radius: 3px;
            }
        """)

        # 创建央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # 服务器配置区域
        config_group = QGroupBox("服务器配置")
        config_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        config_layout = QGridLayout()

        # 登录端口
        config_layout.addWidget(QLabel("登录器端口:"), 0, 0)
        self.login_port = QLineEdit("8080")
        self.login_port.setFixedWidth(100)
        config_layout.addWidget(self.login_port, 0, 1)

        # WOW服务器IP
        config_layout.addWidget(QLabel("WOW服务器IP:"), 1, 0)
        self.wow_ip = QLineEdit("127.0.0.1")
        self.wow_ip.setFixedWidth(100)
        config_layout.addWidget(self.wow_ip, 1, 1)

        # WOW端口号
        config_layout.addWidget(QLabel("WOW端口号:"), 2, 0)
        self.wow_port = QLineEdit("3724")
        self.wow_port.setFixedWidth(100)
        config_layout.addWidget(self.wow_port, 2, 1)

        # 服务器名称
        config_layout.addWidget(QLabel("服务器名称:"), 3, 0)
        self.server_title = QLineEdit("无限火力魔兽")
        self.server_title.setFixedWidth(200)
        config_layout.addWidget(self.server_title, 3, 1)

        # SOAP服务器IP
        config_layout.addWidget(QLabel("SOAP服务器IP:"), 0, 2)
        self.soap_ip = QLineEdit("127.0.0.1")
        self.soap_ip.setFixedWidth(100)
        config_layout.addWidget(self.soap_ip, 0, 3)

        # SOAP端口号
        config_layout.addWidget(QLabel("SOAP端口号:"), 1, 2)
        self.soap_port = QLineEdit("7878")
        self.soap_port.setFixedWidth(100)
        config_layout.addWidget(self.soap_port, 1, 3)

        # SOAP用户名
        config_layout.addWidget(QLabel("SOAP用户名:"), 2, 2)
        self.soap_user = QLineEdit("1")
        self.soap_user.setFixedWidth(100)
        config_layout.addWidget(self.soap_user, 2, 3)

        # SOAP密码
        config_layout.addWidget(QLabel("SOAP密码:"), 3, 2)
        self.soap_pass = QLineEdit("1")
        self.soap_pass.setFixedWidth(100)
        config_layout.addWidget(self.soap_pass, 3, 3)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 服务器日志区域
        log_group = QGroupBox("服务器日志")
        log_group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 1px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 状态栏
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("服务器状态: 已停止")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 添加保存配置按钮
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_current_config)
        status_layout.addWidget(save_btn)
        
        # 添加启动服务按钮
        self.start_btn = QPushButton("启动服务")
        self.start_btn.clicked.connect(self.toggle_server)
        status_layout.addWidget(self.start_btn)
        
        layout.addLayout(status_layout)

    def log_message(self, message):
        """添加日志消息"""
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.log_text.append(f"[{current_time}] {message}")

    def toggle_server(self):
        """切换服务器状态"""
        if not self.server_running:
            # 启动服务器
            self.server_running = True
            self.start_btn.setText("停止服务")
            self.status_label.setText("服务器状态: 启动中")
            self.log_message("服务器启动中...")
            
            # 在新线程中启动服务器
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # 禁用配置输入
            self.disable_config_inputs(True)
            
            # 立即检查一次服务器状态
            QTimer.singleShot(2000, self.check_server_status)  # 2秒后检查
            
        else:
            # 停止服务器
            self.server_running = False
            self.start_btn.setText("启动服务")
            self.status_label.setText("服务器状态: 已停止")
            self.log_message("服务器已停止")
            
            # 重置服务器状态
            SERVER_CONFIG["serverinfo"]["gameserver_online"] = False
            SERVER_CONFIG["serverinfo"]["online_count"] = 0
            
            # 启用配置输入
            self.disable_config_inputs(False)

    def disable_config_inputs(self, disabled):
        """禁用/启用配置输入框"""
        self.login_port.setDisabled(disabled)
        self.wow_ip.setDisabled(disabled)
        self.wow_port.setDisabled(disabled)
        self.server_title.setDisabled(disabled)
        self.soap_ip.setDisabled(disabled)
        self.soap_port.setDisabled(disabled)
        self.soap_user.setDisabled(disabled)
        self.soap_pass.setDisabled(disabled)

    def load_saved_config(self):
        """加载保存的配置"""
        config = load_config()
        
        # 设置UI控件的值
        self.login_port.setText(str(config["server"]["port"]))
        self.wow_ip.setText(config["serverinfo"]["ip"])
        self.wow_port.setText(str(config["serverinfo"]["port"]))
        self.server_title.setText(config["serverinfo"]["title"])
        self.soap_ip.setText(config["soap"]["ip"])
        self.soap_port.setText(str(config["soap"]["port"]))
        self.soap_user.setText(config["soap"]["username"])
        self.soap_pass.setText(config["soap"]["password"])
        
        self.log_message("配置已加载")

    def save_current_config(self):
        """保存当前配置"""
        config = {
            "server": {
                "host": "0.0.0.0",
                "port": int(self.login_port.text()),
                "debug": True
            },
            "serverinfo": {
                "ip": self.wow_ip.text(),
                "port": self.wow_port.text(),
                "title": self.server_title.text(),
                "gameserver_online": SERVER_CONFIG["serverinfo"]["gameserver_online"],
                "online_count": SERVER_CONFIG["serverinfo"]["online_count"],
                "server_notice": SERVER_CONFIG["serverinfo"]["server_notice"]
            },
            "soap": {
                "ip": self.soap_ip.text(),
                "port": self.soap_port.text(),
                "username": self.soap_user.text(),
                "password": self.soap_pass.text()
            },
            "security": SERVER_CONFIG["security"]
        }
        
        # 更新全局配置
        SERVER_CONFIG.update(config)
        
        if save_config(config):
            self.log_message("配置已保存")
            QMessageBox.information(self, "成功", "配置已保存")
        else:
            QMessageBox.warning(self, "错误", "保存配置失败")

    def run_server(self):
        """在新线程中运行服务器"""
        try:
            # 使用api_app替代app
            config = uvicorn.Config(
                app=api_app,  # 这里使用新的变量名
                host=SERVER_CONFIG["server"]["host"],
                port=int(self.login_port.text()),
                reload=False,
                log_level="info"
            )
            server = uvicorn.Server(config)
            server.install_signal_handlers = lambda: None
            
            # 更新运行时配置
            SERVER_CONFIG["server"]["port"] = int(self.login_port.text())
            
            asyncio.run(server.serve())
            
        except Exception as e:
            self.log_message(f"服务器错误: {str(e)}")
            self.server_running = False
            self.start_btn.setText("启动服务")
            self.status_label.setText("服务器状态: 错误")

    def setup_announcement_monitor(self):
        """设置公告文件监控"""
        self.announcement_timer = QTimer()
        self.announcement_timer.timeout.connect(self.check_announcements)
        self.announcement_timer.start(5000)  # 每5秒检查一次
        self.last_modified_time = self.get_announcement_modified_time()
        
    def get_announcement_modified_time(self):
        """获取公告文件修改时间"""
        try:
            return os.path.getmtime('G.txt')
        except:
            return 0
            
    def check_announcements(self):
        """检查公告文件是否更新"""
        current_time = self.get_announcement_modified_time()
        if current_time > self.last_modified_time:
            self.last_modified_time = current_time
            self.load_announcements()
            
    def load_announcements(self):
        """加载公告内容到配置"""
        try:
            with open('G.txt', 'r', encoding='utf-8') as f:
                # 读取所有行并过滤空行
                lines = [line.strip() for line in f.readlines() if line.strip()]
                # 使用 |n 连接所有行
                notice = " |n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
                # 更新配置
                SERVER_CONFIG["serverinfo"]["server_notice"] = notice
                # 同时更新数据库中的公告
                db.announcements = lines  # 更新这里
                self.log_message("公告已更新:")
                self.log_message(notice)
        except Exception as e:
            self.log_message(f"读取公告文件失败: {e}")
            SERVER_CONFIG["serverinfo"]["server_notice"] = "暂无公告"
            db.announcements = ["暂无公告"]  # 更新这里

    def parse_soap_response(self, xml_string):
        """解析SOAP响应，提取result内容或错误信息"""
        try:
            # 移除命名空间前缀，使解析更简单
            xml_string = xml_string.replace('SOAP-ENV:', '').replace('ns1:', '')
            root = ET.fromstring(xml_string)
            
            # 检查是否存在错误信息
            fault = root.find('.//Fault')
            if fault is not None:
                fault_string = fault.find('faultstring').text
                fault_detail = fault.find('detail').text
                self.log_message(f"SOAP错误: {fault_string}\n详细信息: {fault_detail}")
                return f"SOAP错误: {fault_string}\n详细信息: {fault_detail}"
                
            result = root.find('.//result')
            return result.text if result is not None else "未找到结果"
        except Exception as e:
            self.log_message(f"SOAP解析错误: {str(e)}")
            return f"解析错误: {str(e)}"

    def soap_client(self, command):
        """发送SOAP命令到游戏服务器"""
        try:
            # 从配置中获取SOAP连接信息
            soap_ip = SERVER_CONFIG["soap"]["ip"]
            soap_port = int(SERVER_CONFIG["soap"]["port"])
            soap_user = SERVER_CONFIG["soap"]["username"]
            soap_pass = SERVER_CONFIG["soap"]["password"]
            
            # 确保command是经过清理的字符串
            command = command.strip()
            
            # 构建SOAP消息
            soap_message = f"""<?xml version="1.0" encoding="UTF-8"?>
            <SOAP-ENV:Envelope 
                xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" 
                xmlns:ns1="urn:MaNGOS">
                <SOAP-ENV:Body>
                    <ns1:executeCommand>
                        <command>{command}</command>
                    </ns1:executeCommand>
                </SOAP-ENV:Body>
            </SOAP-ENV:Envelope>""".strip()

            # 创建认证字符串
            auth_str = base64.b64encode(f"{soap_user}:{soap_pass}".encode()).decode()
            
            # 创建连接并设置超时
            conn = http.client.HTTPConnection(soap_ip, soap_port, timeout=30)
            
            # 设置请求头，添加认证信息
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "urn:MaNGOS#executeCommand",
                "Authorization": f"Basic {auth_str}",
                "Content-Length": str(len(soap_message))
            }
            
            # 发送请求
            conn.request("POST", "/", soap_message, headers)
            
            # 获取响应
            response = conn.getresponse()
            data = response.read().decode()
            
            # 处理响应
            self.log_message(f"SOAP响应状态: {response.status} {response.reason}")
            result = self.parse_soap_response(data)
            self.log_message(f"SOAP响应结果: {result}")
            
            conn.close()
            return result
            
        except ConnectionError as ce:
            error_msg = f"SOAP连接错误: {str(ce)}"
            self.log_message(error_msg)
            return error_msg
        except TimeoutError:
            error_msg = "SOAP请求超时"
            self.log_message(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"SOAP错误: {str(e)}"
            self.log_message(error_msg)
            return error_msg

    # 示例：添加一个执行SOAP命令的方法
    def execute_soap_command(self, command):
        """执行SOAP命令并显示结果"""
        result = self.soap_client(command)
        self.log_message(f"执行命令: {command}")
        self.log_message(f"执行结果: {result}")
        return result

    def setup_server_status_monitor(self):
        """设置服务器状态监控"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.check_server_status)
        self.status_timer.start(10000)  # 每10秒检查一次
        # 立即执行一次检查
        QTimer.singleShot(0, self.check_server_status)
        
    def check_server_status(self):
        """检查游戏服务器状态"""
        if not self.server_running:
            return
            
        result = self.execute_soap_command("server info")
        if "SOAP错误" in result or "连接错误" in result:
            SERVER_CONFIG["serverinfo"]["gameserver_online"] = False
            SERVER_CONFIG["serverinfo"]["online_count"] = 0
            self.log_message("游戏服务器离线")
        else:
            try:
                # 解析在线人数信息
                # 示例响应: "Players online: 4 (0 queued). Max online: 4 (0 queued)."
                if "Players online:" in result:
                    SERVER_CONFIG["serverinfo"]["gameserver_online"] = True
                    # 提取当前在线人数
                    online_count = int(result.split("Players online:")[1].split("(")[0].strip())
                    SERVER_CONFIG["serverinfo"]["online_count"] = online_count
                    self.log_message(f"游戏服务器在线，当前在线人数: {online_count}")
                else:
                    SERVER_CONFIG["serverinfo"]["gameserver_online"] = False
                    SERVER_CONFIG["serverinfo"]["online_count"] = 0
                    self.log_message("无法解析服务器状态信息")
            except Exception as e:
                SERVER_CONFIG["serverinfo"]["gameserver_online"] = False
                SERVER_CONFIG["serverinfo"]["online_count"] = 0
                self.log_message(f"解析服务器状态失败: {str(e)}")
        
        # 更新状态显示
        self.update_status_display()
        
    def update_status_display(self):
        """更新状态显示"""
        if SERVER_CONFIG["serverinfo"]["gameserver_online"]:
            status = "运行中"
            online_count = SERVER_CONFIG["serverinfo"]["online_count"]
        else:
            status = "离线"
            online_count = 0
            
        self.status_label.setText(f"服务器状态: {status} | 在线人数: {online_count}")

if __name__ == "__main__":
    # 将QApplication实例命名为qt_app
    qt_app = QApplication(sys.argv)
    
    # 设置应用程序图标
    qt_app.setWindowIcon(QIcon("wow_icon.png"))
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    qt_app.setFont(font)
    
    window = ServerUI()
    window.show()
    sys.exit(qt_app.exec_()) 