import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QMenuBar, QSplitter
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from core import constants
from core.config import load_config
from core.styles import styleSheet
from widgets import LeftPanel, CenterPanel, RightPanel, HeaderWidget, FooterWidget
from dialogs import SettingsDialog, AboutDialog


class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BlastVault")
        self.setMinimumSize(1920, 1080)
        self.setStyleSheet(styleSheet)
        self.setWindowIcon(QIcon(constants.ICON))

        saved_catalogs = load_config()
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.left_panel.restore_catalogs(saved_catalogs)

    def create_widgets(self):
        self.menu_bar = QMenuBar()
        menu_menu = self.menu_bar.addMenu("Menu")
        self.add_catalog_action = menu_menu.addAction("Add Catalog")
        self.remove_catalog_action = menu_menu.addAction("Remove Catalog")

        options_menu = self.menu_bar.addMenu("Options")
        self.settings_action = options_menu.addAction("Settings")
        self.about_action = options_menu.addAction("About")

        self.header_widget = HeaderWidget()

        self.splitter = QSplitter(Qt.Horizontal)
        self.left_panel = LeftPanel()
        self.center_panel = CenterPanel()
        self.right_panel = RightPanel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.center_panel)
        self.splitter.addWidget(self.right_panel)

        self.splitter.setSizes([320, 1295, 305])
        self.splitter.setContentsMargins(0, 0, 0, 0)
        self.splitter.setHandleWidth(2)
        self.splitter.setStretchFactor(0, 20)
        self.splitter.setStretchFactor(1, 65)
        self.splitter.setStretchFactor(2, 15)

        self.footer = FooterWidget()

    def create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setMenuBar(self.menu_bar)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_widget)
        main_layout.addWidget(self.splitter)
        main_layout.addWidget(self.footer)

    def create_connections(self):
        self.about_action.triggered.connect(self.show_about)
        self.settings_action.triggered.connect(self.show_settings)
        self.add_catalog_action.triggered.connect(self.left_panel.add_catalog)
        self.remove_catalog_action.triggered.connect(self.left_panel.remove_catalog)
        self.left_panel.folder_selected.connect(self.on_folder_selected)
        self.center_panel.folder_changed.connect(self.left_panel.sync_to_path)
        self.header_widget.toggle_view.connect(self.center_panel.toggle_view)
        self.header_widget.search_changed.connect(self.center_panel.filter_items)
        self.header_widget.refresh_btn.clicked.connect(self.on_refresh)

    def on_folder_selected(self, path):
        self.header_widget.search_bar.clear()
        self.center_panel.load_folder(path)

    def on_refresh(self):
        if self.center_panel.current_path:
            self.header_widget.search_bar.clear()
            self.center_panel.load_folder(self.center_panel.current_path)

    def show_about(self):
        AboutDialog(self).exec_()

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec_()

    def on_settings_changed(self):
        self.header_widget.update_studio_label(constants.STUDIO_NAME)
        self.left_panel.refresh_all()
        if self.center_panel.current_path:
            self.center_panel.load_folder(self.center_panel.current_path)


if __name__ == "__main__":
    app = QApplication(sys.argv + ['-platform', 'windows:darkmode=1'])
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
