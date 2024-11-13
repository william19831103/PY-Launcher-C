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
import psutil
from ctypes import *
from ctypes.wintypes import *
import win32process
import win32event
import win32con
import win32api
import win32security

class WowLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 1. 首先加载配置文件
        self.load_config()
        
        # 2. 设置窗口标题和大小
        self.setWindowTitle("连接中...")  # 初始标题，等待从服务器获取
        self.setFixedSize(1228, 921)

        # 3. 初始化全局变量
        self.wow_ip = "127.0.0.1"
        self.wow_port = "3724" 
        self.login_title = "XX魔兽"
        self.online_count = 0
        self.force_wow = 0
        self.force_mpq = 0
        self.check_update_before_play = 1
        self.announcements = ["暂无公告"]
        self.encryption_key = "@@112233"
        # 4. 创建事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 5. 添加背景图片
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, 1228, 921)
        self.background.setPixmap(QPixmap("bg.jpg").scaled(
            1228, 
            921,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        ))

        # 6. 设置UI
        self.setup_ui()
        
        # 7. 启动时立即获取服务器信息和状态
        self.loop.run_until_complete(self.initial_update())
        
        # 8. 创建定时器定期更新服务器状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_server_status)
        self.timer.start(60000)  # 每60秒更新一次

    def load_config(self):
        """从配置文件加载服务器连接信息"""
        try:
            config_path = 'launcher_config.json'
            print(f"正在加载配置文件: {config_path}")
            
            if not os.path.exists(config_path):
                print(f"配置文件不存在: {config_path}")
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
                
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.api_host = config.get('api_host', 'localhost')
                self.api_port = config.get('api_port', '8080')
                self.api_base_url = f"http://{self.api_host}:{self.api_port}"
                print(f"成功加载服务器配置: {self.api_base_url}")
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            print("使用默认配置")
            # 使用默认值
            self.api_host = 'localhost'
            self.api_port = '8080'
            self.api_base_url = f"http://{self.api_host}:{self.api_port}"

    async def initial_update(self):
        """启动时的初始更新"""
        try:
            # 先获取服务器信息，因为这包含了check_update_before_play的值
            server_info = await self.get_server_info()
            if server_info:
                # 更新标题
                title = server_info.get("login_title", "无限魔兽")
                self.setWindowTitle(title)
                self.title_label.setText(title)
                
                # 确保check_update_before_play被正确设置
                self.check_update_before_play = int(server_info.get("check_update_before_play", 1))
                print(f"初始化时获取到启动前检查更新设置: {self.check_update_before_play}")
            
            # 再获取服务器状态
            response = await self.send_request(Opcodes.SERVER_STATUS)
            if response:
                # 更新状态和在线人数
                server_status = response.get('status', '未知')
                online_count = response.get('online_count', 0)
                
                status = f"服务器状态: {server_status}\n"
                status += f"在线人数: {online_count}\n\n"
                status += "公告：\n"
                
                # 处理公告内容
                announcements = response.get('announcements', ['暂无公告'])
                for announcement in announcements:
                    status += f"{announcement}\n"
                    
                # 立即更新显示
                self.info_box.setText(status)
                
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
        
        # 开始游戏按
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
                # 使用配置的 API URL
                url = f"{self.api_base_url}/api"
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                request_data = {
                    "opcode": int(opcode),
                    "data": data if data else {}
                }
                
                print(f"发送请求: {url}")
                print(f"请求数据: {request_data}")
                
                async with session.post(url, 
                                      json=request_data, 
                                      headers=headers,
                                      timeout=30) as response:
                    print(f"响应状态: {response.status}")
                    
                    # 读取响应内容
                    response_text = await response.text()
                    print(f"响应内容: {response_text}")
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        # 尝试解析错误响应
                        try:
                            error_data = json.loads(response_text)
                            # 返回错误信息，而不是抛出异常
                            return {
                                "success": False,
                                "detail": error_data.get("detail", "未知错误")
                            }
                        except:
                            return {
                                "success": False,
                                "detail": response_text
                            }
                        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "detail": "服务器连接超时"
            }
        except Exception as e:
            print(f"请求异常: {str(e)}")
            return {
                "success": False,
                "detail": str(e)
            }        


    def update_server_status(self):
        """更新服务器状态"""
        try:
            self.loop.run_until_complete(self._async_update_server_status())
            # 同时更新服务器信息
            self.loop.run_until_complete(self.get_server_info())
        except Exception as e:
            print(f"更新服务器状态失败: {str(e)}")
            self.info_box.setText("无法获取服务器状态")

    async def _async_update_server_status(self):
        """异更新服务器状态"""
        try:
            response = await self.send_request(Opcodes.SERVER_STATUS)
            if response:
                server_status = response.get('status', '未知')
                online_count = response.get('online_count', 0)
                
                status = f"服务器状态: {server_status}\n"
                status += f"在线人数: {online_count}\n\n"
                status += "公告：\n"
                
                announcements = response.get('announcements', ['暂无公告'])
                for announcement in announcements:
                    status += f"{announcement}\n"
                    
                self.info_box.setText(status)
        except Exception as e:
            print(f"更新服务器状态失: {str(e)}")
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
                        
    def open_change_pwd(self):
        dialog = ChangePasswordDialog(self)
        # 将对话框移动到主窗口中
        dialog.move(self.geometry().center() - dialog.rect().center())
        dialog.exec_()
    
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
            # 显示进度条
            self.progress.show()
            self.progress.setValue(0)
            self.update_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            self.log_message("开始检查更新...")

            # 获取客户端根目录
            client_root = os.path.dirname(os.path.abspath(__file__))
            self.log_message(f"客户端目录: {client_root}")
            # 检查wow.exe是否在运行
            def is_wow_running():
                # 获取当前文件所在目录的绝对路径
                current_dir = os.path.dirname(os.path.abspath(__file__))  
                # 构建当前目录下的 Wow.exe 路径
                wow_exe_path = os.path.join(current_dir, 'Wow.exe')  

                # 获取进程的执行路径和PID
                for proc in psutil.process_iter(['pid', 'exe']):  
                    try:
                        if proc.info['exe'] and os.path.abspath(proc.info['exe']).lower() == wow_exe_path.lower():
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                return False
                
            if is_wow_running():
                self.log_message("检测到游戏正在运行")
                self.progress.hide()
                self.update_btn.setEnabled(True)
                self.start_btn.setEnabled(True)
                QMessageBox.warning(self, "错误", "请先关闭游戏客户端再进行更新")
                return

            # 获取服务器文件列表和更新选项
            async with aiohttp.ClientSession() as session:
                # 用配置的 API URL
                async with session.get(f"{self.api_base_url}/check_update") as response:
                    if response.status == 200:
                        data = await response.json()
                        server_files = data["files"] 
                        
                        mpq_whitelist = set(data.get("mpq_whitelist", []))
                        
                        #self.log_message(f"获到服务器文件列表: {len(server_files)}个文件")
                        #self.log_message(f"强制更新WOW.EXE: {'是' if self.force_wow == 1 else '否'}")
                        #self.log_message(f"强制删除无关MPQ: {'是' if self.force_mpq == 1 else '否'}")
                        self.log_message(f"启动前检查更新: {'是' if self.check_update_before_play == 1 else '否'}")
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
                    if self.force_wow == 1:
                        # 强制更新Wow目录的文件,但需要检查hash
                        target_path = os.path.join(client_root, file_path.replace("Wow/", ""))
                        if not os.path.exists(target_path) or await self.get_file_hash(Path(target_path)) != info['hash']:
                            self.log_message(f"添加Wow目录文件到更新列表: {file_path}")
                            need_update.append((file_path, target_path))
                            total_size += info['size']
                    continue

                # 处理Data目录下的文件
                if file_path.startswith("Data/"):
                    if self.force_mpq == 1:
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
                #QMessageBox.information(self, "更新", "客户端已是最新版本")
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
                        url = f"http://{self.api_base_url}/download/{encoded_path}"
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

        if self.force_mpq == 1:
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
        """开始游戏"""
        try:
            # 启动前检查更新
            if int(self.check_update_before_play) == 1:  # 确保进行整数比较
                print("启动前检查更新已开启,开始检查更新...")
                # 创建事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # 运行检查更新
                    loop.run_until_complete(self.check_update())
                    # 检查更新完成后再启动游戏
                    self._launch_game()
                finally:
                    loop.close()
            else:
                print("启动前检查更新已关闭,直接启动游戏...")
                self._launch_game()
                
        except Exception as e:
            print(f"启动游戏时发生错误: {str(e)}")  # 添加错误日志
            QMessageBox.warning(self, "错误", f"启动游戏失败: {str(e)}")

    def inject_dll(self, process_handle, dll_path):
        """将DLL注入到目标进程"""
        try:
            kernel32 = WinDLL('kernel32', use_last_error=True)
            
            # 计算DLL路径字符串长度
            dll_path_size = len(dll_path) + 1
            
            # 在目标进程中分配内存
            dll_path_addr = kernel32.VirtualAllocEx(
                process_handle.handle,
                None,
                dll_path_size,
                win32con.MEM_COMMIT | win32con.MEM_RESERVE,
                win32con.PAGE_READWRITE
            )
            
            if not dll_path_addr:
                raise Exception(f"VirtualAllocEx failed with error code: {kernel32.GetLastError()}")
            
            # 写入DLL路径到目标进程
            written = c_ulong(0)
            if not kernel32.WriteProcessMemory(
                process_handle.handle,
                dll_path_addr,
                dll_path.encode('ascii'),
                dll_path_size,
                byref(written)
            ):
                raise Exception(f"WriteProcessMemory failed with error code: {kernel32.GetLastError()}")
            
            # 获取LoadLibraryA地址
            kernel32_handle = win32api.GetModuleHandle("kernel32.dll")
            load_library_addr = win32api.GetProcAddress(kernel32_handle, "LoadLibraryA")
            
            # 创建远程线程
            LPTHREAD_START_ROUTINE = WINFUNCTYPE(DWORD, LPVOID)
            routine = LPTHREAD_START_ROUTINE(load_library_addr)
            
            thread_h = kernel32.CreateRemoteThread(
                process_handle.handle,
                None,
                0,
                routine,
                dll_path_addr,
                0,
                None
            )
            
            if not thread_h:
                raise Exception(f"CreateRemoteThread failed with error code: {kernel32.GetLastError()}")
            
            # 等待注入完成
            result = win32event.WaitForSingleObject(thread_h, 1000)  # 等待1秒
            if result != win32event.WAIT_OBJECT_0:
                raise Exception(f"WaitForSingleObject failed with result: {result}")
            
            # 清理资源
            kernel32.VirtualFreeEx(process_handle.handle, dll_path_addr, 0, win32con.MEM_RELEASE)
            win32api.CloseHandle(thread_h)
            
            return True
            
        except Exception as e:
            print(f"DLL注入失败: {str(e)}")
            return False

    def _launch_game(self):
        """实际启动游戏的方法"""
        # 获取当前目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        wow_path = os.path.join(current_dir, 'Wow.exe')
        dll_path = os.path.join(current_dir, 'DllReadFile.dll')

        # 检查文件是否存在
        if not os.path.exists(wow_path):
            QMessageBox.warning(self, "错误", "未找到游戏客户端，请确认安装路径正确")
            return
            
        if not os.path.exists(dll_path):
            QMessageBox.warning(self, "错误", "未找到DLL文件，请确认安装完整")
            return

        # 修改realmlist.wtf
        realmlist_path = os.path.join(current_dir, 'realmlist.wtf')
        with open(realmlist_path, 'w') as f:
            if self.wow_port != "3724":
                f.write(f"set realmlist {self.wow_ip}:{self.wow_port}\n")
            else:
                f.write(f"set realmlist {self.wow_ip}\n")

        try:
            # 设置启动信息
            startup_info = win32process.STARTUPINFO()
            startup_info.dwFlags |= win32process.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = win32con.SW_SHOWNORMAL
            
            # 设置环境变量
            env = os.environ.copy()
            env['MPQ_DECRYPT_KEY'] = self.encryption_key
            
            # 创建进程(挂起状态)
            proc_info = win32process.CreateProcess(
                wow_path,
                None,
                None,
                None,
                False,
                win32con.CREATE_SUSPENDED,
                env,
                None,
                startup_info
            )
            
            process_handle = proc_info[0]
            thread_handle = proc_info[1]
            
            # 注入DLL
            if self.inject_dll(process_handle, dll_path):
                # 恢复进程运行
                win32process.ResumeThread(thread_handle)
            else:
                # 注入失败则终止进程
                win32process.TerminateProcess(process_handle.handle, 1)
                raise Exception("DLL注入失败")
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动游戏失败: {str(e)}")
            
            # 确保进程被终止
            try:
                win32process.TerminateProcess(process_handle.handle, 1)
            except:
                pass
            
        finally:
            # 清理句柄
            try:
                win32api.CloseHandle(process_handle.handle)
                win32api.CloseHandle(thread_handle)
            except:
                pass

    async def get_server_info(self):
        """获取服务器信息"""
        try:
            async with aiohttp.ClientSession() as session:
                # 使用配的 API URL
                async with session.get(f"{self.api_base_url}/server_info") as response:
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
            self.login_title = server_info.get("login_title", "XX魔兽") 
            self.setWindowTitle(self.login_title)
            self.title_label.setText(self.login_title)
            
            # 更新状态和在线人数
            server_status = server_info.get('status', '未知')
            self.online_count = server_info.get("online_count", 0)
            
            status = f"服务器状态: {server_status}\n"
            status += f"在线人数: {self.online_count}\n\n"

            # 公告
            self.announcements = server_info.get("announcements", ["暂无公告"])
            for announcement in self.announcements:
                status += f"{announcement}\n"                
            # 立即更新显示
            self.info_box.setText(status)

            # 更新全局变量
            self.wow_ip = server_info.get("wow_ip", "127.0.0.1")
            self.wow_port = server_info.get("wow_port", "3724")

            # 强制更新
            self.force_wow = server_info.get("force_wow", 0)
            self.force_mpq = server_info.get("force_mpq", 0)           
            self.check_update_before_play = (server_info.get("check_update_before_play", 0))
            self.encryption_key = server_info.get("encryption_key", "@@112233")
            print(f"获取到启动前检查更新设置: {self.check_update_before_play}")  # 添加调试日志
            
        except Exception as e:
            print(f"更新服务器信息失败: {str(e)}")

    def log_message(self, message):
        """加日志消息到信息框"""
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

    def closeEvent(self, event):
        """窗口关闭时清理事件循环"""
        self.loop.close()
        super().closeEvent(event)

    async def register_account(self, account, password, security_pwd):
        """发送注册账号请求"""
        try:
            # 准备请求数据
            data = {
                "account": account,
                "password": password,
                "security_password": security_pwd
            }
            
            # 发送请求
            response = await self.send_request(Opcodes.REGISTER_ACCOUNT, data)
            
            if response:
                if response.get("success"):
                    return {
                        "success": True,
                        "detail": "注册成功"
                    }
                else:
                    return {
                        "success": False, 
                        "detail": response.get("detail", "注册失败")
                    }
            else:
                return {
                    "success": False,
                    "detail": "服务器无响应"
                }
                
        except Exception as e:
            print(f"注册账号时发生错误: {str(e)}")
            return {
                "success": False,
                "detail": str(e)
            }

    async def change_password(self, account, security_pwd, new_password):
        """发送修改密码请求"""
        try:
            # 准备请求数据
            data = {
                "account": account,
                "new_password": new_password,
                "security_password": security_pwd
            }
            
            # 发送请求
            response = await self.send_request(Opcodes.CHANGE_PASSWORD, data)
            
            if response:
                if response.get("success"):
                    return {
                        "success": True,
                        "detail": "修改密码成功"
                    }
                else:
                    return {
                        "success": False,
                        "detail": response.get("detail", "修改密码失败")
                    }
            else:
                return {
                    "success": False,
                    "detail": "服务器无响应"
                }
                
        except Exception as e:
            print(f"修改密码时发生错误: {str(e)}")
            return {
                "success": False,
                "detail": str(e)
            }

