import sys
import os
import string
import subprocess
import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QMenu,
    QProgressBar,
    QAbstractItemView,
    QHeaderView,
)

from send2trash import send2trash

from file_searcher import FileSearchEngine
from duplicate_finder import DuplicateFinder
from icon_generator import create_icon


# ============================================================
# Resource Path
# ============================================================

def resource_path(filename):
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / filename

    return Path(__file__).parent / filename


# ============================================================
# Ensure Icon Exists
# ============================================================

def ensure_icon():

    icon_path = resource_path("icon.ico")

    if not icon_path.exists():

        try:
            create_icon(icon_path)
        except Exception:
            pass

    return icon_path


# ============================================================
# File Search Worker
# ============================================================

class FileSearchWorker(QThread):

    results_found = Signal(object)

    progress = Signal(
        int,
        int,
        str,
    )

    finished = Signal(
        int,
        int,
    )

    error = Signal(str)

    def __init__(
        self,
        engine,
        roots,
        query,
        extensions,
    ):

        super().__init__()

        self.engine = engine
        self.roots = roots
        self.query = query
        self.extensions = extensions

    def run(self):

        try:

            scanned, found = self.engine.search(
                roots=self.roots,
                query=self.query,
                extensions=self.extensions,
                result_callback=self.send_results,
                progress_callback=self.send_progress,
            )

            self.finished.emit(
                scanned,
                found,
            )

        except Exception as e:

            self.error.emit(str(e))

    def send_results(self, results):

        self.results_found.emit(results)

    def send_progress(
        self,
        scanned,
        found,
        current_path,
    ):

        self.progress.emit(
            scanned,
            found,
            current_path,
        )


# ============================================================
# Duplicate Worker
# ============================================================

class DuplicateWorker(QThread):

    duplicate_found = Signal(
        str,
        object,
    )

    progress = Signal(
        int,
        int,
        str,
    )

    finished = Signal()

    error = Signal(str)

    def __init__(
        self,
        finder,
        roots,
        mode,
    ):

        super().__init__()

        self.finder = finder
        self.roots = roots
        self.mode = mode

    def run(self):

        try:

            if self.mode == "name":

                self.finder.find_by_name(
                    self.roots,
                    result_callback=self.send_duplicate,
                    progress_callback=self.send_progress,
                )

            elif self.mode == "quick":

                self.finder.find_quick(
                    self.roots,
                    result_callback=self.send_duplicate,
                    progress_callback=self.send_progress,
                )

            else:

                self.finder.find_hash(
                    self.roots,
                    result_callback=self.send_duplicate,
                    progress_callback=self.send_progress,
                )

            self.finished.emit()

        except Exception as e:

            self.error.emit(str(e))

    def send_duplicate(
        self,
        key,
        files,
    ):

        self.duplicate_found.emit(
            key,
            files,
        )

    def send_progress(
        self,
        current,
        found,
        message,
    ):

        self.progress.emit(
            current,
            found,
            message,
        )


# ============================================================
# Main Application
# ============================================================

