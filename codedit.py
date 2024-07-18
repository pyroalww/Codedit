
# Project Name: Codedit
# License: MIT
# Author: @pyroalww
# www.pyrollc.com.tr



import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import subprocess

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(PythonHighlighter, self).__init__(parent)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def", "del", 
            "elif", "else", "except", "False", "finally", "for", "from", "global", 
            "if", "import", "in", "is", "lambda", "None", "nonlocal", "not", "or", 
            "pass", "raise", "return", "True", "try", "while", "with", "yield"
        ]
        self.highlighting_rules.extend([(QRegExp("\\b" + keyword + "\\b"), keyword_format) for keyword in keywords])

        single_line_comment_format = QTextCharFormat()
        single_line_comment_format.setForeground(QColor("darkGreen"))
        self.highlighting_rules.append((QRegExp("#[^\n]*"), single_line_comment_format))

        quotation_format = QTextCharFormat()
        quotation_format.setForeground(QColor("#D69D85"))
        self.highlighting_rules.append((QRegExp("\".*\""), quotation_format))
        self.highlighting_rules.append((QRegExp("\'.*\'"), quotation_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.setTabStopWidth(4)
        

    def line_number_area_width(self):
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().width('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), Qt.lightGray)
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, int(top), self.line_number_area.width(), self.fontMetrics().height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(Qt.yellow).lighter(160)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Codedit")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(self.load_stylesheet())

        self.tab_widget = QTabWidget()
        
        self.create_menu_bar()
        
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())
        
        self.tree = QTreeView()
        self.tree.setModel(self.file_system_model)
        self.tree.setRootIndex(self.file_system_model.index(QDir.rootPath()))
        self.tree.clicked.connect(self.open_file_from_tree)
        self.tree.setStyleSheet("background-color: #2b2b2b; color: white;")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree)
        splitter.addWidget(self.tab_widget)
        
        self.setCentralWidget(splitter)
        
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_files)
        self.auto_save_timer.start(60000)  # 60 snde bir oto kayıt

        self.current_theme = "Dark"

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("background-color: #2b2b2b; color: white;")

        file_menu = menu_bar.addMenu('File')
        
        new_file_action = QAction('New File', self)
        new_file_action.setShortcut(QKeySequence.New)
        new_file_action.triggered.connect(self.new_file)
        file_menu.addAction(new_file_action)
        
        new_folder_action = QAction('New Folder', self)
        new_folder_action.triggered.connect(self.new_folder)
        file_menu.addAction(new_folder_action)
        
        open_file_action = QAction('Open File', self)
        open_file_action.setShortcut(QKeySequence.Open)
        open_file_action.triggered.connect(self.open_file)
        file_menu.addAction(open_file_action)
        
        open_folder_action = QAction('Open Folder', self)
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)
        
        save_file_action = QAction('Save File', self)
        save_file_action.setShortcut(QKeySequence.Save)
        save_file_action.triggered.connect(self.save_file)
        file_menu.addAction(save_file_action)
        
        save_as_file_action = QAction('Save As', self)
        save_as_file_action.setShortcut(QKeySequence.SaveAs)
        save_as_file_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_file_action)
        
        run_file_action = QAction('Run File', self)
        run_file_action.setShortcut("Ctrl+R")
        run_file_action.triggered.connect(self.run_file)
        file_menu.addAction(run_file_action)
        
        edit_menu = menu_bar.addMenu('Edit')
        
        copy_action = QAction('Copy', self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_text)
        edit_menu.addAction(copy_action)
        
        cut_action = QAction('Cut', self)
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.cut_text)
        edit_menu.addAction(cut_action)
        
        paste_action = QAction('Paste', self)
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.paste_text)
        edit_menu.addAction(paste_action)
        
        settings_menu = menu_bar.addMenu('Settings')
        
        change_font_action = QAction('Change Font', self)
        change_font_action.triggered.connect(self.change_font)
        settings_menu.addAction(change_font_action)
        
        change_theme_action = QAction('Change Theme', self)
        change_theme_action.triggered.connect(self.change_theme)
        settings_menu.addAction(change_theme_action)
        
        set_auto_save_interval_action = QAction('Set Auto Save Interval', self)
        set_auto_save_interval_action.triggered.connect(self.set_auto_save_interval)
        settings_menu.addAction(set_auto_save_interval_action)

        
        project_menu = menu_bar.addMenu('Project')
        
        new_project_action = QAction('New Project', self)
        new_project_action.triggered.connect(self.new_project)
        project_menu.addAction(new_project_action)
        
        open_project_action = QAction('Open Project', self)
        open_project_action.triggered.connect(self.open_project)
        project_menu.addAction(open_project_action)
        
        git_menu = menu_bar.addMenu('Git')
        
        git_clone_action = QAction('Clone Repository', self)
        git_clone_action.triggered.connect(self.git_clone)
        git_menu.addAction(git_clone_action)
        
        git_commit_action = QAction('Commit', self)
        git_commit_action.triggered.connect(self.git_commit)
        git_menu.addAction(git_commit_action)
        
        git_push_action = QAction('Push', self)
        git_push_action.triggered.connect(self.git_push)
        git_menu.addAction(git_push_action)

    def load_stylesheet(self):
        return """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QTabWidget::pane {
            border: 0;
        }
        QTabBar::tab {
            background: #2b2b2b;
            color: white;
            padding: 10px;
        }
        QTabBar::tab:selected {
            background: #3c3c3c;
        }
        QPlainTextEdit {
            background-color: #1e1e1e;
            color: white;
            font-family: Consolas;
            font-size: 12pt;
        }
        QTreeView {
            background-color: #2b2b2b;
            color: white;
        }
        QMenuBar {
            background-color: #2b2b2b;
            color: white;
        }
        QMenuBar::item {
            background: #2b2b2b;
            color: white;
        }
        QMenuBar::item:selected {
            background: #3c3c3c;
        }
        QMenu {
            background-color: #2b2b2b;
            color: white;
        }
        QMenu::item:selected {
            background-color: #3c3c3c;
        }
        QTreeView::item {
            background-color: #2b2b2b;
            color: white;
        }
        QTreeView::item:selected {
            background-color: #3c3c3c;
        }
        """

    def new_file(self):
        new_tab = CodeEditor()
        new_tab.highlighter = PythonHighlighter(new_tab.document())
        index = self.tab_widget.addTab(new_tab, "Untitled")
        self.tab_widget.setCurrentIndex(index)

    def new_folder(self):
        folder_name, _ = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if folder_name:
            current_path = self.file_system_model.rootPath()
            new_folder_path = os.path.join(current_path, folder_name)
            os.makedirs(new_folder_path, exist_ok=True)
            self.file_system_model.setRootPath(current_path)
            self.tree.setRootIndex(self.file_system_model.index(current_path))

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Python Files (*.py);;All Files (*)")
        if file_path:
            self.load_file(file_path)

    def open_file_from_tree(self, index):
        file_path = self.file_system_model.filePath(index)
        if os.path.isfile(file_path):
            self.load_file(file_path)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Open Folder", "")
        if folder_path:
            self.file_system_model.setRootPath(folder_path)
            self.tree.setRootIndex(self.file_system_model.index(folder_path))

    def save_file(self):
        current_editor = self.current_editor()
        if current_editor:
            current_path = self.tab_widget.tabToolTip(self.tab_widget.currentIndex())
            if current_path:
                with open(current_path, 'w') as file:
                    file.write(current_editor.toPlainText())
            else:
                self.save_file_as()

    def save_file_as(self):
        current_editor = self.current_editor()
        if current_editor:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", "Python Files (*.py);;All Files (*)")
            if file_path:
                with open(file_path, 'w') as file:
                    file.write(current_editor.toPlainText())
                self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_path))
                self.tab_widget.setTabToolTip(self.tab_widget.currentIndex(), file_path)

    def run_file(self):
        current_editor = self.current_editor()
        if current_editor:
            current_path = self.tab_widget.tabToolTip(self.tab_widget.currentIndex())
            if current_path:
                result = subprocess.run(['python', current_path], capture_output=True, text=True)
                QMessageBox.information(self, "Run Result", result.stdout)
            else:
                QMessageBox.warning(self, "Run Error", "Save the file before running.")

    def copy_text(self):
        current_editor = self.current_editor()
        if current_editor:
            current_editor.copy()

    def cut_text(self):
        current_editor = self.current_editor()
        if current_editor:
            current_editor.cut()

    def paste_text(self):
        current_editor = self.current_editor()
        if current_editor:
            current_editor.paste()

    def change_font(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.set_editor_font(font)

    def change_theme(self):
        themes = ["Dark", "Light"]
        theme, ok = QInputDialog.getItem(self, "Change Theme", "Select Theme:", themes, 0, False)
        if ok:
            self.apply_theme(theme)

    def set_auto_save_interval(self):
        interval, ok = QInputDialog.getInt(self, "Set Auto Save Interval", "Enter interval in seconds:", 60, 1, 3600)
        if ok:
            self.auto_save_timer.start(interval * 1000)

    def auto_save_files(self):
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            file_path = self.tab_widget.tabToolTip(i)
            if file_path:
                with open(file_path, 'w') as file:
                    file.write(editor.toPlainText())

    def load_file(self, file_path):
        with open(file_path, 'r') as file:
            content = file.read()
        editor = CodeEditor()
        editor.highlighter = PythonHighlighter(editor.document())
        editor.setPlainText(content)
        index = self.tab_widget.addTab(editor, os.path.basename(file_path))
        self.tab_widget.setTabToolTip(index, file_path)
        self.tab_widget.setCurrentIndex(index)

    def current_editor(self):
        return self.tab_widget.currentWidget()

    def set_editor_font(self, font):
        for i in range(self.tab_widget.count()):
            editor = self.tab_widget.widget(i)
            editor.setFont(font)

    def apply_theme(self, theme):
        if theme == "Dark":
            self.setStyleSheet(self.load_stylesheet())
        elif theme == "Light":
            self.setStyleSheet("")

    def new_project(self):
        project_name, _ = QInputDialog.getText(self, "New Project", "Project Name:")
        if project_name:
            project_path = os.path.join(QDir.homePath(), project_name)
            os.makedirs(project_path, exist_ok=True)
            self.file_system_model.setRootPath(project_path)
            self.tree.setRootIndex(self.file_system_model.index(project_path))

    def open_project(self):
        project_path = QFileDialog.getExistingDirectory(self, "Open Project", "")
        if project_path:
            self.file_system_model.setRootPath(project_path)
            self.tree.setRootIndex(self.file_system_model.index(project_path))

    def git_clone(self):
        repo_url, ok = QInputDialog.getText(self, "Clone Repository", "Repository URL:")
        if ok and repo_url:
            project_path = QFileDialog.getExistingDirectory(self, "Select Directory", "")
            if project_path:
                result = subprocess.run(['git', 'clone', repo_url, project_path], capture_output=True, text=True)
                QMessageBox.information(self, "Clone Result", result.stdout)
                self.file_system_model.setRootPath(project_path)
                self.tree.setRootIndex(self.file_system_model.index(project_path))

    def git_commit(self):
        commit_message, ok = QInputDialog.getText(self, "Commit Changes", "Commit Message:")
        if ok and commit_message:
            result = subprocess.run(['git', 'commit', '-am', commit_message], capture_output=True, text=True)
            QMessageBox.information(self, "Commit Result", result.stdout)

    def git_push(self):
        result = subprocess.run(['git', 'push'], capture_output=True, text=True)
        QMessageBox.information(self, "Push Result", result.stdout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