# 首先创建一个基类
class BaseServiceDialog(QDialog):
    def __init__(self, parent=None, title="服务对话框", hint_text="欢迎使用服务"):
        super().__init__(parent)
        self.setWindowTitle("当前分区")
        self.setFixedSize(550, 550)
        
        # 设置通用样式表
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
            QRadioButton:disabled {
                color: #4CAF50;
                font-weight: bold;
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
        
        self.setup_ui(title, hint_text)
        
    def setup_ui(self, title, hint_text):
        # 创建主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(20)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(self.main_layout)
        
        # 标题区域
        self._setup_title()
        
        # 提示文本
        self._setup_hint(hint_text)
        
        # 输入框区域
        self._setup_inputs()
        
        # 验证码区域
        self._setup_captcha()
        
        # 单选按钮组
        self._setup_radio_buttons()
        
        # 按钮区域
        self._setup_buttons()
        
    def _setup_title(self):
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
        
    def _setup_hint(self, hint_text):
        hint_label = QLabel(hint_text)
        hint_label.setStyleSheet("color: #00BFFF; font-size: 20px;")
        self.main_layout.addWidget(hint_label)
        
    def _create_input(self, label_text, placeholder_text):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        label = QLabel(f"{label_text}:")
        label.setFixedWidth(100)
        
        input_field = QLineEdit()
        input_field.setFixedWidth(250)
        input_field.setPlaceholderText(placeholder_text)
        
        hint = QLabel(placeholder_text)
        hint.setStyleSheet("color: #666666; font-size: 14px;")
        
        layout.addWidget(label)
        layout.addWidget(input_field)
        layout.addWidget(hint)
        layout.addStretch()
        
        self.main_layout.addWidget(container)
        return input_field
        
    def _setup_captcha(self):
        captcha_container = QWidget()
        captcha_layout = QHBoxLayout(captcha_container)
        captcha_layout.setContentsMargins(0, 0, 0, 0)
        captcha_layout.setSpacing(15)

        captcha_label = QLabel("随机验证:")
        captcha_label.setFixedWidth(100)

        self.captcha_input = QLineEdit()
        self.captcha_input.setFixedWidth(250)

        self.captcha_number = QLabel()
        self.captcha_number.setStyleSheet("""
            color: #ff0000;
            font-size: 16px;
            font-weight: bold;
            background-color: #333333;
            padding: 5px 10px;
            border-radius: 3px;
        """)
        
        self.current_captcha = self.generate_captcha()
        self.captcha_number.setText(self.current_captcha)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(60)
        self.refresh_btn.clicked.connect(self.refresh_captcha)

        captcha_layout.addWidget(captcha_label)
        captcha_layout.addWidget(self.captcha_input)
        captcha_layout.addWidget(self.captcha_number)
        captcha_layout.addWidget(self.refresh_btn)
        captcha_layout.addStretch()

        self.main_layout.addWidget(captcha_container)
        
    def _setup_buttons(self):
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        
        self.confirm_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        
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
        
        btn_layout.addWidget(self.confirm_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        self.main_layout.addLayout(btn_layout)
        
        self.confirm_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def generate_captcha(self):
        import random
        return ''.join(str(random.randint(0, 9)) for _ in range(4))

    def refresh_captcha(self):
        self.current_captcha = self.generate_captcha()
        self.captcha_number.setText(self.current_captcha)

    def _setup_radio_buttons(self):
        radio_layout = QHBoxLayout()
        radio_layout.setSpacing(30)
        self.register_radio = QRadioButton("账号注册")
        self.change_pwd_radio = QRadioButton("更改密码")
        
        radio_layout.addWidget(self.register_radio)
        radio_layout.addWidget(self.change_pwd_radio)
        self.main_layout.addLayout(radio_layout)

# 注册对话框类
class RegisterDialog(BaseServiceDialog):
    def __init__(self, parent=None):
        super().__init__(parent, 
                        title="账号注册",
                        hint_text="*欢迎使用账号注册服务,请务必牢记账号密码")
        
    def _setup_inputs(self):
        self.account_input = self._create_input("账号名称", "4-12位数字和字母")
        self.password_input = self._create_input("输入密码", "4-12位数字和字母")
        self.confirm_pwd_input = self._create_input("确认密码", "两次输入的密码")
        self.security_pwd_input = self._create_input("安全密码", "1-8位数字和字��")
        
        # ���置验证器
        for input_field in [self.account_input, self.password_input, 
                          self.confirm_pwd_input, self.security_pwd_input]:
            input_field.setValidator(QRegExpValidator(QRegExp("^[a-zA-Z0-9]*$")))
            
    def _setup_radio_buttons(self):
        super()._setup_radio_buttons()
        self.register_radio.setChecked(True)
        self.register_radio.setEnabled(False)
        self.change_pwd_radio.clicked.connect(self.open_change_pwd)
        
    def accept(self):
        try:
            # 获取并验证输入
            account = self.account_input.text().strip()
            password = self.password_input.text().strip()
            confirm_pwd = self.confirm_pwd_input.text().strip()
            security_pwd = self.security_pwd_input.text().strip()
            captcha = self.captcha_input.text().strip()
            
            # 验证输入
            if not self._validate_input(account, password, confirm_pwd, security_pwd, captcha):
                return
                
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 获取 WowLauncher 实例并发送注册请求
                launcher = self.parent()
                response = loop.run_until_complete(launcher.register_account(account, password, security_pwd))
                
                if response.get("success"):
                    QMessageBox.information(self, "成功", "账号注册成功!")
                    super().accept()
                else:
                    error_msg = response.get("detail", "注册失败")
                    QMessageBox.warning(self, "错误", error_msg)
                    
            finally:
                loop.close()
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"注册失败: {str(e)}")
            
    def _validate_input(self, account, password, confirm_pwd, security_pwd, captcha):
        if not all([account, password, confirm_pwd, security_pwd]):
            QMessageBox.warning(self, "错误", "请填写所有必填项")
            return False
            
        if not account.isalnum() or not password.isalnum() or not security_pwd.isalnum():
            QMessageBox.warning(self, "错误", "输入只能包含字母和数字")
            return False
            
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
            
        if captcha != self.current_captcha:
            QMessageBox.warning(self, "错误", "验证码错误")
            self.refresh_captcha()
            self.captcha_input.clear()
            return False
            
        return True
        
    def open_change_pwd(self):
        self.close()
        dialog = ChangePasswordDialog(self.parent())
        dialog.move(self.parent().geometry().center() - dialog.rect().center())
        dialog.exec_()

# 修改密码对话框类
class ChangePasswordDialog(BaseServiceDialog):
    def __init__(self, parent=None):
        super().__init__(parent, 
                        title="修改密码",
                        hint_text="*欢迎使用修改密码服务")
        
    def _setup_inputs(self):
        self.account_input = self._create_input("账号名称", "4-12位数字和字母")
        self.new_password_input = self._create_input("新密码", "4-12位数字和字母")
        self.security_pwd_input = self._create_input("安全密码", "注册时设置的安全密码")
        
        # 设置验证器和密码模式
        for input_field in [self.account_input, self.new_password_input, self.security_pwd_input]:
            input_field.setValidator(QRegExpValidator(QRegExp("^[a-zA-Z0-9]*$")))
        self.new_password_input.setEchoMode(QLineEdit.Password)
            
    def _setup_radio_buttons(self):
        super()._setup_radio_buttons()
        self.change_pwd_radio.setChecked(True)
        self.change_pwd_radio.setEnabled(False)
        self.register_radio.clicked.connect(self.switch_to_register)
        
    def accept(self):
        try:
            account = self.account_input.text().strip()
            new_password = self.new_password_input.text().strip()
            security_pwd = self.security_pwd_input.text().strip()
            captcha = self.captcha_input.text().strip()
            
            if not self._validate_input(account, new_password, security_pwd, captcha):
                return
                
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 获取 WowLauncher 实例并发送修改密码请求
                launcher = self.parent()
                response = loop.run_until_complete(launcher.change_password(account, security_pwd, new_password))
                
                if response.get("success"):
                    QMessageBox.information(self, "成功", "密码修改成功!")
                    super().accept()
                else:
                    error_msg = response.get("detail", "修改密码失败")
                    QMessageBox.warning(self, "错误", error_msg)
                    
            finally:
                loop.close()
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"修改密码失败: {str(e)}")
            
    def _validate_input(self, account, new_password, security_pwd, captcha):
        if not all([account, new_password, security_pwd, captcha]):
            QMessageBox.warning(self, "错误", "请填写所有必填项")
            return False
            
        if not account.isalnum() or not new_password.isalnum():
            QMessageBox.warning(self, "错误", "账号和密码只能包含字母和数字")
            return False
            
        if len(account) < 4 or len(account) > 12:
            QMessageBox.warning(self, "错误", "账号长度必须在4-12位之间")
            return False
            
        if len(new_password) < 4 or len(new_password) > 12:
            QMessageBox.warning(self, "错误", "新密码长度必须在4-12位之间")
            return False
            
        if captcha != self.current_captcha:
            QMessageBox.warning(self, "错误", "验证码错误")
            self.refresh_captcha()
            self.captcha_input.clear()
            return False
            
        return True
        
    def switch_to_register(self):
        self.close()
        dialog = RegisterDialog(self.parent())
        dialog.move(self.parent().geometry().center() - dialog.rect().center())
        dialog.exec_()

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