class SmartFileFinder(QWidget):

    def __init__(self):

        super().__init__()

        # ----------------------------------------------------
        # Window
        # ----------------------------------------------------

        self.setWindowTitle(
            "Smart File Finder"
        )

        self.resize(
            470,
            530,
        )

        self.setMinimumSize(
            470,
            530,
        )

        # ----------------------------------------------------
        # Icon
        # ----------------------------------------------------

        icon_path = ensure_icon()

        if icon_path.exists():

            self.setWindowIcon(
                QIcon(str(icon_path))
            )

        # ----------------------------------------------------
        # Engines
        # ----------------------------------------------------

        self.search_engine = FileSearchEngine()

        self.duplicate_finder = DuplicateFinder()

        self.search_worker = None

        self.duplicate_worker = None

        # ----------------------------------------------------
        # Duplicate Groups
        #
        # key -> QTreeWidgetItem
        # ----------------------------------------------------

        self.duplicate_items = {}

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.setup_ui()

        self.apply_style()

    # ========================================================
    # Setup UI
    # ========================================================

    def setup_ui(self):

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )

        main_layout.setSpacing(7)

        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------

        title = QLabel(
            "Smart File Finder"
        )

        title.setObjectName(
            "title"
        )

        subtitle = QLabel(
            "Fast Search • Live Results • Duplicate Detection"
        )

        subtitle.setObjectName(
            "subtitle"
        )

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # ----------------------------------------------------
        # Tabs
        # ----------------------------------------------------

        self.tabs = QTabWidget()

        main_layout.addWidget(
            self.tabs,
            1,
        )

        self.setup_search_tab()

        self.setup_duplicate_tab()

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        self.status = QLabel(
            "Ready"
        )

        self.status.setObjectName(
            "status"
        )

        self.status.setWordWrap(True)

        main_layout.addWidget(
            self.status
        )

        # ----------------------------------------------------
        # Developer Footer
        # ----------------------------------------------------

        developer_footer = QLabel(
            "Developed by: Md. Shakil Hossain  |  "
            "Email: shakil.hossain2417@gmail.com"
        )

        developer_footer.setObjectName(
            "developer_footer"
        )

        developer_footer.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        developer_footer.setWordWrap(True)

        main_layout.addWidget(
            developer_footer
        )

    # ========================================================
    # File Search Tab
    # ========================================================

    def setup_search_tab(self):

        tab = QWidget()

        layout = QVBoxLayout(tab)

        layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        layout.setSpacing(6)

        self.tabs.addTab(
            tab,
            "🔎 Search",
        )

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        location_row = QHBoxLayout()

        self.search_scope = QComboBox()

        self.search_scope.addItems([
            "Browse",
            "All Drives",
        ])

        self.search_scope.currentTextChanged.connect(
            self.search_scope_changed
        )

        self.search_path = QLineEdit()

        self.search_path.setPlaceholderText(
            "Select folder or drive..."
        )

        self.search_browse_button = QPushButton(
            "Browse"
        )

        self.search_browse_button.clicked.connect(
            self.browse_search_location
        )

        location_row.addWidget(
            self.search_scope
        )

        location_row.addWidget(
            self.search_path,
            1,
        )

        location_row.addWidget(
            self.search_browse_button
        )

        layout.addLayout(
            location_row
        )

        # ----------------------------------------------------
        # Search Input
        # ----------------------------------------------------

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Search file name..."
        )

        self.search_input.returnPressed.connect(
            self.start_file_search
        )

        layout.addWidget(
            self.search_input
        )

        # ----------------------------------------------------
        # Extension Filter
        # ----------------------------------------------------

        extension_row = QHBoxLayout()

        self.extension_filter = QComboBox()

        self.extension_filter.addItems([
            "All Files",
            "Documents",
            "Images",
            "Videos",
            "Audio",
            "Archives",
            "Programs",
            "Custom",
        ])

        self.extension_filter.currentTextChanged.connect(
            self.extension_changed
        )

        self.custom_extension = QLineEdit()

        self.custom_extension.setPlaceholderText(
            ".pdf,.txt,.jpg"
        )

        self.custom_extension.setEnabled(
            False
        )

        extension_row.addWidget(
            self.extension_filter
        )

        extension_row.addWidget(
            self.custom_extension,
            1,
        )

        layout.addLayout(
            extension_row
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        button_row = QHBoxLayout()

        self.search_button = QPushButton(
            "⚡ Search"
        )

        self.search_button.clicked.connect(
            self.start_file_search
        )

        self.stop_search_button = QPushButton(
            "Stop"
        )

        self.stop_search_button.setEnabled(
            False
        )

        self.stop_search_button.clicked.connect(
            self.stop_file_search
        )

        button_row.addWidget(
            self.search_button
        )

        button_row.addWidget(
            self.stop_search_button
        )

        layout.addLayout(
            button_row
        )

        # ----------------------------------------------------
        # Results
        # ----------------------------------------------------

        self.search_results = QTreeWidget()

        self.search_results.setHeaderLabels([
            "Name",
            "Location",
            "Size",
        ])

        self.search_results.setRootIsDecorated(
            False
        )

        self.search_results.setAlternatingRowColors(
            True
        )

        self.search_results.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.search_results.itemDoubleClicked.connect(
            self.open_search_item
        )

        self.search_results.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.search_results.customContextMenuRequested.connect(
            self.search_menu
        )

        header = self.search_results.header()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(
            self.search_results,
            1,
        )

    # ========================================================
    # Duplicate Tab
    # ========================================================

    def setup_duplicate_tab(self):

        tab = QWidget()

        layout = QVBoxLayout(tab)

        layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        layout.setSpacing(6)

        self.tabs.addTab(
            tab,
            "♻ Duplicates",
        )

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        location_row = QHBoxLayout()

        self.duplicate_scope = QComboBox()

        self.duplicate_scope.addItems([
            "Browse",
            "All Drives",
        ])

        self.duplicate_scope.currentTextChanged.connect(
            self.duplicate_scope_changed
        )

        self.duplicate_path = QLineEdit()

        self.duplicate_path.setPlaceholderText(
            "Select folder or drive..."
        )

        self.duplicate_browse_button = QPushButton(
            "Browse"
        )

        self.duplicate_browse_button.clicked.connect(
            self.browse_duplicate_location
        )

        location_row.addWidget(
            self.duplicate_scope
        )

        location_row.addWidget(
            self.duplicate_path,
            1,
        )

        location_row.addWidget(
            self.duplicate_browse_button
        )

        layout.addLayout(
            location_row
        )

        # ----------------------------------------------------
        # Mode
        # ----------------------------------------------------

        self.duplicate_mode = QComboBox()

        self.duplicate_mode.addItem(
            "⚡ Name Search — Fastest",
            "name",
        )

        self.duplicate_mode.addItem(
            "🚀 Quick Search",
            "quick",
        )

        self.duplicate_mode.addItem(
            "🔐 Hash Search — Exact",
            "hash",
        )

        layout.addWidget(
            self.duplicate_mode
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        button_row = QHBoxLayout()

        self.duplicate_button = QPushButton(
            "Find Duplicates"
        )

        self.duplicate_button.clicked.connect(
            self.start_duplicate_search
        )

        self.stop_duplicate_button = QPushButton(
            "Stop"
        )

        self.stop_duplicate_button.setEnabled(
            False
        )

        self.stop_duplicate_button.clicked.connect(
            self.stop_duplicate_search
        )

        button_row.addWidget(
            self.duplicate_button
        )

        button_row.addWidget(
            self.stop_duplicate_button
        )

        layout.addLayout(
            button_row
        )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        self.progress = QProgressBar()

        self.progress.setRange(
            0,
            0,
        )

        self.progress.setTextVisible(
            False
        )

        self.progress.setVisible(
            False
        )

        layout.addWidget(
            self.progress
        )

        # ----------------------------------------------------
        # Results
        # ----------------------------------------------------

        self.duplicate_results = QTreeWidget()

        self.duplicate_results.setHeaderLabels([
            "Duplicate",
            "Location",
            "Size",
        ])

        self.duplicate_results.setAlternatingRowColors(
            True
        )

        self.duplicate_results.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.duplicate_results.itemDoubleClicked.connect(
            self.open_duplicate_item
        )

        self.duplicate_results.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.duplicate_results.customContextMenuRequested.connect(
            self.duplicate_menu
        )

        header = self.duplicate_results.header()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        layout.addWidget(
            self.duplicate_results,
            1,
        )

        # ----------------------------------------------------
        # ONLY 3 Selection Buttons
        # ----------------------------------------------------

        selection_layout = QHBoxLayout()

        self.select_all_duplicates_button = QPushButton(
            "Select All Duplicate Files"
        )

        self.select_all_duplicates_button.clicked.connect(
            self.select_all_duplicate_files
        )

        self.clear_duplicate_selection_button = QPushButton(
            "Clear Selection"
        )

        self.clear_duplicate_selection_button.clicked.connect(
            self.clear_duplicate_selection
        )

        self.delete_duplicates_button = QPushButton(
            "🗑 Delete"
        )

        self.delete_duplicates_button.clicked.connect(
            self.delete_selected_duplicates
        )

        selection_layout.addWidget(
            self.select_all_duplicates_button
        )

        selection_layout.addWidget(
            self.clear_duplicate_selection_button
        )

        selection_layout.addWidget(
            self.delete_duplicates_button
        )

        layout.addLayout(
            selection_layout
        )

    # ========================================================
    # Style
    # ========================================================

    def apply_style(self):

        self.setStyleSheet("""
            QWidget {
                background-color: #f6f7fb;
                color: #1f2937;
                font-family: "Segoe UI";
                font-size: 12px;
            }

            QLabel#title {
                font-size: 21px;
                font-weight: 700;
                color: #111827;
                background: transparent;
            }

            QLabel#subtitle {
                font-size: 11px;
                color: #6b7280;
                background: transparent;
            }

            QLabel#status {
                font-size: 10px;
                color: #4b5563;
                background: transparent;
            }

            QLabel#developer_footer {
                font-size: 10px;
                color: #6b7280;
                background: transparent;
                padding-top: 4px;
            }

            QLineEdit,
            QComboBox {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 6px;
                min-height: 16px;
            }

            QLineEdit:focus,
            QComboBox:focus {
                border: 2px solid #2563eb;
            }

            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 10px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton:pressed {
                background-color: #1e40af;
            }

            QPushButton:disabled {
                background-color: #9ca3af;
            }

            QTabWidget::pane {
                border: 1px solid #d1d5db;
                background: white;
            }

            QTabBar::tab {
                background: #e5e7eb;
                color: #374151;
                padding: 7px 10px;
                margin-right: 2px;
            }

            QTabBar::tab:selected {
                background: white;
                color: #2563eb;
                font-weight: 700;
            }

            QTreeWidget {
                background: white;
                border: 1px solid #d1d5db;
                border-radius: 5px;
                alternate-background-color: #f9fafb;
            }

            QTreeWidget::item {
                padding: 4px;
                color: #111827;
            }

            QTreeWidget::item:selected {
                background: #bfdbfe;
                color: #111827;
            }

            QHeaderView::section {
                background: #f3f4f6;
                color: #374151;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #d1d5db;
                font-weight: 700;
            }

            QProgressBar {
                border: 1px solid #d1d5db;
                border-radius: 5px;
                background: white;
            }

            QProgressBar::chunk {
                background: #2563eb;
            }

            QMenu {
                background: white;
                border: 1px solid #d1d5db;
            }

            QMenu::item {
                padding: 7px 22px;
                color: #111827;
            }

            QMenu::item:selected {
                background: #dbeafe;
            }
        """)

    # ========================================================
    # Search Scope
    # ========================================================

    def search_scope_changed(self, mode):

        if mode == "All Drives":

            self.search_path.setText(
                "All available drives"
            )

            self.search_path.setEnabled(
                False
            )

            self.search_browse_button.setEnabled(
                False
            )

        else:

            self.search_path.clear()

            self.search_path.setEnabled(
                True
            )

            self.search_browse_button.setEnabled(
                True
            )

    # ========================================================
    # Duplicate Scope
    # ========================================================

    def duplicate_scope_changed(self, mode):

        if mode == "All Drives":

            self.duplicate_path.setText(
                "All available drives"
            )

            self.duplicate_path.setEnabled(
                False
            )

            self.duplicate_browse_button.setEnabled(
                False
            )

        else:

            self.duplicate_path.clear()

            self.duplicate_path.setEnabled(
                True
            )

            self.duplicate_browse_button.setEnabled(
                True
            )

    # ========================================================
    # Browse Search
    # ========================================================

    def browse_search_location(self):

        path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder or Drive",
        )

        if path:

            path = os.path.normpath(path)

            self.search_path.setText(
                path
            )

            self.status.setText(
                f"Selected: {path}"
            )

    # ========================================================
    # Browse Duplicate
    # ========================================================

    def browse_duplicate_location(self):

        path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder or Drive",
        )

        if path:

            path = os.path.normpath(path)

            self.duplicate_path.setText(
                path
            )

            self.status.setText(
                f"Selected: {path}"
            )

    # ========================================================
    # Extension
    # ========================================================

    def extension_changed(self, value):

        self.custom_extension.setEnabled(
            value == "Custom"
        )

    def get_extensions(self):

        category = self.extension_filter.currentText()

        mapping = {

            "Documents": {
                ".pdf",
                ".doc",
                ".docx",
                ".txt",
                ".xlsx",
                ".xls",
                ".ppt",
                ".pptx",
                ".csv",
            },

            "Images": {
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".webp",
                ".bmp",
            },

            "Videos": {
                ".mp4",
                ".mkv",
                ".avi",
                ".mov",
                ".wmv",
            },

            "Audio": {
                ".mp3",
                ".wav",
                ".flac",
                ".aac",
                ".m4a",
            },

            "Archives": {
                ".zip",
                ".rar",
                ".7z",
                ".tar",
                ".gz",
            },

            "Programs": {
                ".exe",
                ".msi",
                ".bat",
                ".cmd",
            },
        }

        if category == "All Files":

            return set()

        if category == "Custom":

            extensions = set()

            for ext in self.custom_extension.text().split(","):

                ext = ext.strip().lower()

                if not ext:
                    continue

                if not ext.startswith("."):
                    ext = "." + ext

                extensions.add(ext)

            return extensions

        return mapping.get(
            category,
            set(),
        )

    # ========================================================
    # Drives
    # ========================================================

    def get_drives(self):

        drives = []

        for letter in string.ascii_uppercase:

            drive = f"{letter}:\\"

            if os.path.exists(drive):

                drives.append(drive)

        return drives

    # ========================================================
    # Search Roots
    # ========================================================

    def get_search_roots(self):

        if self.search_scope.currentText() == "All Drives":

            return self.get_drives()

        path = self.search_path.text().strip()

        if not path or not os.path.exists(path):

            return []

        return [path]

    # ========================================================
    # Duplicate Roots
    # ========================================================

    def get_duplicate_roots(self):

        if self.duplicate_scope.currentText() == "All Drives":

            return self.get_drives()

        path = self.duplicate_path.text().strip()

        if not path or not os.path.exists(path):

            return []

        return [path]

    # ========================================================
    # Start Search
    # ========================================================

    def start_file_search(self):

        roots = self.get_search_roots()

        if not roots:

            QMessageBox.warning(
                self,
                "Location Required",
                "Please select a valid folder or choose All Drives.",
            )

            return

        query = self.search_input.text().strip()

        extensions = self.get_extensions()

        self.search_results.clear()

        self.search_engine.reset()

        self.search_button.setEnabled(
            False
        )

        self.stop_search_button.setEnabled(
            True
        )

        self.status.setText(
            "Starting realtime search..."
        )

        self.search_worker = FileSearchWorker(
            self.search_engine,
            roots,
            query,
            extensions,
        )

        self.search_worker.results_found.connect(
            self.add_search_results
        )

        self.search_worker.progress.connect(
            self.search_progress
        )

        self.search_worker.finished.connect(
            self.search_finished
        )

        self.search_worker.error.connect(
            self.worker_error
        )

        self.search_worker.start()

    # ========================================================
    # Stop Search
    # ========================================================

    def stop_file_search(self):

        self.search_engine.stop()

        self.status.setText(
            "Stopping search..."
        )

    # ========================================================
    # Add Live Search Results
    # ========================================================

    def add_search_results(self, results):

        items = []

        for result in results:

            item = QTreeWidgetItem([
                result["name"],
                result["path"],
                self.format_size(
                    result["size"]
                ),
            ])

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                result["path"],
            )

            items.append(item)

        self.search_results.addTopLevelItems(
            items
        )

    # ========================================================
    # Live Search Progress
    # ========================================================

    def search_progress(
        self,
        scanned,
        found,
        current_path,
    ):

        short_path = current_path

        if len(short_path) > 60:

            short_path = (
                "..."
                + short_path[-57:]
            )

        self.status.setText(
            f"Scanning: {short_path}\n"
            f"Scanned: {scanned:,} | "
            f"Found: {found:,}"
        )

    # ========================================================
    # Search Finished
    # ========================================================

    def search_finished(
        self,
        scanned,
        found,
    ):

        self.search_button.setEnabled(
            True
        )

        self.stop_search_button.setEnabled(
            False
        )

        self.status.setText(
            f"Finished | "
            f"Scanned: {scanned:,} | "
            f"Found: {found:,}"
        )

    # ========================================================
    # Open Search Item
    # ========================================================

    def open_search_item(
        self,
        item,
        column,
    ):

        path = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        self.open_file(path)

    # ========================================================
    # Search Context Menu
    # ========================================================

    def search_menu(self, position):

        item = self.search_results.itemAt(
            position
        )

        if not item:
            return

        path = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        self.show_file_menu(
            position,
            path,
            self.search_results,
        )

    # ========================================================
    # Start Duplicate Search
    # ========================================================

    def start_duplicate_search(self):

        roots = self.get_duplicate_roots()

        if not roots:

            QMessageBox.warning(
                self,
                "Location Required",
                "Please select a valid folder or choose All Drives.",
            )

            return

        self.duplicate_results.clear()

        self.duplicate_items.clear()

        self.duplicate_finder.reset()

        self.duplicate_button.setEnabled(
            False
        )

        self.stop_duplicate_button.setEnabled(
            True
        )

        self.progress.setVisible(
            True
        )

        self.status.setText(
            "Searching duplicates..."
        )

        mode = self.duplicate_mode.currentData()

        self.duplicate_worker = DuplicateWorker(
            self.duplicate_finder,
            roots,
            mode,
        )

        self.duplicate_worker.duplicate_found.connect(
            self.update_duplicate_group
        )

        self.duplicate_worker.progress.connect(
            self.duplicate_progress
        )

        self.duplicate_worker.finished.connect(
            self.duplicate_finished
        )

        self.duplicate_worker.error.connect(
            self.worker_error
        )

        self.duplicate_worker.start()

    # ========================================================
    # Stop Duplicate Search
    # ========================================================

    def stop_duplicate_search(self):

        self.duplicate_finder.stop()

        self.status.setText(
            "Stopping duplicate search..."
        )

    # ========================================================
    # Live Duplicate Results
    # ========================================================

    def update_duplicate_group(
        self,
        key,
        files,
    ):

        if key in self.duplicate_items:

            parent = self.duplicate_items[key]

            parent.takeChildren()

        else:

            parent = QTreeWidgetItem([
                "",
                "",
                "",
            ])

            self.duplicate_results.addTopLevelItem(
                parent
            )

            self.duplicate_items[key] = parent

        parent.setText(
            0,
            f"Duplicate ({len(files)} files)",
        )

        # ----------------------------------------------------
        # Add actual file children
        # ----------------------------------------------------

        for info in files:

            child = QTreeWidgetItem([
                info["name"],
                info["path"],
                self.format_size(
                    info["size"]
                ),
            ])

            child.setData(
                0,
                Qt.ItemDataRole.UserRole,
                info["path"],
            )

            # Store file information directly on item.
            # This is safe and avoids .get() error.
            child.setData(
                0,
                Qt.ItemDataRole.UserRole + 1,
                info,
            )

            parent.addChild(
                child
            )

        parent.setExpanded(
            True
        )

    # ========================================================
    # Duplicate Progress
    # ========================================================

    def duplicate_progress(
        self,
        current,
        found,
        message,
    ):

        self.status.setText(
            f"{message}\n"
            f"Processed: {current:,} | "
            f"Groups: {found:,}"
        )

    # ========================================================
    # Duplicate Finished
    # ========================================================

    def duplicate_finished(self):

        self.duplicate_button.setEnabled(
            True
        )

        self.stop_duplicate_button.setEnabled(
            False
        )

        self.progress.setVisible(
            False
        )

        groups = len(
            self.duplicate_items
        )

        self.status.setText(
            f"Finished | "
            f"{groups} duplicate group(s)"
        )

    # ========================================================
    # Open Duplicate Item
    # ========================================================

    def open_duplicate_item(
        self,
        item,
        column,
    ):

        path = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if path:

            self.open_file(path)

    # ========================================================
    # Duplicate Context Menu
    # ========================================================

    def duplicate_menu(self, position):

        item = self.duplicate_results.itemAt(
            position
        )

        if not item:
            return

        path = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if not path:
            return

        self.show_file_menu(
            position,
            path,
            self.duplicate_results,
        )

    # ========================================================
    # File Context Menu
    # ========================================================

    def show_file_menu(
        self,
        position,
        path,
        widget,
    ):

        menu = QMenu(self)

        open_action = menu.addAction(
            "Open"
        )

        location_action = menu.addAction(
            "Open Location"
        )

        copy_action = menu.addAction(
            "Copy Path"
        )

        menu.addSeparator()

        delete_action = menu.addAction(
            "Delete"
        )

        action = menu.exec(
            widget.viewport().mapToGlobal(
                position
            )
        )

        if action == open_action:

            self.open_file(path)

        elif action == location_action:

            self.open_location(path)

        elif action == copy_action:

            QApplication.clipboard().setText(
                path
            )

            self.status.setText(
                "Path copied"
            )

        elif action == delete_action:

            self.delete_file(path)

    # ========================================================
    # Open File
    # ========================================================

    def open_file(self, path):

        if not path:
            return

        if not os.path.exists(path):

            QMessageBox.warning(
                self,
                "File Not Found",
                "This file no longer exists.",
            )

            return

        try:

            os.startfile(path)

        except Exception as e:

            QMessageBox.warning(
                self,
                "Open Failed",
                str(e),
            )

    # ========================================================
    # Open Location
    # ========================================================

    def open_location(self, path):

        if not path:
            return

        if not os.path.exists(path):

            QMessageBox.warning(
                self,
                "File Not Found",
                "This file no longer exists.",
            )

            return

        try:

            subprocess.Popen([
                "explorer.exe",
                "/select,",
                os.path.normpath(path),
            ])

        except Exception as e:

            QMessageBox.warning(
                self,
                "Open Location Failed",
                str(e),
            )

    # ========================================================
    # Delete One File
    # ========================================================

    def delete_file(self, path):

        if not path:
            return

        if not os.path.exists(path):
            return

        answer = QMessageBox.question(
            self,
            "Delete File",
            f"Move this file to Recycle Bin?\n\n{path}",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:

            send2trash(path)

            self.status.setText(
                "File moved to Recycle Bin"
            )

        except Exception as e:

            QMessageBox.warning(
                self,
                "Delete Failed",
                str(e),
            )

    # ========================================================
    # Normalize Filename For Duplicate Detection
    # ========================================================

    @staticmethod
    def normalize_duplicate_name(filename):

        stem = Path(filename).stem

        # Lowercase
        name = stem.lower().strip()

        # ----------------------------------------------------
        # Remove common Windows duplicate suffixes
        #
        # file (1)
        # file (2)
        # file - Copy
        # file - Copy (1)
        # file_copy
        # file copy
        # file.1
        # file.2
        # file.copy
        # file.1.copy
        # ----------------------------------------------------

        patterns = [

            # "file - Copy (1)"
            r"\s*-\s*copy\s*\(\d+\)\s*$",

            # "file - Copy"
            r"\s*-\s*copy\s*$",

            # "file Copy (1)"
            r"\s+copy\s*\(\d+\)\s*$",

            # "file Copy"
            r"\s+copy\s*$",

            # "file_copy_1"
            r"[_\-\s]+copy[_\-\s]*\d*\s*$",

            # "file.copy"
            r"\.copy\s*$",

            # "file.copy.1"
            r"\.copy(?:\.\d+)?\s*$",

            # "file.1"
            r"\.\d+\s*$",

            # "file (1)"
            r"\s*\(\d+\)\s*$",
        ]

        previous = None

        # Run multiple times so:
        # file.copy.1 -> file
        while previous != name:

            previous = name

            for pattern in patterns:

                name = re.sub(
                    pattern,
                    "",
                    name,
                    flags=re.IGNORECASE,
                )

        return name.strip()

    # ========================================================
    # Duplicate Priority
    # ========================================================

    def duplicate_priority(self, item):

        path = item.data(
            0,
            Qt.ItemDataRole.UserRole,
        )

        if not path:
            return (
                999,
                999,
                999,
            )

        filename = os.path.basename(path)

        stem = Path(filename).stem

        normalized = self.normalize_duplicate_name(
            filename
        )

        lower_stem = stem.lower().strip()

        # ----------------------------------------------------
        # Score 1:
        # Exact clean/original filename gets highest priority.
        #
        # file.txt
        #   => 0
        #
        # file (1).txt
        #   => 1
        #
        # file.copy.txt
        #   => 1
        # ----------------------------------------------------

        if lower_stem == normalized:

            suffix_score = 0

        else:

            suffix_score = 1

        # ----------------------------------------------------
        # Score 2:
        # Prefer shorter filename.
        # ----------------------------------------------------

        filename_length = len(filename)

        # ----------------------------------------------------
        # Score 3:
        # Prefer shallower directory.
        #
        # Example:
        # C:\Files\file.txt
        #
        # is preferred over:
        # C:\Files\Backup\file (1).txt
        # ----------------------------------------------------

        try:

            depth = len(
                Path(path).parts
            )

        except Exception:

            depth = 999

        return (
            suffix_score,
            filename_length,
            depth,
        )

    # ========================================================
    # Find Original File
    # ========================================================

    def find_original_item(self, children):

        valid_items = []

        for item in children:

            path = item.data(
                0,
                Qt.ItemDataRole.UserRole,
            )

            if path:

                valid_items.append(
                    item
                )

        if not valid_items:

            return None

        # ----------------------------------------------------
        # Sort according to original priority.
        #
        # IMPORTANT:
        # No dictionary .get() is used here.
        # Every object is a QTreeWidgetItem.
        # ----------------------------------------------------

        valid_items.sort(
            key=self.duplicate_priority
        )

        return valid_items[0]

    # ========================================================
    # Select All Duplicate Files
    # ========================================================

    def select_all_duplicate_files(self):

        # ----------------------------------------------------
        # Clear everything first.
        # ----------------------------------------------------

        self.duplicate_results.clearSelection()

        selected_count = 0
        group_count = 0

        # ----------------------------------------------------
        # Process every duplicate group.
        # ----------------------------------------------------

        for i in range(
            self.duplicate_results.topLevelItemCount()
        ):

            parent = (
                self.duplicate_results.topLevelItem(i)
            )

            children = []

            # ------------------------------------------------
            # Get actual file rows only.
            # ------------------------------------------------

            for j in range(
                parent.childCount()
            ):

                child = parent.child(j)

                path = child.data(
                    0,
                    Qt.ItemDataRole.UserRole,
                )

                if path:

                    children.append(
                        child
                    )

            # ------------------------------------------------
            # Need at least 2 files.
            # ------------------------------------------------

            if len(children) < 2:
                continue

            group_count += 1

            # ------------------------------------------------
            # Find original.
            # ------------------------------------------------

            original = self.find_original_item(
                children
            )

            # ------------------------------------------------
            # Select EVERYTHING EXCEPT original.
            # ------------------------------------------------

            for child in children:

                if child is original:
                    continue

                child.setSelected(
                    True
                )

                selected_count += 1

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        self.status.setText(
            f"Selected {selected_count:,} duplicate file(s) "
            f"from {group_count:,} group(s). "
            f"Original files were kept unselected."
        )

    # ========================================================
    # Clear Selection
    # ========================================================

    def clear_duplicate_selection(self):

        self.duplicate_results.clearSelection()

        self.status.setText(
            "Duplicate selection cleared"
        )

    # ========================================================
    # Delete Selected Duplicates
    # ========================================================

    def delete_selected_duplicates(self):

        selected = (
            self.duplicate_results.selectedItems()
        )

        paths = []

        items_to_remove = []

        # ----------------------------------------------------
        # Only child file rows are considered.
        # Parent group rows are ignored.
        # ----------------------------------------------------

        for item in selected:

            path = item.data(
                0,
                Qt.ItemDataRole.UserRole,
            )

            if not path:
                continue

            # Only delete actual files.
            if not item.parent():
                continue

            if path not in paths:

                paths.append(path)

                items_to_remove.append(
                    item
                )

        # ----------------------------------------------------
        # Nothing selected
        # ----------------------------------------------------

        if not paths:

            QMessageBox.information(
                self,
                "No Files Selected",
                "Select duplicate files first.",
            )

            return

        # ----------------------------------------------------
        # Confirmation
        # ----------------------------------------------------

        answer = QMessageBox.question(
            self,
            "Delete Selected Duplicates",
            f"Move {len(paths)} duplicate file(s) "
            "to Recycle Bin?\n\n"
            "Original files will remain untouched.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        deleted = 0
        failed = 0

        # ----------------------------------------------------
        # Delete files
        # ----------------------------------------------------

        for item in items_to_remove:

            path = item.data(
                0,
                Qt.ItemDataRole.UserRole,
            )

            try:

                if not os.path.exists(path):

                    failed += 1
                    continue

                send2trash(path)

                deleted += 1

                parent = item.parent()

                if parent:

                    parent.removeChild(
                        item
                    )

                    # ------------------------------------------------
                    # If only one file remains, it is no longer
                    # a duplicate group.
                    # ------------------------------------------------

                    if parent.childCount() <= 1:

                        index = (
                            self.duplicate_results
                            .indexOfTopLevelItem(parent)
                        )

                        if index >= 0:

                            self.duplicate_results.takeTopLevelItem(
                                index
                            )

                        # Remove from dictionary
                        for key, value in list(
                            self.duplicate_items.items()
                        ):

                            if value is parent:

                                del self.duplicate_items[
                                    key
                                ]

                                break

            except Exception:

                failed += 1

        # ----------------------------------------------------
        # Result message
        # ----------------------------------------------------

        message = (
            f"Moved {deleted} duplicate file(s) "
            "to Recycle Bin."
        )

        if failed:

            message += (
                f" Failed: {failed}"
            )

        self.status.setText(
            message
        )

        if deleted or failed:

            QMessageBox.information(
                self,
                "Delete Complete",
                message,
            )

    # ========================================================
    # Format Size
    # ========================================================

    @staticmethod
    def format_size(size):

        units = [
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        ]

        size = float(size)

        for unit in units:

            if size < 1024:

                return (
                    f"{size:.1f} {unit}"
                )

            size /= 1024

        return f"{size:.1f} PB"

    # ========================================================
    # Error
    # ========================================================

    def worker_error(self, message):

        self.search_button.setEnabled(
            True
        )

        self.stop_search_button.setEnabled(
            False
        )

        self.duplicate_button.setEnabled(
            True
        )

        self.stop_duplicate_button.setEnabled(
            False
        )

        self.progress.setVisible(
            False
        )

        QMessageBox.critical(
            self,
            "Error",
            message,
        )


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":

    # Generate icon automatically
    icon_path = ensure_icon()

    app = QApplication(sys.argv)

    app.setApplicationName(
        "Smart File Finder"
    )

    if icon_path.exists():

        app.setWindowIcon(
            QIcon(str(icon_path))
        )

    window = SmartFileFinder()

    window.show()

    sys.exit(
        app.exec()
    )