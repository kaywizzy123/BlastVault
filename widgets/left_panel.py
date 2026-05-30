import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu, QDialog
)
from PyQt5.QtCore import Qt, QDir, QEvent, pyqtSignal

from core import constants
from core.config import is_excluded, save_config
from core.styles import context_menu_style
from utils.icons import colored_icon
from dialogs.add_catalog_dialog import AddCatalogDialog
from dialogs.remove_catalog_dialog import RemoveCatalogDialog


class LeftPanel(QWidget):
    folder_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.folder_closed = colored_icon(constants.ACCENT, closed=True)
        self.folder_open = colored_icon(constants.ACCENT_HI, closed=False)
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.tree_widget = QTreeWidget()
        self.tree_widget.header().hide()
        self.tree_widget.setColumnCount(1)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.viewport().installEventFilter(self)

    def create_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.tree_widget)

    def create_connections(self):
        self.tree_widget.itemExpanded.connect(self.on_item_expanded)
        self.tree_widget.itemCollapsed.connect(self.on_item_collapsed)
        self.tree_widget.itemClicked.connect(self.on_item_clicked)
        self.tree_widget.customContextMenuRequested.connect(self.on_context_menu)

    # ------------------------------------------------------------------ #
    #  Collapse / expand all  (Shift + Left Click)                         #
    # ------------------------------------------------------------------ #

    def eventFilter(self, obj, event):
        if obj is self.tree_widget.viewport():
            if (event.type() == QEvent.MouseButtonPress
                    and event.button() == Qt.LeftButton
                    and event.modifiers() & Qt.ShiftModifier):
                item = self.tree_widget.itemAt(event.pos())
                if item:
                    if item.isExpanded():
                        self._collapse_recursive(item)
                    else:
                        self._expand_recursive(item)
                    return True   # consume — don't also fire the normal click
        return super().eventFilter(obj, event)

    def _expand_recursive(self, item):
        """Expand *item* and all its descendants."""
        self.tree_widget.expandItem(item)   # triggers on_item_expanded → loads children
        for i in range(item.childCount()):
            self._expand_recursive(item.child(i))

    def _collapse_recursive(self, item):
        """Collapse *item* and all its descendants."""
        for i in range(item.childCount()):
            self._collapse_recursive(item.child(i))
        self.tree_widget.collapseItem(item)

    def add_catalog(self):
        dialog = AddCatalogDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            for path in dialog.selected_paths:
                self._add_catalog_item(path)
            self.save_catalogs()

    def remove_catalog(self):
        root = self.tree_widget.invisibleRootItem()
        if root.childCount() == 0:
            return
        dialog = RemoveCatalogDialog(root, self.folder_closed, self)
        if dialog.exec_() == QDialog.Accepted:
            for tree_item in dialog.items_to_remove:
                root.removeChild(tree_item)
            self.save_catalogs()

    def refresh_all(self):
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            catalog = root.child(i)
            while catalog.childCount():
                catalog.removeChild(catalog.child(0))
            self.add_children(catalog, catalog.data(0, Qt.UserRole))

    def add_children(self, parent_item, path):
        directory = QDir(path)
        directory.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
        directory.setSorting(QDir.Name)

        for folder in directory.entryInfoList():
            if folder.fileName() == ".meta" or is_excluded(folder.fileName()):
                continue
            child = QTreeWidgetItem(parent_item, [folder.fileName()])
            child.setData(0, Qt.UserRole, folder.absoluteFilePath())
            child.setIcon(0, self.folder_closed)
            if QDir(folder.absoluteFilePath()).entryInfoList(
                QDir.Dirs | QDir.NoDotAndDotDot
            ):
                QTreeWidgetItem(child, [""])

    def on_item_clicked(self, item):
        path = item.data(0, Qt.UserRole)
        if path:
            self.folder_selected.emit(path)

    def sync_to_path(self, path):
        self._find_and_select(self.tree_widget.invisibleRootItem(), path)

    def _find_and_select(self, parent, path):
        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.data(0, Qt.UserRole) == path:
                self.tree_widget.setCurrentItem(item)
                self.tree_widget.scrollToItem(item)
                p = item.parent()
                while p:
                    self.tree_widget.expandItem(p)
                    p = p.parent()
                return True
            if self._find_and_select(item, path):
                return True
        return False

    def on_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet(context_menu_style())

        add_action = menu.addAction("Add Catalog")
        remove_action = None
        if item and item.parent() is None:
            remove_action = menu.addAction("Remove Catalog")

        action = menu.exec_(self.tree_widget.viewport().mapToGlobal(pos))

        if action == add_action:
            self.add_catalog()
        elif remove_action and action == remove_action:
            self.tree_widget.invisibleRootItem().removeChild(item)
            self.save_catalogs()

    def on_item_collapsed(self, item):
        item.setIcon(0, self.folder_closed)

    def on_item_expanded(self, item):
        item.setIcon(0, self.folder_open)
        for i in range(item.childCount()):
            child = item.child(i)
            if child.text(0) == "":
                item.removeChild(child)
                break
        if item.childCount() == 0:
            self.add_children(item, item.data(0, Qt.UserRole))

    def get_catalog_paths(self):
        root = self.tree_widget.invisibleRootItem()
        return [
            root.child(i).data(0, Qt.UserRole)
            for i in range(root.childCount())
        ]

    def save_catalogs(self):
        save_config(catalog_paths=self.get_catalog_paths())

    def _add_catalog_item(self, path):
        if not Path(path).exists():
            return
        root_item = QTreeWidgetItem(self.tree_widget, [QDir(path).dirName()])
        root_item.setData(0, Qt.UserRole, path)
        root_item.setIcon(0, self.folder_closed)
        self.add_children(root_item, path)

    def restore_catalogs(self, paths):
        for path in paths:
            self._add_catalog_item(path)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from core.styles import styleSheet, qt_argv
    from core.config import load_config
    app = QApplication(qt_argv())
    app.setStyle("Fusion")
    app.setStyleSheet(styleSheet)
    w = LeftPanel()
    w.restore_catalogs(load_config())
    w.resize(320, 600)
    w.show()
    sys.exit(app.exec_())

