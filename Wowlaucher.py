from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import os
import subprocess
import requests
from PyQt5.QtWidgets import QDialog, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from network_opcodes import Opcodes
import json
import aiohttp
import asyncio
import hashlib
from pathlib import Path
import urllib.parse

class WowLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置窗口标题和大小
        self.setWindowTitle("连接中...")  # 初始标题，等待从服务器获取
        self.setFixedSize(1228, 921)
        
        # 添加背景图片
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, 1228, 921)
        self.background.setPixmap(QPixmap("bg.jpg").scaled(
            1228, 
            921,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        ))

        self.setStyleSheet
        ("""
            QLabel {
                color: white;
                font-size: 16px;
            }
            QPushButton {
                background-color: rgba(41, 128, 185, 0.8);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(52, 152, 219, 0.8);
            }
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 1px solid #3498db;
                border-radius: 5px;
                padding: 10px;
            }
        """
        )
        
        self.setup_ui()
        
        # 启动时立即获取服务器信息和状态
        asyncio.run(self.initial_update())  # 使用asyncio.run执行异步初始化
        
        # 创建定时器定期更新服务器状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_server_status)
        self.timer.start(30000)  # 每30秒更新一次

    async def initial_update(self):
        """启动时的初始更新"""
        try:
            # 先获取服务器状态
            response = await self.send_request(Opcodes.SERVER_STATUS)
            if response:
                # 更新状态和在线人数
                server_status = response.get('status', '未知')  # 获取服务器返回的状态
                online_count = response.get('online_count', 0)
                
                status = f"服务器状态: {server_status}\n"  # 使用服务器返回的状态
                status += f"在线人数: {online_count}\n\n"
                status += "公告：\n"
                
                # 处理公告内容
                announcements = response.get('announcements', ['暂无公告'])
                for announcement in announcements:
                    status += f"{announcement}\n"
                    
                # 立即更新显示
                self.info_box.setText(status)
                
            # 再获取服务器信息
            server_info = await self.get_server_info()
            if server_info:
                # 更新标题
                title = server_info.get("login_title", "无限魔兽")
                self.setWindowTitle(title)
                self.title_label.setText(title)
                
        except Exception as e:
            print(f"初始化更新失败: {str(e)}")
            self.info_box.setText("无法获取服务器信息")

    def setup_ui(self):
        # 题文字放大300%
        self.title_label = QLabel("连接中...", self)  # 初始标题，等从服务器获取
        self.title_label.setGeometry(0, -50, 1228, 200)  # 增加高度以适应更大的字体
        self.title_label.setStyleSheet("""
            font-size: 64px;  /* 84px * 1 */
            color: white;
            font-weight: bold;
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 128, 255, 180))  # 设置阴影颜色
        shadow.setOffset(0, 0)
        self.title_label.setGraphicsEffect(shadow)

        
        # 创建中央部件，调整位置和大小
        central_widget = QWidget(self)
        central_widget.setGeometry(60, 100, 1108, 600)  # 向上移动50个像素
        
        # 主布局
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(40)
        
        # 服务器信息区域 - 增加字体大小
        info_box = QTextEdit(central_widget)
        info_box.setFixedHeight(550)
        info_box.setReadOnly(True)  # 设置为只读
        info_box.setTextInteractionFlags(Qt.TextBrowserInteraction)  # 只允许文本选择和链接点击
        info_box.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                border: 1px solid rgba(52, 152, 219, 0.8);
                border-radius: 5px;
                padding: 20px;
                font-size: 24px;
                line-height: 1.8;
            }
            QTextEdit[readOnly="true"] {
                background-color: rgba(0, 0, 0, 0.7);  /* 确保只读状态下的背景色 */
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.2);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(52, 152, 219, 0.8);
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.info_box = info_box
        layout.addWidget(info_box)

        
        # 添加弹性空间
        layout.addStretch()
        
        # 功能按钮区域 - 使用背景图片的按钮
        button_container = QWidget(self)        
        button_container.setGeometry(60, 690, 1108, 50)
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(30)
        
        # 创建三个带背景的按钮容器
        for text in ["账号管理", "游戏商城", "检查更新"]:
            # 创建按钮容器
            btn_frame = QFrame(button_container)
            btn_frame.setFixedSize(220, 40)
            btn_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(41, 128, 185, 0.8);
                    border-radius: 5px;
                }
            """)
            
            # 在容器内创建按钮
            btn = QPushButton(text, btn_frame)
            btn.setGeometry(0, 0, 220, 40)  # 填满容器
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    font-size: 18px;
                    font-weight: bold;    
                }
                QPushButton:hover {
                    background-color: rgba(52, 152, 219, 0.3);
                }
            """)
            
            # 设置按钮文字居中
            btn.setFixedSize(220, 50)
            
            if text == "账号管理":
                self.register_btn = btn
            elif text == "游戏商城":
                self.shop_btn = btn
            else:
                self.update_btn = btn
                
            button_layout.addWidget(btn_frame)
        
        # 进度条位置调整
        self.progress = QProgressBar(self)
        self.progress.setGeometry(60, 770, 1108, 15)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 4px;
                text-align: center;
                background-color: rgba(0, 0, 0, 0.3);
            }
            QProgressBar::chunk {
                background-color: rgba(52, 152, 219, 0.8);
                border-radius: 4px;
            }
        """)
        self.progress.hide()
        
        # 开始游戏按钮
        self.start_btn = QPushButton("开始游戏", self)
        self.start_btn.setGeometry(494, 810, 240, 70)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(46, 204, 113, 0.8);
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(46, 204, 113, 0.9);
            }
        """)
        
        # 连接信号
        self.register_btn.clicked.connect(self.open_register)
        self.shop_btn.clicked.connect(self.open_shop)
        self.update_btn.clicked.connect(self.check_update_clicked)
        self.start_btn.clicked.connect(self.start_game)
        
        # 初始化服务器状态
        self.update_server_status()

    async def send_request(self, opcode, data=None):
        """发送网络请求的通用方法"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://localhost:8080/api"
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                # 构建请求数据
                request_data = {
                    "opcode": int(opcode),  # 确保opcode是整数
                    "data": data if data else {}
                }
                
                print(f"发送请求: {url}")  # 调试信息
                print(f"请求数据: {request_data}")  # 调试信息
                
                async with session.post(url, 
                                      json=request_data, 
                                      headers=headers,
                                      timeout=30) as response:
                    print(f"响应状态: {response.status}")  # 调试信息
                    
                    if response.status == 200:
                        result = await response.json()
                        print(f"响应数据: {result}")  # 调试信息
                        return result
                    else:
                        error_text = await response.text()
                        print(f"错误响应: {error_text}")  # 调试信息
                        raise Exception(f"请求失败: {error_text}")
                        
        except asyncio.TimeoutError:
            QMessageBox.warning(self, "错误", "服务器连接超时")
            return None
        except Exception as e:
            print(f"请求异常: {str(e)}")  # 调试信息
            QMessageBox.warning(self, "错误", f"网络请求失败: {str(e)}")
            return None

    def register_account(self, account, password, security_pwd):
        """注册账号"""
        data = {
            "account": account,
            "password": password,
            "security_password": security_pwd
        }
        
        response = asyncio.run(self.send_request(Opcodes.REGISTER_ACCOUNT, data))
        return response
        
    def change_password(self, account, old_password, new_password):
        """修改密码"""
        data = {
            "account": account,
            "old_password": old_password,
            "new_password": new_password
        }
        
        response = asyncio.run(self.send_request(Opcodes.CHANGE_PASSWORD, data))
        return response
        
    def unlock_character(self, account, character_name):
        """角色解卡"""
        data = {
            "account": account,
            "character_name": character_name
        }
        
        response = asyncio.run(self.send_request(Opcodes.UNLOCK_CHARACTER, data))
        return response
        
    def check_client_update(self):
        """检查客户端更新"""
        response = asyncio.run(self.send_request(Opcodes.CHECK_VERSION))
        if response and response.get("needs_update"):
            patch_list = response.get("patch_list", [])
            return patch_list
        return None

    def update_server_status(self):
        """更新服务器状态"""
        try:
            response = asyncio.run(self.send_request(Opcodes.SERVER_STATUS))
            if response:
                # 更新状态和在线人数
                server_status = response.get('status', '未知')  # 获取服务器返回的状态
                online_count = response.get('online_count', 0)
                
                status = f"服务器状态: {server_status}\n"  # 使用服务器返回的状态
                status += f"在线人数: {online_count}\n\n"
                status += "公告：\n"
                
                # 处理公告内容
                announcements = response.get('announcements', ['暂无公告'])
                for announcement in announcements:
                    status += f"{announcement}\n"
                    
                # 立即更新显示
                self.info_box.setText(status)
        except Exception as e:
            print(f"更新服务器状态失败: {str(e)}")
            self.info_box.setText("无法获取服务器状态")
    
    def open_register(self):
        dialog = RegisterDialog(self)
        # 将对话框移动到主窗口中心
        dialog.move(self.geometry().center() - dialog.rect().center())
        
        if dialog.exec_() == QDialog.Accepted:
            # 获取输入的数据
            account = dialog.account_input.text()
            password = dialog.password_input.text()
            confirm_pwd = dialog.confirm_pwd_input.text()
            security_pwd = dialog.security_pwd_input.text()
            captcha = dialog.captcha_input.text()
            
            # 验证输入
            if not self._validate_register_input(account, password, confirm_pwd, security_pwd, captcha):
                return
            
            # TODO: 发送注册请求到服务器
            try:
                # 这里添加与服务器通信的代码
                QMessageBox.information(self, "成功", "账号注册成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"注册失败：{str(e)}")
    
    def _validate_register_input(self, account, password, confirm_pwd, security_pwd, captcha):
        """验证注册输入"""
        if len(account) < 4 or len(account) > 12:
            QMessageBox.warning(self, "错误", "账号长度必须在4-12位之间")
            return False
            
        if len(password) < 4 or len(password) > 12:
            QMessageBox.warning(self, "错误", "密码长度必须在4-12位之间")
            return False
            
        if password != confirm_pwd:
            QMessageBox.warning(self, "错误", "两次输入的密码不一致")
            return False
            
        if len(security_pwd) < 1 or len(security_pwd) > 8:
            QMessageBox.warning(self, "错误", "安全密码长度必须在1-8位之间")
            return False
            
        if not captcha:
            QMessageBox.warning(self, "错", "请输入验证码")
            return False
            
        return True
    
    def open_shop(self):
        QDesktopServices.openUrl(QUrl("http://your-server.com/shop"))
    
    def check_update_clicked(self):
        """检查更新按钮点击处理"""
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 运行异步任务
            loop.run_until_complete(self.check_update())
        finally:
            # 关闭事件循环
            loop.close()

    async def check_update(self):
        """检查更新"""
        try:
            self.progress.show()
            self.progress.setValue(0)
            self.update_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            self.log_message("开始检查更新...")

            # 获取客户端根目录
            client_root = os.path.dirname(os.path.abspath(__file__))
            self.log_message(f"客户端目录: {client_root}")

            # 获取服务器文件列表和更新选项
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8080/check_update") as response:
                    if response.status == 200:
                        data = await response.json()
                        server_files = data["files"]
                        
                        # 从新的配置结构中读取值
                        config = data.get("config", {})
                        force_wow = int(config.get("force_wow", 0))
                        force_mpq = int(config.get("force_mpq", 0))
                        
                        # 打印接收到的配置值用于调试
                        print(f"接收到的配置: {json.dumps(config, indent=2)}")
                        print(f"force_wow: {force_wow}")
                        print(f"force_mpq: {force_mpq}")
                        
                        mpq_whitelist = set(data.get("mpq_whitelist", []))
                        
                        self.log_message(f"获取到服务器文件列表: {len(server_files)}个文件")
                        self.log_message(f"强制更新WOW.EXE: {'是' if force_wow == 1 else '否'}")
                        self.log_message(f"强制删除无关MPQ: {'是' if force_mpq == 1 else '否'}")
                    else:
                        raise Exception("获取服务器文件列表失败")

            # 检查本地文件
            need_update = []
            total_size = 0

            # 处理文件更新
            for file_path, info in server_files.items():
                local_path = os.path.join(client_root, file_path)
                
                # 处理Wow目录下的文件
                if file_path.startswith("Wow/"):
                    if force_wow == 1:
                        # 强制更新Wow目录下的所有文件
                        target_path = os.path.join(client_root, file_path.replace("Wow/", ""))
                        self.log_message(f"添加Wow目录文件到更新列表: {file_path}")
                        need_update.append((file_path, target_path))
                        total_size += info['size']
                    continue

                # 处理Data目录下的文件
                if file_path.startswith("Data/"):
                    if force_mpq == 1:
                        # 检查是否在白名单中
                        file_name = os.path.basename(file_path).lower()
                        if file_name in mpq_whitelist:
                            if not os.path.exists(local_path) or await self.get_file_hash(Path(local_path)) != info['hash']:
                                self.log_message(f"添加白名单MPQ文件到更新列表: {file_path}")
                                need_update.append((file_path, local_path))
                                total_size += info['size']
                        else:
                            # 删除不在白名单中的MPQ文件
                            if os.path.exists(local_path):
                                try:
                                    os.remove(local_path)
                                    self.log_message(f"删除非白名单MPQ文件: {file_path}")
                                except Exception as e:
                                    self.log_message(f"删除文件失败 {file_path}: {str(e)}")
                    else:
                        # 不检查白名单，只同步文件
                        if not os.path.exists(local_path) or await self.get_file_hash(Path(local_path)) != info['hash']:
                            self.log_message(f"添加Data目录文件到更新列表: {file_path}")
                            need_update.append((file_path, local_path))
                            total_size += info['size']

            if not need_update:
                self.progress.hide()
                self.update_btn.setEnabled(True)
                self.start_btn.setEnabled(True)
                self.log_message("客户端已是最新版本")
                QMessageBox.information(self, "更新", "客户端已是最新版本")
                return

            # 开始下载需要更新的文件
            self.log_message(f"需要更新 {len(need_update)} 个文件")
            downloaded_size = 0
            for server_path, local_path in need_update:
                try:
                    self.log_message(f"正在更新: {server_path}")
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)

                    # 下载文件
                    async with aiohttp.ClientSession() as session:
                        encoded_path = urllib.parse.quote(server_path)
                        url = f"http://localhost:8080/download/{encoded_path}"
                        self.log_message(f"下载URL: {url}")
                        
                        async with session.get(url) as response:
                            if response.status == 200:
                                self.log_message(f"开始下载到: {local_path}")
                                with open(local_path, 'wb') as f:
                                    while True:
                                        chunk = await response.content.read(8192)
                                        if not chunk:
                                            break
                                        f.write(chunk)
                                        downloaded_size += len(chunk)
                                        progress = int((downloaded_size / total_size) * 100)
                                        self.progress.setValue(progress)
                                self.log_message(f"文件下载完成: {server_path}")
                            else:
                                error_text = await response.text()
                                raise Exception(f"下载失败 ({response.status}): {error_text}")

                except Exception as e:
                    self.log_message(f"下载文件 {server_path} 失败: {str(e)}")
                    raise

            self.progress.hide()
            self.update_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            self.log_message("更新完成")
            QMessageBox.information(self, "更新", "更新完成")

        except Exception as e:
            self.log_message(f"更新失败: {str(e)}")
            self.progress.hide()
            self.update_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            QMessageBox.warning(self, "错误", f"更新失败: {str(e)}")

        if force_mpq == 1:
            self.log_message("检查无关MPQ文件...")
            data_dir = os.path.join(client_root, "Data")
            if os.path.exists(data_dir):
                # 获取客户端Data目录下所有MPQ文件
                client_mpq_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.mpq')]
                self.log_message(f"客户端MPQ文件: {client_mpq_files}")
                self.log_message(f"白名单MPQ文件: {mpq_whitelist}")
                
                # 检查每个MPQ文件
                for mpq_file in client_mpq_files:
                    mpq_file_lower = mpq_file.lower()
                    if mpq_file_lower not in mpq_whitelist:
                        full_path = os.path.join(data_dir, mpq_file)
                        try:
                            os.remove(full_path)
                            self.log_message(f"删除非白名单MPQ文件: {mpq_file}")
                        except Exception as e:
                            self.log_message(f"删除文件失败 {mpq_file}: {str(e)}")

    async def get_file_hash(self, filepath):
        """获取文件的MD5哈希值"""
        try:
            md5_hash = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except Exception as e:
            self.log_message(f"计算文件哈希失败 {filepath}: {str(e)}")
            return None

    def start_game(self):
        wow_path = "C:\\Program Files\\World of Warcraft\\Wow.exe"
        if os.path.exists(wow_path):
            subprocess.Popen(wow_path)
        else:
            QMessageBox.warning(self, "错误", "未找到游戏客户端，请确认安装路径正确")

    async def get_server_info(self):
        """获取服务器信息"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8080/server_info") as response:
                    if response.status == 200:
                        data = await response.json()
                        # 更新UI
                        self.update_server_info(data)
                        return data
                    else:
                        raise Exception("获取服务器信息失败")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法连接到服务器: {str(e)}")
            return None

    def update_server_info(self, server_info):
        """更新服务器信息到UI"""
        try:
            # 设置窗口标题和标签标题
            title = server_info.get("login_title", "无限魔兽")
            self.setWindowTitle(title)
            self.title_label.setText(title)
            
            # 更新状态和在线人数
            server_status = server_info.get('status', '未知')  # 从服务器信息中获取状态
            online_count = server_info.get('online_count', 0)
            
            status = f"服务器状态: {server_status}\n"
            status += f"在线人数: {online_count}\n\n"
            status += "公告：\n"
            
            # 更新公告
            announcements = server_info.get("announcements", ["暂无公告"])
            for announcement in announcements:
                status += f"{announcement}\n"
                
            # 立即更新显示
            self.info_box.setText(status)
        except Exception as e:
            print(f"更新服务器信息失败: {str(e)}")

    def log_message(self, message):
        """添加日志消息到信息框"""
        current_text = self.info_box.toPlainText()
        if current_text:
            current_text += "\n"
        current_text += message
        self.info_box.setText(current_text)
        # 滚动到底部
        self.info_box.verticalScrollBar().setValue(
            self.info_box.verticalScrollBar().maximum()
        )
        # 让 Qt 处理事件，立即更新显示
        QApplication.processEvents()

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("当前分区")
        self.setFixedSize(550, 550)  # 增加30%的尺寸
        
        # 设置窗口背景色和样式
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #ffffff;
                font-size: 16px;
            }
            QLineEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                padding: 8px;
                margin: 2px;
                height: 32px;
                font-size: 16px;
            }
            QRadioButton {
                color: white;
                spacing: 10px;
                font-size: 16px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #3a3a3a;
                padding: 10px 30px;
                min-width: 120px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        
        # 创建主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(20)  # 增加垂直间距
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.main_layout)
        
        # 标题标签 - 红色背景
        title_container = QWidget()
        title_container.setStyleSheet("background-color: #aa0000;")
        title_container.setFixedHeight(40)
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("[无限魔兽]")
        title_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(title_label)
        
        self.main_layout.addWidget(title_container)
        
        # 提示文本
        hint_label = QLabel("*欢迎使用账号注册服务,请务必牢记账号密码")
        hint_label.setStyleSheet("color: #00BFFF; font-size: 20px;")
        self.main_layout.addWidget(hint_label)
        
        # 创建输入框区域
        self.account_input = self._create_input("账号名称", "4-12位数字和字母")
        self.password_input = self._create_input("输入密", "4-12位数字和字母")
        self.confirm_pwd_input = self._create_input("确认密码", "两次输入的密码")
        self.security_pwd_input = self._create_input("安全密码", "1-8位数字和字母")
        
        # 验证码区域
        captcha_container = QWidget()
        captcha_layout = QHBoxLayout(captcha_container)
        captcha_layout.setContentsMargins(0, 0, 0, 0)
        captcha_layout.setSpacing(15)

        # 创建左侧标签
        captcha_label = QLabel("随机验证:")
        captcha_label.setFixedWidth(100)  # 与其他标签相同宽度

        # 创建入框
        self.captcha_input = QLineEdit()
        self.captcha_input.setFixedWidth(250)  # 与其他输入框相同宽度

        # 创建验证码数字标签
        captcha_number = QLabel("10023")
        captcha_number.setStyleSheet("""
            color: #ff0000;
            font-size: 16px;
        """)

        # 添加到布局
        captcha_layout.addWidget(captcha_label)
        captcha_layout.addWidget(self.captcha_input)
        captcha_layout.addWidget(captcha_number)
        captcha_layout.addStretch()

        self.main_layout.addWidget(captcha_container)

        # 移除原来的placeholder
        self.captcha_input.setPlaceholderText("")

        # 单选按钮组
        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(30)
        self.register_radio = QRadioButton("账号注册")
        self.unlock_radio = QRadioButton("角色解卡")
        self.change_pwd_radio = QRadioButton("更改密码")
        self.register_radio.setChecked(True)
        radio_layout.addWidget(self.register_radio)
        radio_layout.addWidget(self.unlock_radio)
        radio_layout.addWidget(self.change_pwd_radio)
        self.main_layout.addLayout(radio_layout)
        
        # 服务类型标签
        service_label = QLabel("服务类型: 账号注册")
        service_label.setStyleSheet("color: #00BFFF; font-size: 14px;")
        self.main_layout.addWidget(service_label)
        
        # 添加弹性空间
        self.main_layout.addStretch()
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        
        # 设置按钮样式
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                border: none;
                color: white;
                padding: 10px 30px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
        """)
        
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
                color: white;
                padding: 10px 30px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.setSpacing(20)
        self.main_layout.addLayout(btn_layout)
        
        # 连按钮号
        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
    def _create_input(self, label_text, placeholder_text):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # 创左侧标签
        label = QLabel(f"{label_text}:")
        label.setFixedWidth(100)
        
        # 创建输入框
        input_field = QLineEdit()
        input_field.setFixedWidth(250)
        
        # 创建右侧提示文本
        hint = QLabel(placeholder_text)
        hint.setStyleSheet("color: #666666; font-size: 14px;")
        
        # 添加到布局
        layout.addWidget(label)
        layout.addWidget(input_field)
        layout.addWidget(hint)
        layout.addStretch()
        
        self.main_layout.addWidget(container)
        return input_field

    def accept(self):
        account = self.account_input.text()
        password = self.password_input.text()
        security_pwd = self.security_pwd_input.text()
        
        if self.register_radio.isChecked():
            response = self.parent().register_account(account, password, security_pwd)
            if response and response.get("success"):
                QMessageBox.information(self, "成功", "账号注册成功！")
                self.accept()
            else:
                QMessageBox.warning(self, "错误", response.get("message", "注册失败"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    app.setWindowIcon(QIcon("wow_icon.png"))
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 12)
    app.setFont(font)
    
    launcher = WowLauncher()
    launcher.show()
    sys.exit(app.exec_())
