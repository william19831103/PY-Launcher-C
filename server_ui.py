from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import uvicorn
import threading
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from config import CONFIG, save_config, load_config
from network_opcodes import Opcodes
import os
import base64
import http.client
import xml.etree.ElementTree as ET
import hashlib
import json
from pathlib import Path
import urllib.parse
import mysql.connector
from mysql.connector import Error
import random

# 在文件开头添加一个全局变量来存储白名单
GLOBAL_MPQ_WHITELIST = set()

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

def get_db_connection():
    """创建数据库连接"""
    try:
        # 从全局配置获取数据库连接信息
        db_config = {
            'host': CONFIG.get('mysql_host', '127.0.0.1'),
            'port': CONFIG.get('mysql_port', 3306),
            'user': CONFIG.get('mysql_user', 'root'),
            'password': CONFIG.get('mysql_password', 'root'),
            'database': CONFIG.get('mysql_database', 'realmd')
        }
        
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("成功连接到MySQL数据库")
            return connection
    except Error as e:
        print(f"连接数据库时出错: {e}")
        return None

def update_account_security_pwd(account_id, security_pwd):
    """更新账号的安全密码"""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            # 使用email字段存储安全密码
            update_query = "UPDATE `realmd`.`account` SET `email` = %s WHERE `id` = %s"
            cursor.execute(update_query, (security_pwd, account_id))
            connection.commit()
            print(f"成功更新账号 {account_id} 的安全密码")
            return True
    except Error as e:
        print(f"更新安全密码时出错: {e}")
        return False
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_account_id(account_name):
    """获取账号ID"""
    try:
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            query = "SELECT id FROM `realmd`.`account` WHERE username = %s"
            cursor.execute(query, (account_name,))
            result = cursor.fetchone()
            if result:
                return result[0]
    except Error as e:
        print(f"获取账号ID时出错: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
    return None

# API路由
@api_app.post("/api")
async def handle_request(request: Request):
    """处理客户端请求"""
    try:
        request_data = await request.json()
        opcode = request_data.get("opcode")
        data = request_data.get("data", {})
        
        if opcode == Opcodes.SERVER_STATUS:
            # 每次请求时重新读取公告
            try:
                with open('G.txt', 'r', encoding='utf-8') as f:
                    announcements = [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                print(f"读取公告文件失败: {e}")
                announcements = ["暂无公告"]           


            return JSONResponse(content={
                "status": "正常运行" if CONFIG.get("gameserver_online", 0) == 1 else "离线",
                "online_count": CONFIG.get("online_count", 0),
                "announcements": announcements  # 使用刚读取的公告
            })
            
        elif opcode == Opcodes.REGISTER_ACCOUNT:
            account = data["account"]
            password = data["password"]
            security_pwd = data["security_password"]
            
            try:
                # 创建ServerUI实例来使用soap_client
                server_ui = ServerUI()
                command = f"account create {account} {password} {password}"
                result = server_ui.soap_client(command)
                
                # 检查SOAP返回结果
                if "Account created" in result:
                    # 获取新创建的账号ID
 
                    # 尝试最多3次获取账号ID,每次间隔0.3秒
                    account_id = None
                    for _ in range(3):
                        account_id = get_account_id(account)
                        if account_id:
                            break
                        await asyncio.sleep(0.3)
                    if account_id:
                        # 更新安全密码
                        if update_account_security_pwd(account_id, security_pwd):
                            return JSONResponse(content={
                                "success": True, 
                                "message": "注册功"
                            })
                        else:
                            raise HTTPException(status_code=500, detail="更新安全密码失败")
                    else:
                        raise HTTPException(status_code=500, detail="账号注册成功,但是保存安全密码失败,请联系老G")
                else:
                    # 处理常见的错误情况
                    if "already exist" in result:
                        raise HTTPException(status_code=400, detail="该账号已存在")
                    elif "name is invalid" in result:
                        raise HTTPException(status_code=400, detail="账号名称无效")
                    else:
                        raise HTTPException(status_code=400, detail=f"注册失败: {result}")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        elif opcode == Opcodes.CHANGE_PASSWORD:
            account = data["account"]
            new_password = data["new_password"]
            security_pwd = data["security_password"]  # 从请求中获取安全密码
            
            try:
                connection = get_db_connection()
                if connection:
                    cursor = connection.cursor()
                    # 查询账号ID和安全密码(email字段)
                    query = "SELECT id, email FROM `realmd`.`account` WHERE username = %s"
                    cursor.execute(query, (account,))
                    result = cursor.fetchone()
                    
                    if result:
                        account_id, stored_security_pwd = result
                        
                        # 验证安全密码
                        if stored_security_pwd == security_pwd:
                            # 使用SOAP命令修改密码
                            server_ui = ServerUI()
                            command = f"account set password {account_id} {new_password} {new_password}"
                            soap_result = server_ui.soap_client(command)
                            
                            if "The password was changed" in soap_result:
                                return JSONResponse(content={
                                    "success": True,
                                    "message": "密码修改成功"
                                })
                            else:
                                raise HTTPException(status_code=400, detail="修改密码失败,请联系管理员")
                        else:
                            raise HTTPException(status_code=400, detail="安全密码错误")
                    else:
                        raise HTTPException(status_code=404, detail="账号不存在")
                    
            except Error as e:
                print(f"数据库操作错误: {e}")
                raise HTTPException(status_code=500, detail="数据库操作失败")
            finally:
                if connection and connection.is_connected():
                    cursor.close()
                    connection.close()

        else:
            raise HTTPException(status_code=400, detail="未知的操作码")

    except Exception as e:
        print(f"处理请求异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_app.get("/server_info")
async def get_server_info():
    """获取服务器信息"""
    try: 
        # 加载公告
        try:
            with open('G.txt', 'r', encoding='utf-8') as f:
                announcements = [line.strip() for line in f.readlines() if line.strip()]
        except Exception as e:
            print(f"读取公告文件失败: {e}")
            announcements = ["暂无公告"]

        server_info = {
            "wow_ip": CONFIG.get("wow_ip", "127.0.0.1"),
            "wow_port": CONFIG.get("wow_port", "3724"),
            "login_title": CONFIG.get("server_title", "XX魔兽"),
            "status": "正常运行" if CONFIG.get("gameserver_online", 0) == 1 else "离线",
            "online_count": CONFIG.get("online_count", 0),
            "force_wow": CONFIG.get("force_wow", 0),
            "force_mpq": CONFIG.get("force_mpq", 0),
            "check_update_before_play": (CONFIG.get("check_update_before_play", 1)),
            "announcements": announcements,  
        }
        return JSONResponse(content=server_info)
        
    except Exception as e:
        print(f"获取服务器信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

class ServerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.server_running = False
        self.download_path = "Download"
        self.setup_ui()
        # 初始化时加载公告到全局变量
        global Announcements

        self.load_saved_config()
        # 初始化时加载白名单到全局变量
        global GLOBAL_MPQ_WHITELIST
        GLOBAL_MPQ_WHITELIST = self.load_mpq_whitelist()

    def setup_ui(self):
        # 设置窗口基本属性
        self.setWindowTitle("无限魔兽务器管理")
        self.setFixedSize(800, 600)
        
        # 设窗口样式
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

        # 创建中央部件
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
        config_layout.addWidget(QLabel("登录端口:"), 0, 0)
        self.login_port = QLineEdit()
        self.login_port.setFixedWidth(100)
        config_layout.addWidget(self.login_port, 0, 1)

        # WOW服务器IP
        config_layout.addWidget(QLabel("WOW服务器IP:"), 1, 0)
        self.wow_ip = QLineEdit()
        self.wow_ip.setFixedWidth(100)
        config_layout.addWidget(self.wow_ip, 1, 1)

        # WOW端口号
        config_layout.addWidget(QLabel("WOW端口号:"), 2, 0)
        self.wow_port = QLineEdit()
        self.wow_port.setFixedWidth(100)
        config_layout.addWidget(self.wow_port, 2, 1)

        # 服务器名称
        config_layout.addWidget(QLabel("服务器称:"), 3, 0)
        self.server_title = QLineEdit()
        self.server_title.setFixedWidth(200)
        config_layout.addWidget(self.server_title, 3, 1)

        # SOAP配置
        config_layout.addWidget(QLabel("SOAP服务器IP:"), 0, 2)
        self.soap_ip = QLineEdit()
        self.soap_ip.setFixedWidth(100)
        config_layout.addWidget(self.soap_ip, 0, 3)

        config_layout.addWidget(QLabel("SOAP端口号:"), 1, 2)
        self.soap_port = QLineEdit()
        self.soap_port.setFixedWidth(100)
        config_layout.addWidget(self.soap_port, 1, 3)

        config_layout.addWidget(QLabel("SOAP用户名:"), 2, 2)
        self.soap_user = QLineEdit()
        self.soap_user.setFixedWidth(100)
        config_layout.addWidget(self.soap_user, 2, 3)

        config_layout.addWidget(QLabel("SOAP密码:"), 3, 2)
        self.soap_pass = QLineEdit()
        self.soap_pass.setFixedWidth(100)
        config_layout.addWidget(self.soap_pass, 3, 3)

        # 强制更新WOW.EXE
        config_layout.addWidget(QLabel("更新根目录WOW.EXE等(0/1):"), 4, 0)
        self.force_wow = QLineEdit()
        self.force_wow.setFixedWidth(100)
        config_layout.addWidget(self.force_wow, 4, 1)

        # 强制删除无关MPQ
        config_layout.addWidget(QLabel("强制删除无关MPQ(0/1):"), 4, 2)
        self.force_mpq = QLineEdit()
        self.force_mpq.setFixedWidth(100)
        config_layout.addWidget(self.force_mpq, 4, 3)

        # 启动前检查更新 - 移动到这里
        config_layout.addWidget(QLabel("启动前检查更新(0/1):"), 5, 0)
        self.check_update = QLineEdit()
        self.check_update.setFixedWidth(100)
        config_layout.addWidget(self.check_update, 5, 1)

        # MySQL配置标题
        config_layout.addWidget(QLabel("MySQL配置"), 6, 0, 1, 4)

        # MySQL主机
        config_layout.addWidget(QLabel("MySQL主机:"), 7, 0)
        self.mysql_host = QLineEdit()
        self.mysql_host.setFixedWidth(100)
        config_layout.addWidget(self.mysql_host, 7, 1)

        # MySQL端口
        config_layout.addWidget(QLabel("MySQL端口:"), 7, 2)
        self.mysql_port = QLineEdit()
        self.mysql_port.setFixedWidth(100)
        config_layout.addWidget(self.mysql_port, 7, 3)

        # MySQL用户名
        config_layout.addWidget(QLabel("MySQL用户名:"), 8, 0)
        self.mysql_user = QLineEdit()
        self.mysql_user.setFixedWidth(100)
        config_layout.addWidget(self.mysql_user, 8, 1)

        # MySQL密码
        config_layout.addWidget(QLabel("MySQL密码:"), 8, 2)
        self.mysql_pass = QLineEdit()
        self.mysql_pass.setFixedWidth(100)
        config_layout.addWidget(self.mysql_pass, 8, 3)

        # MySQL数据库名
        config_layout.addWidget(QLabel("数据库名:"), 9, 0)
        self.mysql_database = QLineEdit()
        self.mysql_database.setFixedWidth(100)
        config_layout.addWidget(self.mysql_database, 9, 1)



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
        
        self.status_label = QLabel("服务器状: 已停止")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        # 添加保存按钮
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_current_config)
        status_layout.addWidget(self.save_btn)
        
        self.start_btn = QPushButton("启动服务")
        self.start_btn.clicked.connect(self.toggle_server)
        status_layout.addWidget(self.start_btn)
        
        layout.addLayout(status_layout)

        # 在功能按钮区域上方添加选项
        options_container = QWidget(self)
        options_container.setGeometry(60, 640, 1108, 40)  # 调整位置
        options_layout = QHBoxLayout(options_container)
        options_layout.setSpacing(30)

        # 强制更新WOW.EXE选项
        self.force_wow_check = QCheckBox("强制更新WOW.EXE", options_container)
        self.force_wow_check.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #3498db;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #3498db;
                background: #3498db;
            }
        """)
        self.force_wow_check.stateChanged.connect(self.on_force_wow_changed)
        options_layout.addWidget(self.force_wow_check)

        # 强制删除无关MPQ选项
        self.force_mpq_check = QCheckBox("强制删无关MPQ", options_container)
        self.force_mpq_check.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #3498db;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #3498db;
                background: #3498db;
            }
        """)
        self.force_mpq_check.stateChanged.connect(self.on_force_mpq_changed)    


    def log_message(self, message):
        """添加日志消息"""
        current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.log_text.append(f"[{current_time}] {message}")

    def toggle_server(self):
        """切换服务器状态"""
        if not self.server_running:
            # 启动前验证配置
            try:

                self.log_message(f"启动服务器 - 当前配置:")

                # 启动服务器
                self.server_running = True
                self.start_btn.setText("停服务")
                self.status_label.setText("服务器状态: 启动中")
                self.log_message("服务器启动中...")
                
                # 在新线程中启动服务器
                self.server_thread = threading.Thread(target=self.run_server)
                self.server_thread.daemon = True
                self.server_thread.start()
                
                # 禁用配置输入
                self.disable_config_inputs(True)
                
                # 立即检查一次服务器状态
                QTimer.singleShot(2000, self.check_server_status)

                # 设置定时器定期检查服务器状态
                self.status_timer = QTimer(self)
                self.status_timer.timeout.connect(self.check_server_status)
                self.status_timer.start(60000)  # 设置定时器间隔为60000毫秒（即60秒）
                
            except Exception as e:
                self.log_message(f"启动服务器时发生错误: {str(e)}")
                return
                
        else:
            # 停止服务器
            self.server_running = False
            self.start_btn.setText("启动服务")
            self.status_label.setText("服务器状态: 已止")
            self.log_message("服务器已停止")
            
            # 重置服务器状态
            CONFIG["gameserver_online"] = 0  # 使用扁平化的配置
            CONFIG["online_count"] = 0
            
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
        self.force_wow.setDisabled(disabled)
        self.force_mpq.setDisabled(disabled)
        self.check_update.setDisabled(disabled)

    def load_saved_config(self):
        """加载保存的配置"""
        config = CONFIG  # 使用全局配置对象
        
        # 从扁平化配置中加载值
        self.login_port.setText(str(config.get("server_port", 8080)))
        self.wow_ip.setText(config.get("wow_ip", "127.0.0.1"))
        self.wow_port.setText(str(config.get("wow_port", "3724")))
        self.server_title.setText(config.get("server_title", "无限魔兽"))
        self.soap_ip.setText(config.get("soap_ip", "127.0.0.1"))
        self.soap_port.setText(str(config.get("soap_port", "7878")))
        self.soap_user.setText(config.get("soap_username", "1"))
        self.soap_pass.setText(config.get("soap_password", "1"))
        self.force_wow.setText(str(config.get("force_wow", 0)))
        self.force_mpq.setText(str(config.get("force_mpq", 0)))
        self.check_update.setText(str(config.get("check_update_before_play", 1)))
        
        # 加载MySQL配置
        self.mysql_host.setText(config.get("mysql_host", "127.0.0.1"))
        self.mysql_port.setText(str(config.get("mysql_port", 3306)))
        self.mysql_user.setText(config.get("mysql_user", "root"))
        self.mysql_pass.setText(config.get("mysql_password", "root"))
        self.mysql_database.setText(config.get("mysql_database", "realmd"))

        # 添加新配置的加载

        self.log_message("配置已加载")

    def save_current_config(self):
        """保存当前配置"""
        try:
            # 使用扁平化的配置结构
            config = {
                "server_host": "0.0.0.0",
                "server_port": int(self.login_port.text()),
                "server_debug": True,
                
                "wow_ip": self.wow_ip.text(),
                "wow_port": self.wow_port.text(),
                "server_title": self.server_title.text(),
                "gameserver_online": CONFIG.get("gameserver_online", 0),
                "online_count": CONFIG.get("online_count", 0),
                "force_wow": int(self.force_wow.text()),  # 确保是整数
                "force_mpq": int(self.force_mpq.text()),  # 确保是整数
                "check_update_before_play": int(self.check_update.text()),  # 确保是整数
                
                "soap_ip": self.soap_ip.text(),
                "soap_port": self.soap_port.text(),
                "soap_username": self.soap_user.text(),
                "soap_password": self.soap_pass.text(),
                
                "jwt_secret": CONFIG.get("jwt_secret", "your-secret-key"),
                "token_expire_minutes": CONFIG.get("token_expire_minutes", 60),
                "max_login_attempts": CONFIG.get("max_login_attempts", 5),
                
                "mysql_host": self.mysql_host.text(),
                "mysql_port": int(self.mysql_port.text()),
                "mysql_user": self.mysql_user.text(),
                "mysql_password": self.mysql_pass.text(),
                "mysql_database": self.mysql_database.text(),
            }
            
            # 打印要保存的配置
            self.log_message(f"要保存的配置:")

            if save_config(config):
                # 更新全局配置
                CONFIG.clear()
                CONFIG.update(config)
                
                # 保存到文件
                if save_config(config):
                    self.log_message("配置已保存")             
                    QMessageBox.information(self, "成功", "配置已保存")
                else:
                    QMessageBox.warning(self, "错误", "保存配置失败")
                
        except Exception as e:
            self.log_message(f"保存配置时发生错误: {str(e)}")
            QMessageBox.warning(self, "错误", f"保存配置失败: {str(e)}")

    def run_server(self):
        """在新线程中运行服务器"""
        try:
            config = uvicorn.Config(
                app=api_app,
                host=CONFIG.get("server_host", "0.0.0.0"),  # 使用扁平化的配置
                port=int(CONFIG.get("server_port", 8080)),  # 使用扁平化的配置
                reload=False,
                log_level="info"
            )
            server = uvicorn.Server(config)
            server.install_signal_handlers = lambda: None
            
            asyncio.run(server.serve())
            
        except Exception as e:
            self.log_message(f"服务器错误: {str(e)}")
            self.server_running = False
            self.start_btn.setText("启动服务")
            self.status_label.setText("服务器状态: 错误")

    def parse_soap_response(self, xml_string):
        """解析SOAP响应，提取result内容或错误信息"""
        try:
            # 移除命名空间前缀，使解析更简单
            xml_string = xml_string.replace('SOAP-ENV:', '').replace('ns1:', '')
            root = ET.fromstring(xml_string)
            
            # 检是否存在错误信息
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
            return f"解析错: {str(e)}"

    def soap_client(self, command):
        """发送SOAP命令到游戏服务器"""
        try:
            # 从扁平化配置中获取SOAP连接信息
            soap_ip = CONFIG.get("soap_ip", "127.0.0.1")
            soap_port = int(CONFIG.get("soap_port", "7878"))
            soap_user = CONFIG.get("soap_username", "1")
            soap_pass = CONFIG.get("soap_password", "1")
            
            # 确保command是经过清理的字串
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

    def execute_soap_command(self, command):
        """执行SOAP命令并显示结果"""
        result = self.soap_client(command)
        self.log_message(f"执行命令: {command}")
        self.log_message(f"执行结果: {result}")
        return result
        
    def check_server_status(self):
        """检查游戏服务器状态"""
        if not self.server_running:
            return
            
        result = self.execute_soap_command("server info")
        if "SOAP错误" in result or "连接错误" in result:
            CONFIG["gameserver_online"] = 0  # 改为扁化结构
            CONFIG["online_count"] = 0
            self.log_message("游戏服务器离线")
        else:
            try:
                # 解析在线人数息
                # 示例响: "Players online: 4 (0 queued). Max online: 4 (0 queued)."
                if "Players online:" in result:
                    CONFIG["gameserver_online"] = 1  # 改为扁平化结构
                    # 提取当前在线人数
                    online_count = int(result.split("Players online:")[1].split("(")[0].strip())
                    CONFIG["online_count"] = online_count
                    self.log_message(f"游戏服务器在线，当前在线人数: {online_count}")
                else:
                    CONFIG["gameserver_online"] = 0
                    CONFIG["online_count"] = 0
                    self.log_message("无法解析服务器状态信息")
            except Exception as e:
                CONFIG["gameserver_online"] = 0
                CONFIG["online_count"] = 0
                self.log_message(f"解析服务器状态失败: {str(e)}")
        
        # 更新状态显示
        self.update_status_display()
        
    def update_status_display(self):
        """更新状态显示"""
        if CONFIG.get("gameserver_online", 0) == 1:
            status = "运行中"
            online_count = CONFIG.get("online_count", 0)
        else:
            status = "离线"
            online_count = 0
            
        self.status_label.setText(f"服务器状态: {status} | 在线人数: {online_count}")


    def on_force_mpq_changed(self, text):
        """强制删除无关MPQ选项改变处理"""
        try:
            value = text.strip()
            if value not in ["0", "1"]:
                self.force_mpq.setText("0")
                return
            self.log_message(f"MPQ选项状态改变: {value}")
            CONFIG["force_clean_mpq"] = int(value)
        except Exception as e:
            self.log_message(f"更新MPQ选项时发生错误: {str(e)}")
            self.force_mpq.setText("0")

    def on_force_wow_changed(self, text):
        """强制更新WOW.EXE选项改变处理"""
        try:
            value = text.strip()
            if value not in ["0", "1"]:
                self.force_wow.setText("0")
                return
            self.log_message(f"WOW选项状态改变: {value}")
            CONFIG["force_update_wow"] = int(value)
        except Exception as e:
            self.log_message(f"更新WOW选项时发生错误: {str(e)}")
            self.force_wow.setText("0")

    def load_mpq_whitelist(self):
        """加载MPQ白名单"""
        whitelist = set()
        try:
            # 从白名单文件加载
            with open('MpqWhiteList.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        whitelist.add(line.lower())
            self.log_message(f"已加载MPQ白名单: {len(whitelist)}个文件")

            # 添加服务器Data目录下的MPQ文件到白名单
            download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Download")
            server_data_path = os.path.join(download_path, "Data")
            if os.path.exists(server_data_path):
                for file in os.listdir(server_data_path):
                    if file.lower().endswith('.mpq'):
                        whitelist.add(file.lower())
                        print(f"添加服务器MPQ到白名单: {file.lower()}")                    
            print(f"最终的MPQ白名单: {whitelist}")

        except Exception as e:
            self.log_message(f"加载MPQ白名单失败: {str(e)}")
            
        return whitelist

    def on_save_clicked(self):
        """保存按钮点击处理"""
        try:
            # 直接从复选框获取当前状态
            force_wow = 1 if self.force_wow_check.isChecked() else 0
            force_mpq = 1 if self.force_mpq_check.isChecked() else 0
            
            self.log_message(f"保存配置 - 强制更新WOW: {force_wow}, 强制删除MPQ: {force_mpq}")
            
            # 使用扁平化的配置结构
            config = {
                "server_host": "0.0.0.0",
                "server_port": int(self.login_port.text()),
                "server_debug": True,
                
                "wow_ip": self.wow_ip.text(),
                "wow_port": self.wow_port.text(),
                "server_title": self.server_title.text(),
                "gameserver_online": CONFIG.get("gameserver_online", 0),
                "online_count": CONFIG.get("online_count", 0),
                "force_wow": force_wow,  # 直接使用整数值
                "force_mpq": force_mpq,  # 直接使用整数值
                
                "soap_ip": self.soap_ip.text(),
                "soap_port": self.soap_port.text(),
                "soap_username": self.soap_user.text(),
                "soap_password": self.soap_pass.text(),
                
                "jwt_secret": CONFIG.get("jwt_secret", "your-secret-key"),
                "token_expire_minutes": CONFIG.get("token_expire_minutes", 60),
                "max_login_attempts": CONFIG.get("max_login_attempts", 5)
            }
            
            # 更新全局配置
            CONFIG.clear()
            CONFIG.update(config)
            
            # 保存到文件
            if save_config(config):
                self.log_message("配置已保存")
                self.log_message(f"保存的force_wow: {CONFIG.get('force_wow')}")
                self.log_message(f"保存的force_mpq: {CONFIG.get('force_mpq')}")
                QMessageBox.information(self, "成功", "配置已保存")
            else:
                QMessageBox.warning(self, "错误", "保存配置失败")
                
        except Exception as e:
            self.log_message(f"保存配置时发生错误: {str(e)}")
            QMessageBox.warning(self, "错误", f"保存配置失败: {str(e)}")


# 添加新的API路由
@api_app.get("/check_update")
async def check_update():
    """获取服务器文件列表并处理MPQ同步"""
    try:
        download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Download")
        print(f"扫描目录: {download_path}") 

        files_info = {}
        
        # 使用全局白名单
        mpq_whitelist = GLOBAL_MPQ_WHITELIST.copy()  

        # 扫描Download目录
        for root, _, files in os.walk(download_path):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, download_path)
                relative_path = relative_path.replace('\\', '/')
                
                # 根据不同目录和配置决定是否加文件
                if relative_path.startswith('Wow/'):
                    # Wow目录下的文件只在force_wow=1时添加
                    if int(CONFIG.get("force_wow", 0)) == 1:
                        print(f"添加Wow目录文件: {relative_path}")
                        files_info[relative_path] = {
                            'hash': hashlib.md5(open(full_path, 'rb').read()).hexdigest(),
                            'size': os.path.getsize(full_path),
                            'is_mpq': False,
                            'in_whitelist': False,
                            'is_wow_file': True,
                            'is_data_file': False
                        }
                elif relative_path.startswith('Data/'):
                    # Data目录下的文件始终添���
                    file_lower = file.lower()
                    is_mpq = file_lower.endswith('.mpq')
                    in_whitelist = file_lower in mpq_whitelist if is_mpq else False
                    
                    print(f"添加Data目录文件: {relative_path}")
                    print(f"- 是否MPQ: {is_mpq}")
                    print(f"- 是否在白名单: {in_whitelist}")
                    
                    files_info[relative_path] = {
                        'hash': hashlib.md5(open(full_path, 'rb').read()).hexdigest(),
                        'size': os.path.getsize(full_path),
                        'is_mpq': is_mpq,
                        'in_whitelist': in_whitelist,
                        'is_wow_file': False,
                        'is_data_file': True
                    }
                else:
                    # 其他目录的文件始终添加
                    print(f"添加其他目录件: {relative_path}")
                    files_info[relative_path] = {
                        'hash': hashlib.md5(open(full_path, 'rb').read()).hexdigest(),
                        'size': os.path.getsize(full_path),
                        'is_mpq': False,
                        'in_whitelist': False,
                        'is_wow_file': False,
                        'is_data_file': False
                    }



        # 构建响应数据，添加更多信息
        response_data = {
            "files": files_info,
            "mpq_whitelist": list(mpq_whitelist)    
        }
                
        # 使用 JSONResponse 时指定媒体类型和编码，并添加额外的响应头
        return JSONResponse(
            content=response_data,
            media_type="application/json",
            headers={
                "Content-Type": "application/json; charset=utf-8",
            }
        )
        
    except Exception as e:
        print(f"获取文件列表失败: {str(e)}")
        print(f"异常类型: {type(e)}")
        print(f"异常详情: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """下载指定文件"""
    try:
        # 解码文件路径
        file_path = urllib.parse.unquote(file_path)
        # 规范化路径分隔符
        file_path = file_path.replace('\\', '/')
        # 构建完整的文件路径
        full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Download", file_path)
        
        print(f"请下载文件: {file_path}")
        print(f"完整路径: {full_path}")
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return FileResponse(
                path=full_path,
                filename=os.path.basename(file_path),
                media_type='application/octet-stream'
            )
        else:
            print(f"文件不存在: {full_path}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
    except Exception as e:
        print(f"下载文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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