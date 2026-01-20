import sys
import os
import json
import pyperclip
import keyboard
from PyQt5.QtWidgets import(
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QDialog, QLineEdit, QLabel, QTextEdit as QtTextEdit,
    QComboBox, QMessageBox, QSplitter, QMenu, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QInputDialog
)
from PyQt5.QtCore import (
    Qt, QPoint, QTimer, pyqtSignal, QObject
)
from PyQt5.QtGui import (
    QFont, QPixmap, QPainter, QColor, QBrush, QRegion, QImage
)
from PIL import Image

# ===================== 配置管理 =====================
CONFIG_FILE = "config.json"

def load_config():
    """加载配置文件"""
    default_config = {
        "enable_floating": True,
        "hotkey_mode": 0  # 0: 点击外部隐藏; 1: 再次按快捷键隐藏
    }
    if not os.path.exists(CONFIG_FILE):
        save_config(default_config)
        return default_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        QMessageBox.warning(None, "错误", "配置文件损坏，将使用默认设置。")
        save_config(default_config)
        return default_config

def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        QMessageBox.critical(None, "错误", f"保存配置失败：{str(e)}")

# ===================== 悬浮窗类 =====================
class FloatingWindow(QWidget):
    toggle_main_window = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.parent_window = parent
        self.setFixedSize(100, 100)
        self.setWindowOpacity(0.95)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.img_path = "xxx.png"
        self.pixmap = self.load_circular_image()

        self.dragging = False
        self.drag_start_pos = QPoint()
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.on_single_click)

    def load_circular_image(self):
        target_pixmap = QPixmap(100, 100)
        target_pixmap.fill(Qt.transparent)
        
        if os.path.exists(self.img_path):
            try:
                img = Image.open(self.img_path).convert("RGBA")
                img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                
                width, height = img.size
                bytes_per_line = 4 * width
                img_data = img.tobytes("raw", "RGBA")
                q_image = QImage(img_data, width, height, bytes_per_line, QImage.Format_RGBA8888)
                img_pixmap = QPixmap.fromImage(q_image)
                
                painter = QPainter(target_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                x = (100 - width) // 2
                y = (100 - height) // 2
                painter.setClipRegion(QRegion(0, 0, 100, 100, QRegion.Ellipse))
                painter.drawPixmap(x, y, img_pixmap)
                painter.end()
            except Exception as e:
                print(f"加载图片失败：{e}")
                self.draw_default_circle(target_pixmap)
        else:
            self.draw_default_circle(target_pixmap)
        
        self.setMask(QRegion(0, 0, 100, 100, QRegion.Ellipse))
        return target_pixmap

    def draw_default_circle(self, pixmap):
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(66, 133, 244))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 100, 100)
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(0, 0, self.pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.click_timer.start(200)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self.drag_start_pos)
            self.click_timer.stop()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()

    def on_single_click(self):
        self.toggle_main_window.emit()

