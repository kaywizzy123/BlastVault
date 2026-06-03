import sys

from .constants import (
    BG, TEXT_PRI, TEXT_SEC, BORDER, ACCENT, ACCENT_HI, SPLITTER_COLOR
)


def qt_argv() -> list:
    """Return sys.argv plus any platform-specific QApplication flags.

    On Windows, appends ``-platform windows:darkmode=1`` so the app
    follows the system dark-mode setting.  On macOS and Linux the flag
    is omitted (those platforms handle dark mode differently).
    """
    args = sys.argv[:]
    if sys.platform == "win32":
        args += ["-platform", "windows:darkmode=1"]
    return args

styleSheet = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT_PRI};
}}
QMenuBar {{
    background-color: {BORDER};
    color: {TEXT_PRI};
}}
QMenuBar::item:selected {{
    background-color: {ACCENT};
}}
QMenu {{
    background-color: {BORDER};
    border: 1px solid {BORDER};
}}
QMenu::item {{
    padding: 6px 20px;
    background-color: transparent;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
    color: {TEXT_PRI};
}}
QSplitter::handle {{
    background-color: {SPLITTER_COLOR};
}}
QSplitter::handle:horizontal {{
    width: 4px;
}}
HeaderWidget {{
    background-color: {BORDER};
    border-bottom: 2px solid {SPLITTER_COLOR};
}}
FooterWidget {{
    background-color: {BORDER};
    border-top: 2px solid {SPLITTER_COLOR};
}}
LeftPanel {{
    background-color: {BG};
}}
CenterPanel {{
    background-color: {BG};
}}
RightPanel {{
    background-color: {BG};
}}
QTreeWidget {{
    background-color: {BG};
    color: {TEXT_PRI};
    border: none;
    outline: none;
}}
QTreeWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTreeWidget::item:hover {{
    background-color: {BORDER};
    color: {TEXT_PRI};
}}
QTreeWidget::item:selected {{
    background-color: {ACCENT};
    color: {TEXT_PRI};
}}
QTreeWidget::branch {{
    background-color: {BG};
}}
QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {{
    image: none;
    border-image: none;
}}
QTreeWidget::branch:open:has-children:!has-siblings,
QTreeWidget::branch:open:has-children:has-siblings {{
    image: none;
    border-image: none;
}}
QHeaderView::section {{
    background-color: {BORDER};
    color: {TEXT_SEC};
    border: none;
    padding: 4px 8px;
}}
QListWidget {{
    background-color: {BG};
    color: {TEXT_PRI};
    border: none;
    outline: none;
}}
QListWidget::item {{
    border: None;
    padding: 2px;
}}
QListWidget::item:hover {{
    background-color: {BORDER};
    border: 2px solid {SPLITTER_COLOR};
    border-radius: 5px;
    padding: 5px;
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    border: 2px solid {SPLITTER_COLOR};
    color: {TEXT_PRI};
    border-radius: 5px;
    padding: 5px;
}}
QScrollBar:vertical {{
    background-color: {BG};
    width: 10px;
    border: 1px solid {SPLITTER_COLOR};
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER};
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {ACCENT};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {BG};
    height: 10px;
    border: 1px solid {SPLITTER_COLOR};
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {ACCENT};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QToolTip {{
    background-color: {BORDER};
    color: {TEXT_PRI};
    border: 1px solid {SPLITTER_COLOR};
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
}}
"""


def header_btn_style():
    return f"""
        QPushButton {{
            background-color: transparent;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {ACCENT};
            border-radius: 4px;
        }}
    """


def context_menu_style():
    return f"""
        QMenu {{
            background-color: {BORDER};
            border: 1px solid {ACCENT};
        }}
        QMenu::item {{
            padding: 6px 20px;
            color: {TEXT_PRI};
        }}
        QMenu::item:selected {{
            background-color: {ACCENT};
        }}
    """


def dialog_list_style():
    return f"""
        QListWidget {{
            background-color: {BORDER};
            color: {TEXT_PRI};
            border: 1px solid {BG};
            border-radius: 4px;
            padding: 4px 5px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 6px 8px;
            border: none;
        }}
        QListWidget::item:hover {{
            background-color: {SPLITTER_COLOR};
        }}
        QListWidget::item:selected {{
            background-color: {ACCENT};
        }}
    """


def input_style():
    return f"""
        QLineEdit {{
            background-color: {BORDER};
            color: {TEXT_SEC};
            border: 1px solid {SPLITTER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QLineEdit:focus {{
            border: 1px solid {ACCENT};
        }}
        QTextEdit {{
            background-color: {BORDER};
            color: {TEXT_SEC};
            border: 1px solid {SPLITTER_COLOR};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QTextEdit:focus {{
            border: 1px solid {ACCENT};
        }}
        QLabel {{
            color: {TEXT_SEC}
        }}
    """
