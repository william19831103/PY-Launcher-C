from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import os
import subprocess
import requests

class WowLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        # 设置窗口标题和大小
        self.setWindowTitle("无限魔兽")
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
        
        # 创建定时器定期更新服务器状态
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_server_status)
        self.timer.start(30000)

    def setup_ui(self):
        # 标题文字放大300%
        title = QLabel("无限魔兽", self)
        title.setGeometry(0, -50, 1228, 200)  # 增加高度以适应更大的字体
        title.setStyleSheet("""
            font-size: 64px;  /* 84px * 1 */
            color: white;
            font-weight: bold;
        """)
        title.setAlignment(Qt.AlignCenter)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 128, 255, 180))  # 设置阴影颜色
        shadow.setOffset(0, 0)
        title.setGraphicsEffect(shadow)

        
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
        self.update_btn.clicked.connect(self.check_update)
        self.start_btn.clicked.connect(self.start_game)
        
        # 初始化服务器状态
        self.update_server_status()

    def update_server_status(self):
        try:
            # 这里替换为实际的服务器API
            # response = requests.get("http://your-server.com/api/status")
            # data = response.json()
            
            # 模拟数据
            status = "服务器状态: 正常运行\n"
            status += "在线人数: 1000\n\n"
            status += "公告：\n"
            status += "1. 独家自制各职业专属技能升级模式\n"
            status += "2. 自制五人挑战地图\n"
            status += "3. 自制BOSS乐园\n"
            status += "4. 自制飞行地图\n"
            status += "5. 收藏宇宙合成神龙触发特殊事件"
            
            self.info_box.setText(status)
        except:
            self.info_box.setText("无法获取服务器状态")
    
    def open_register(self):
        QDesktopServices.openUrl(QUrl("http://your-server.com/register"))
    
    def open_shop(self):
        QDesktopServices.openUrl(QUrl("http://your-server.com/shop"))
    
    def check_update(self):
        self.progress.show()
        self.progress.setValue(0)
        
        # 模拟更新进度
        self.update_progress = 0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_progress_bar)
        self.update_timer.start(50)
    
    def update_progress_bar(self):
        self.update_progress += 1
        self.progress.setValue(self.update_progress)
        
        if self.update_progress >= 100:
            self.update_timer.stop()
            QMessageBox.information(self, "更新完成", "客户端已是最新版本！")
            self.progress.hide()
    
    def start_game(self):
        wow_path = "C:\\Program Files\\World of Warcraft\\Wow.exe"
        if os.path.exists(wow_path):
            subprocess.Popen(wow_path)
        else:
            QMessageBox.warning(self, "错误", "未找到游戏客户端，请确认安装路径正确")

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
