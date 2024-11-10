from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import uvicorn
import threading
import asyncio
from server import app
from config import SERVER_CONFIG

class ServerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_thread = None
        self.server_running = False
        self.setup_ui()
        
    def setup_ui(self):
        # 设置窗口基本属性
        self.setWindowTitle("无限魔兽服务器管理")
        self.setFixedSize(800, 600)
        
        # 设置窗口样式
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

        # 登录器标题
        config_layout.addWidget(QLabel("登录器标题:"), 3, 0)
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
            self.status_label.setText("服务器状态: 运行中")
            self.log_message("服务器启动中...")
            
            # 在新线程中启动服务器
            self.server_thread = threading.Thread(target=self.run_server)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # 禁用配置输入
            self.disable_config_inputs(True)
            
        else:
            # 停止服务器
            self.server_running = False
            self.start_btn.setText("启动服务")
            self.status_label.setText("服务器状态: 已停止")
            self.log_message("服务器已停止")
            
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

    def run_server(self):
        """在新线程中运行服务器"""
        config = uvicorn.Config(
            app=app,
            host=SERVER_CONFIG["host"],
            port=int(self.login_port.text()),
            reload=False
        )
        server = uvicorn.Server(config)
        asyncio.run(server.serve())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    app.setWindowIcon(QIcon("wow_icon.png"))
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = ServerUI()
    window.show()
    sys.exit(app.exec_()) 