# ===================== 设置窗口类 =====================
class SettingsDialog(QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(350, 200)
        self.current_config = current_config
        self.result_config = current_config.copy()

        layout = QVBoxLayout()

        # 悬浮窗设置
        self.float_check = QCheckBox("启用悬浮窗 (重启生效)")
        self.float_check.setChecked(self.current_config["enable_floating"])
        self.float_check.stateChanged.connect(self.on_float_changed)
        layout.addWidget(self.float_check)

        # 快捷键模式设置
        mode_group = QGroupBox("快捷键行为模式")
        mode_layout = QVBoxLayout()
        
        self.mode0_radio = QRadioButton("模式 A：点击软件外区域自动隐藏 (类似剪贴板)")
        self.mode1_radio = QRadioButton("模式 B：再次按下快捷键隐藏")
        
        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.mode0_radio, 0)
        self.mode_group.addButton(self.mode1_radio, 1)
        
        if self.current_config["hotkey_mode"] == 0:
            self.mode0_radio.setChecked(True)
        else:
            self.mode1_radio.setChecked(True)
            
        self.mode_group.buttonClicked[int].connect(self.on_mode_changed)

        mode_layout.addWidget(self.mode0_radio)
        mode_layout.addWidget(self.mode1_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def on_float_changed(self, state):
        self.result_config["enable_floating"] = (state == Qt.Checked)

    def on_mode_changed(self, id):
        self.result_config["hotkey_mode"] = id

    def save(self):
        save_config(self.result_config)
        QMessageBox.information(self, "提示", "设置已保存！\n*悬浮窗设置需重启软件生效。")
        self.accept()

# ===================== 主窗口类 =====================
class HALFunctionBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HAL函数浏览器")
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)

        # 1. 加载配置
        self.config = load_config()
        
        # 2. 初始化数据
        self.base_dir = init_base_dir()
        self.init_default_data()

        # 3. 初始化UI
        self._init_ui()

        # 4. 初始化悬浮窗 (根据配置)
        self.floating_win = None
        if self.config["enable_floating"]:
            self.init_floating_window()

        # 5. 初始化keyboard快捷键
        self.init_hotkey()

        # 标志位
        self.is_hotkey_showing = False

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 顶部按钮栏
        top_layout = QHBoxLayout()
        self.add_mcu_btn = QPushButton("新建单片机")
        self.add_mcu_btn.clicked.connect(self.add_mcu)
        self.add_cat_btn = QPushButton("新建分类")
        self.add_cat_btn.clicked.connect(self.add_category)
        self.add_func_btn = QPushButton("添加函数")
        self.add_func_btn.clicked.connect(self.add_function)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_tree)
        
        # 新增设置按钮
        self.settings_btn = QPushButton("设置")
        self.settings_btn.clicked.connect(self.open_settings)

        top_layout.addWidget(self.add_mcu_btn)
        top_layout.addWidget(self.add_cat_btn)
        top_layout.addWidget(self.add_func_btn)
        top_layout.addWidget(self.refresh_btn)
        top_layout.addWidget(self.settings_btn)
        top_layout.addStretch()

        # 分割器
        splitter = QSplitter(Qt.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("HAL函数库")
        self.tree.setMinimumWidth(300)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        self.refresh_tree()

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setFont(QFont("Consolas", 10))
        self.detail_text.setPlaceholderText("选中函数查看详情...")

        splitter.addWidget(self.tree)
        splitter.addWidget(self.detail_text)
        splitter.setSizes([400, 600])

        main_layout = QVBoxLayout(central_widget)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(splitter)

    def init_floating_window(self):
        self.floating_win = FloatingWindow(self)
        self.floating_win.toggle_main_window.connect(self.toggle_visibility)
        screen_geo = QApplication.desktop().screenGeometry()
        self.floating_win.move(screen_geo.width() - 120, screen_geo.height() - 120)
        self.floating_win.show()

    def init_hotkey(self):
        """绑定快捷键"""
        keyboard.add_hotkey('ctrl+D', self.on_hotkey_triggered)

    def on_hotkey_triggered(self):
        """直接在回调中操作UI"""
        if self.config["hotkey_mode"] == 1:
            # 模式B：再次按快捷键隐藏
            if self.isVisible():
                self.hide()
            else:
                self.is_hotkey_showing = True
                self.showNormal()
                self.activateWindow()
        else:
            # 模式A：点击外部隐藏
            if not self.isVisible():
                self.is_hotkey_showing = True
                self.showNormal()
                self.activateWindow()

    def toggle_visibility(self):
        """悬浮窗点击切换显示/隐藏"""
        if self.isVisible():
            self.hide()
        else:
            self.is_hotkey_showing = True
            self.showNormal()
            self.activateWindow()

    def focusOutEvent(self, event):
        """失去焦点立即隐藏"""
        if self.config["hotkey_mode"] == 0 and self.is_hotkey_showing:
            self.hide()
            self.is_hotkey_showing = False
        super().focusOutEvent(event)

    def open_settings(self):
        """打开设置窗口"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_():
            self.config = dialog.result_config

    # ------------------- 业务逻辑 -------------------
    def init_default_data(self):
        """初始化默认数据"""
        stm32_dir = os.path.join(self.base_dir, "stm32")
        if not os.path.exists(stm32_dir):
            os.makedirs(stm32_dir)
        
        gpio_file = os.path.join(stm32_dir, "GPIO.json")
        if not os.path.exists(gpio_file):
            default_gpio = {
                "HAL_GPIO_Init(GPIO_TypeDef  *GPIOx, GPIO_InitTypeDef *GPIO_Init)": 
                """/**
  * @：GPIO初始化
  * @：HAL_GPIO_Init(GPIOA, GPIO_PIN_9)
  */""",
                "HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin, GPIO_PinState PinState)": 
                """/**
  * @：GPIO写状态
  * @：HAL_GPIO_WritePin(GPIOF, GPIO_PIN_9,GPIO_PIN_RESET)
  * @:第二个参数：GPIO_PIN_RESET/GPIO_PIN_SET
  */"""
            }
            save_category_functions(self.base_dir, "stm32", "GPIO", default_gpio)
        
        py32_dir = os.path.join(self.base_dir, "py32")
        if not os.path.exists(py32_dir):
            os.makedirs(py32_dir)

    def refresh_tree(self):
        """刷新树形列表"""
        self.tree.clear()
        mcu_folders = get_mcu_folders(self.base_dir)
        for mcu in mcu_folders:
            mcu_item = QTreeWidgetItem(self.tree)
            mcu_item.setText(0, mcu)
            mcu_item.setData(0, Qt.UserRole, ("mcu", mcu))

            categories = get_category_files(self.base_dir, mcu)
            for cat in categories:
                cat_item = QTreeWidgetItem(mcu_item)
                cat_item.setText(0, cat)
                cat_item.setData(0, Qt.UserRole, ("category", mcu, cat))

                functions = load_category_functions(self.base_dir, mcu, cat)
                for func_name in functions.keys():
                    func_item = QTreeWidgetItem(cat_item)
                    func_item.setText(0, func_name)
                    func_item.setData(0, Qt.UserRole, ("function", mcu, cat, func_name))

    def on_selection_changed(self):
        """选中项变化时显示函数详情"""
        selected = self.tree.selectedItems()
        if not selected:
            self.detail_text.clear()
            return

        item = selected[0]
        item_data = item.data(0, Qt.UserRole)
        if item_data and item_data[0] == "function":
            mcu, cat, func_name = item_data[1], item_data[2], item_data[3]
            functions = load_category_functions(self.base_dir, mcu, cat)
            self.detail_text.setPlainText(functions.get(func_name, ""))
        else:
            self.detail_text.clear()

    def show_context_menu(self, pos):
        """右键菜单：复制函数名"""
        item = self.tree.itemAt(pos)
        if item and item.data(0, Qt.UserRole) and item.data(0, Qt.UserRole)[0] == "function":
            menu = QMenu()
            copy_action = menu.addAction("复制函数名")
            copy_action.triggered.connect(lambda: pyperclip.copy(item.text(0)))
            menu.exec_(self.tree.mapToGlobal(pos))

    def add_mcu(self):
        """新建单片机文件夹"""
        text, ok = QInputDialog.getText(self, "新建单片机", "输入单片机名称:")
        if ok and text.strip():
            path = os.path.join(self.base_dir, text.strip())
            if not os.path.exists(path):
                os.makedirs(path)
                self.refresh_tree()
                QMessageBox.information(self, "成功", f"已创建单片机文件夹：{text.strip()}")

    def add_category(self):
        """新建分类文件"""
        mcus = get_mcu_folders(self.base_dir)
        if not mcus:
            QMessageBox.warning(self, "警告", "请先创建单片机！")
            return
        mcu, ok1 = QInputDialog.getItem(self, "选择单片机", "所属单片机:", mcus, 0, False)
        if ok1:
            cat, ok2 = QInputDialog.getText(self, "新建分类", "输入分类名称:")
            if ok2 and cat.strip():
                save_category_functions(self.base_dir, mcu, cat.strip(), {})
                self.refresh_tree()
                QMessageBox.information(self, "成功", f"已创建分类文件：{mcu}/{cat.strip()}.json")

    def add_function(self):
        """添加函数到分类文件"""
        mcus = get_mcu_folders(self.base_dir)
        if not mcus:
            QMessageBox.warning(self, "警告", "请先创建单片机！")
            return
        
        mcu, ok1 = QInputDialog.getItem(self, "选择单片机", "所属单片机:", mcus, 0, False)
        if not ok1: return
        
        cats = get_category_files(self.base_dir, mcu)
        if not cats:
            QMessageBox.warning(self, "警告", "请先创建分类！")
            return
            
        
        cat, ok2 = QInputDialog.getItem(self, "选择分类", "所属分类:", cats, 0, False)
        if not ok2: return

        func_name, ok3 = QInputDialog.getText(self, "添加函数", "输入函数名:")
        if ok3 and func_name.strip():
            func_detail, ok4 = QInputDialog.getMultiLineText(self, "添加详情", "输入函数详情:")
            if ok4:
                funcs = load_category_functions(self.base_dir, mcu, cat)
                funcs[func_name.strip()] = func_detail
                save_category_functions(self.base_dir, mcu, cat, funcs)
                self.refresh_tree()
                QMessageBox.information(self, "成功", f"已添加函数到：{mcu}/{cat}.json")

    def closeEvent(self, event):
        """关闭时清理"""
        try:
            keyboard.unhook_all()
            if self.floating_win:
                self.floating_win.close()
        except:
            pass
        event.accept()

# ===================== 工具函数 =====================
def init_base_dir():
    """初始化基础目录"""
    base_dir = "hal_functions"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    return base_dir

def get_mcu_folders(base_dir):
    """获取所有单片机文件夹"""
    return [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]

def get_category_files(base_dir, mcu_name):
    """获取指定单片机下的分类文件"""
    mcu_dir = os.path.join(base_dir, mcu_name)
    if not os.path.exists(mcu_dir):
        return []
    return [f[:-5] for f in os.listdir(mcu_dir) if f.endswith(".json") and os.path.isfile(os.path.join(mcu_dir, f))]

def load_category_functions(base_dir, mcu_name, category):
    """加载指定分类文件中的函数"""
    file_path = os.path.join(base_dir, mcu_name, f"{category}.json")
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_category_functions(base_dir, mcu_name, category, functions):
    """保存函数到分类文件"""
    mcu_dir = os.path.join(base_dir, mcu_name)
    if not os.path.exists(mcu_dir):
        os.makedirs(mcu_dir)
    file_path = os.path.join(mcu_dir, f"{category}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(functions, f, ensure_ascii=False, indent=4)

# ===================== 程序入口 =====================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = HALFunctionBrowser()
    if window.config["enable_floating"]:
        window.hide()
    else:
        window.show()
        
    sys.exit(app.exec_())