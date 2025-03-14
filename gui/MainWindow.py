from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from gui.ChatWidget import ChatWidget
from gui.PluginManagerWidget import PluginManagerWidget

class MainWindow(QMainWindow):
    """主窗口，包含聊天界面和插件管理界面"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatVision")
        self.resize(900, 700)
        
        # 中央选项卡布局
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 创建聊天界面
        self.chat_widget = ChatWidget()
        self.tabs.addTab(self.chat_widget, "聊天")
        
        # 创建插件管理界面
        self.plugin_manager = PluginManagerWidget()
        self.tabs.addTab(self.plugin_manager, "插件管理")
        
        # 状态栏
        self.statusBar().showMessage("就绪")
