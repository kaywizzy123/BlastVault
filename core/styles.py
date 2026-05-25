from .constants import (
    BG, TEXT_PRI, TEXT_SEC, BORDER, ACCENT, ACCENT_HI, SPLITTER_COLOR
)

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
    border: none;
    padding: 2px;
}}
QListWidget::item:hover {{
    background-color: {BORDER};
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
    color: {TEXT_PRI};
}}
QScrollBar:vertical {{
    background-color: {BG};
    width: 8px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER};
    border-radius: 4px;
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
    height: 8px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    border-radius: 4px;
    min-width: 20px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {ACCENT};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
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
            color: {TEXT_PRI};
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QLineEdit:focus {{
            border: 1px solid {ACCENT};
        }}
    """
