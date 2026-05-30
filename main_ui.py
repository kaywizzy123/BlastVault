import sys
import time
import hashlib

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QSplitter, QAction,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from core import constants
from core.config import load_config, save_config
from core.styles import styleSheet
from widgets import LeftPanel, CenterPanel, RightPanel, HeaderWidget, FooterWidget
from dialogs import SettingsDialog, AboutDialog, FirstRunDialog


class MainWindow(QMainWindow):
    def __init__(self, parent=None, splash=None):
        super().__init__(parent)
        self._splash = splash

        self.setWindowTitle("BlastVault")
        self.setMinimumSize(900, 600)
        QApplication.instance().setStyleSheet(styleSheet)
        self.setWindowIcon(QIcon(constants.ICON))

        self._splash_update(10, "Loading configuration…")
        is_first_run = not constants.CONFIG_PATH.exists()
        saved_catalogs = load_config()
        if splash:
            splash.set_studio_name(constants.STUDIO_NAME)

        self._splash_update(35, "Building interface…")
        self.create_widgets()

        self._splash_update(60, "Setting up layout…")
        self.create_layout()

        self._splash_update(80, "Connecting signals…")
        self.create_connections()

        self._splash_update(95, "Restoring catalogs…")
        self.left_panel.restore_catalogs(saved_catalogs)

        self._splash_update(100, "Ready!")
        # Prune stale thumbnail cache entries 5 s after startup (background)
        QTimer.singleShot(5000, self._prune_thumb_cache)
        if is_first_run:
            dlg = FirstRunDialog(self)
            dlg.exec_()
            # Reflect any name the user just entered in the header immediately
            self.header_widget.update_studio_label(constants.STUDIO_NAME)

    def _splash_update(self, value: int, message: str) -> None:
        """Forward progress update to the splash screen if one is active."""
        if self._splash:
            self._splash.set_progress(value, message)

    def create_widgets(self):
        # Use QMainWindow's built-in menuBar() — correctly integrated on every platform.
        # Roles must be set before the window is shown so macOS processes them on startup.
        mb = self.menuBar()

        menu_menu = mb.addMenu("Menu")
        self.add_catalog_action = menu_menu.addAction("Add Catalog")
        self.remove_catalog_action = menu_menu.addAction("Remove Catalog")

        options_menu = mb.addMenu("Options")
        self.settings_action = options_menu.addAction("Settings")
        self.about_action    = options_menu.addAction("About")

        # NoRole: keep these items exactly where they are — stops macOS from
        # pulling them into the application menu and emptying the Options menu.
        self.settings_action.setMenuRole(QAction.NoRole)
        self.about_action.setMenuRole(QAction.NoRole)

        self.header_widget = HeaderWidget()

        self.splitter = QSplitter(Qt.Horizontal)
        self.left_panel   = LeftPanel()
        self.center_panel = CenterPanel()
        self.right_panel  = RightPanel()

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
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_widget)
        main_layout.addWidget(self.splitter)
        main_layout.addWidget(self.footer)
        self.setCentralWidget(central)

    def create_connections(self):
        self.about_action.triggered.connect(self.show_about)
        self.settings_action.triggered.connect(self.show_settings)
        self.add_catalog_action.triggered.connect(self.left_panel.add_catalog)
        self.remove_catalog_action.triggered.connect(self.left_panel.remove_catalog)
        self.left_panel.folder_selected.connect(self.on_folder_selected)
        self.center_panel.folder_changed.connect(self.left_panel.sync_to_path)
        self.header_widget.toggle_view.connect(self.center_panel.toggle_view)
        self.header_widget.search_changed.connect(self.center_panel.filter_items)
        self.header_widget.department_changed.connect(self.center_panel.filter_department)
        self.header_widget.artist_changed.connect(self.center_panel.filter_artist)
        self.center_panel.artists_found.connect(self.on_artists_found)
        self.header_widget.refresh_btn.clicked.connect(self.on_refresh)
        self.header_widget.thumb_size_changed.connect(self.center_panel.set_thumb_size)
        self.header_widget.sort_changed.connect(self.center_panel.sort_items)
        self.center_panel.items_loaded.connect(self.footer.update_items)
        self.center_panel.selection_changed.connect(self.footer.update_selection)
        self.center_panel.file_selected.connect(self.right_panel.display_metadata)
        self.center_panel.seq_item_selected.connect(self.right_panel.set_seq_mode)
        self.right_panel.status_changed.connect(self.center_panel.update_item_status)
        self.header_widget.lock_toggled.connect(self._on_lock_toggled)
        # Apply initial locked state to both panels
        self.center_panel.set_status_locked(True)
        self.right_panel.set_status_locked(True)
        self.center_panel.filters_cleared.connect(self.on_filters_cleared)
        self.header_widget.status_changed.connect(self.center_panel.filter_status)

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

    def on_filters_cleared(self):
        """Reset all header filter controls to their default 'All'/empty state."""
        self.header_widget.search_bar.blockSignals(True)
        self.header_widget.search_bar.clear()
        self.header_widget.search_bar.blockSignals(False)

        self.header_widget.department_filter_combobox.blockSignals(True)
        self.header_widget.department_filter_combobox.setCurrentIndex(0)
        self.header_widget.department_filter_combobox.blockSignals(False)

        self.header_widget.artist_filter_combobox.blockSignals(True)
        self.header_widget.artist_filter_combobox.setCurrentIndex(0)
        self.header_widget.artist_filter_combobox.blockSignals(False)

        self.header_widget.status_filter_combobox.blockSignals(True)
        self.header_widget.status_filter_combobox.setCurrentIndex(0)
        self.header_widget.status_filter_combobox.blockSignals(False)

    def on_artists_found(self, artists: list):
        """Called every time a folder finishes loading.

        - Appends newly discovered artist tokens to ``constants.ARTISTS`` in
          discovery order (no re-sort — preserves user-defined order from Settings).
        - Always refreshes the artist combobox so it updates immediately in
          the current session.
        """
        new = [a for a in artists if a and a not in constants.ARTISTS]
        if new:
            constants.ARTISTS.extend(new)
            save_config()
        # Refresh combobox on every load — new artists or not
        self.header_widget.reload_artists()

    def closeEvent(self, event):
        """Save window geometry and splitter state before closing."""
        constants.SPLITTER_SIZES   = self.splitter.sizes()
        constants.WINDOW_MAXIMIZED = self.isMaximized()
        if not self.isMaximized():
            geo = self.geometry()
            constants.WINDOW_GEOMETRY = (geo.x(), geo.y(), geo.width(), geo.height())
        save_config()
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    #  Admin lock                                                          #
    # ------------------------------------------------------------------ #

    def _on_lock_toggled(self, locked: bool):
        """Called when the padlock button is clicked.

        *locked = True*  → user wants to re-lock (no PIN needed).
        *locked = False* → user wants to unlock (PIN required).
        """
        if locked:
            constants.STATUS_LOCKED = True
            self.header_widget.set_locked(True)
            self.center_panel.set_status_locked(True)
            self.right_panel.set_status_locked(True)
        else:
            self._try_unlock()

    def _try_unlock(self):
        """Show PIN dialog; unlock only if the correct PIN is entered."""
        from dialogs.pin_dialog import PinInputDialog, PinSetupDialog

        if not constants.ADMIN_PIN_HASH:
            # ── First time: no PIN set yet ──────────────────────────────
            dlg = PinSetupDialog(self)
            pin, ok = dlg.get_pin()
            if not ok or not pin:
                self.header_widget.set_locked(True)
                return
            constants.ADMIN_PIN_HASH = hashlib.sha256(pin.encode()).hexdigest()
            save_config()

        else:
            # ── Verify existing PIN ─────────────────────────────────────
            def _verify(pin: str) -> bool:
                return hashlib.sha256(pin.encode()).hexdigest() == constants.ADMIN_PIN_HASH

            dlg = PinInputDialog(verify_fn=_verify, parent=self)
            pin, ok = dlg.get_pin()
            if not ok:
                self.header_widget.set_locked(True)
                return

        # ── PIN verified (or freshly created) — unlock ──────────────────
        constants.STATUS_LOCKED = False
        self.header_widget.set_locked(False)
        self.center_panel.set_status_locked(False)
        self.right_panel.set_status_locked(False)

    def _prune_thumb_cache(self):
        """Prune old thumbnail cache entries in a daemon background thread."""
        import threading
        from utils.icons import prune_thumbnail_cache
        threading.Thread(target=prune_thumbnail_cache, daemon=True).start()

    def on_settings_changed(self):
        self.header_widget.update_studio_label(constants.STUDIO_NAME)
        self.header_widget.reload_departments()
        self.header_widget.reload_artists()
        self.left_panel.refresh_all()
        if self.center_panel.current_path:
            self.center_panel.load_folder(self.center_panel.current_path)


if __name__ == "__main__":
    from core.styles import qt_argv
    from widgets.splash_screen import SplashScreen

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(qt_argv())
    app.setStyle("Fusion")

    splash = SplashScreen()
    splash.show()
    QApplication.processEvents()
    _start = time.monotonic()

    window = MainWindow(splash=splash)

    # Ensure splash is visible for at least MIN_DISPLAY_MS
    elapsed_ms  = int((time.monotonic() - _start) * 1000)
    remaining_ms = max(0, SplashScreen.MIN_DISPLAY_MS - elapsed_ms)

    def _finish():
        splash.close()
        if constants.SPLITTER_SIZES:
            window.splitter.setSizes(constants.SPLITTER_SIZES)
        if not constants.WINDOW_MAXIMIZED and constants.WINDOW_GEOMETRY:
            x, y, w, h = constants.WINDOW_GEOMETRY
            window.setGeometry(x, y, w, h)
            window.show()
        else:
            window.showMaximized()

    QTimer.singleShot(remaining_ms, _finish)
    sys.exit(app.exec_())
