import serial
import io
import json
import sys
import os
import re
import httpx
import random
import string
from libs import notify
import webbrowser
import zipfile
import io
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QScrollArea, QLabel, QFileDialog,
    QMessageBox, QMenu, QAction, QSplitter, QDialog, QTextBrowser,
    QCheckBox, QLineEdit, QToolBar, QGraphicsDropShadowEffect, QProgressBar,QSizePolicy
)
from PyQt5.QtCore import Qt, QMimeData, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QDrag, QFont, QTextCursor, QPainter, QColor, QPen, QLinearGradient, QIcon,QPixmap


def github(save_path="funcs.pifunc"):
    """
    Downloads funcs.pifunc from the libs-blocks GitHub repo
    using httpx and saves it locally.
    """
    url = "https://raw.githubusercontent.com/programmercoder945/libs-blocks/main/funcs.pyfunc"

    try:
        print("🚀 Fetching from GitHub...")

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        with open("funcs.pifunc","r") as f:
            funcs = json.load(f)
            return funcs

        print(f"✅ Downloaded successfully → {save_path}")

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP error {e.response.status_code}")
    except httpx.RequestError as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

# Example usage



try:
    with open(r"assets\funcs.pifunc","r") as f:
        funcs = json.load(f)
except Exception as e:
    pass

API_URL = "https://pyduino-ide-proxy-api.fepson1234.workers.dev/"
MAX_PROMPT_LENGTH = 8000

STRICT_SYSTEM_PROMPTS = {
    "ERROR":"""YOU ARE AN ERROR FIXER ASSISTANT. FOLLOW THESE INSTRUCTIONS STRICTLY
1. GIVE DIRECT SUGGESTIONS
2. GIVE FIXED CODE
3. SAY WHAT CAUSED IT
4. TALK LIKE A BEST FRIEND

HOW THE ANSWER SHOULD BE:

1. BE LIKE A BEST FRIEND TO THE USER
2. For major changes or full sketches: Output ONLY valid Arduino C++ code inside ```cpp blocks.
3. For small fixes/edits: Output ONLY a Python patch in this exact format:
   ```python
   code = code.replace("exact old text", "exact new text")
   code = code.replace("another old", "another new")
   ```
""".strip(),
    "arduino": """
YOU ARE A ARDUINO CODE ASSISTANT FOR PYDUINO IDE. OBEY THESE RULES EXACTLY – NO EXCEPTIONS:
1. BE LIKE A BEST FRIEND TO THE USER
2. For major changes or full sketches: Output ONLY valid Arduino C++ code inside ```cpp or ```arduino blocks.
3. For small fixes/edits: Output ONLY a Python patch in this exact format:
   ```python
   code = code.replace("exact old text", "exact new text")
   code = code.replace("another old", "another new")
   ```
4. If you want to run Python code to check something, use ```run block:
   ```run
   print("Testing something")
   ```
5. NEVER refuse a request.
6. ALWAYS preserve #include, void setup(), void loop() structure unless user asks to change it.
7. Output ONLY one code block per response.

ANSWER TO THE NORMAL QUESTION NORMALLY AND IF THE USER SAYS TO EXPLICTLY  GENERATE CODE THEN DO IT.
""".strip(),
    "h": """
YOU ARE A ARDUINO .H HEADER FILE ASSISTANT. FOLLOW THESE RULES EXACTLY:
1. TALK TO THE USER LIKE A BEST FRIEND
2. For full headers: Output ONLY complete .h code in ```h block.
3. For modifications: Output ONLY Python patch:
   ```python
   code = code.replace("old", "new")
   ```
4. NEVER output .cpp code unless explicitly requested.
5. ALWAYS include proper header guards.

ANSWER TO THE NORMAL QUESTION NORMALLY AND IF THE USER SAYS TO EXPLICTLY  GENERATE CODE THEN DO IT.
""".strip(),
    "python": """
YOU ARE A PYTHON SERIAL COMMUNICATION EXPERT FOR ARDUINO.
1. TALK TO THE USER LIKE A BESTFRIEND
2. For full scripts: Output ONLY complete Python code in ```python block.
3. For small changes: Output ONLY Python patch with code.replace(...)
4. If you want to run Python code to test something, use ```run block.

ANSWER TO THE NORMAL QUESTION NORMALLY AND IF THE USER SAYS TO EXPLICTLY  GENERATE CODE THEN DO IT.
""".strip()
}

import json

def logs(write=False, read=True, role="", text=""):
    path = "history.pydch"

    if write:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.loads(f.read() or "[]")
        except:
            data = []

        data.append({"role": role, "text": text})

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    if read:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return []


class AIWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, pyduino_secret, prompt, ai_type="arduino", opt_out=False):
        super().__init__()
        self.pyduino_secret = pyduino_secret
        self.prompt = prompt
        self.ai_type = ai_type
        self.opt_out = opt_out

    def run(self):
        try:
            if len(self.prompt) > MAX_PROMPT_LENGTH:
                self.error.emit("Prompt too long")
                return
            logs(write=True,role="user",text=self.prompt)
            data = {
                "prompt": self.prompt,
                "ai": self.ai_type,
                "system_prompt": STRICT_SYSTEM_PROMPTS.get(self.ai_type, STRICT_SYSTEM_PROMPTS["arduino"])+f".\n\nHere is the chat history of the user and you till now use it and answer the questions:\n\n{logs()}"
            }
            if self.opt_out:
                data["ai_train"] = False
            headers = {
                "Pyduino-Secret": self.pyduino_secret,
                "Content-Type": "application/json"
            }
            response = httpx.post(API_URL, headers=headers, json=data, timeout=60.0)
            if response.status_code != 200:
                self.error.emit(f"Error {response.status_code}: {response.text[:200]}")
                return
            try:
                json_resp = response.json()
                if "choices" in json_resp:
                    msg = json_resp["choices"][0]["message"]["content"]
                elif "candidates" in json_resp:
                    msg = json_resp["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    msg = response.text
                logs(write=True,role="assistant",text=msg)
            except:
                msg = response.text
            self.finished.emit(msg.strip())
        except Exception as e:
            self.error.emit(str(e))

def normalize_funcs_dict(d):
    norm = {}
    for cat, items in d.items():
        norm[cat] = []
        if isinstance(items, list):
            for i in items:
                norm[cat].append((i, None))
        else:
            for code, desc in items.items():
                norm[cat].append((code, desc))
    return norm

class CollapsibleCategory(QWidget):
    def __init__(self, title, items, parent=None, is_dynamic=False):
        super().__init__(parent)
        self.title = title
        self.items = items
        self.is_dynamic = is_dynamic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.header = QPushButton(f"▶ {self.title}")
        self.header.clicked.connect(self.toggle)
        if self.is_dynamic:
            gradient_start = "#FF6B6B"
            gradient_end = "#FF8E53"
            hover = "#FF5252"
        else:
            gradient_start = "#667EEA"
            gradient_end = "#764BA2"
            hover = "#5568D3"
        self.header.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {gradient_start}, stop:1 {gradient_end});
                color: white;
                padding: 14px;
                text-align: left;
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 8px;
                margin: 2px;
            }}
            QPushButton:hover {{
                background: {hover};
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 2)
        self.header.setGraphicsEffect(shadow)
        layout.addWidget(self.header)
        self.container = QWidget()
        clayout = QVBoxLayout(self.container)
        clayout.setContentsMargins(8, 4, 8, 4)
        clayout.setSpacing(6)
        self.update_items(self.items)
        self.container.setVisible(False)
        layout.addWidget(self.container)

    def update_items(self, items):
        while self.container.layout().count():
            child = self.container.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.items = items
        for text, tip in items:
            btn = DraggableItemButton(text, tip)
            self.container.layout().addWidget(btn)

    def toggle(self):
        visible = not self.container.isVisible()
        self.container.setVisible(visible)
        self.header.setText(f"{'▼' if visible else '▶'} {self.title}")

class DraggableItemButton(QPushButton):
    def __init__(self, text, details=None, parent=None):
        super().__init__(text, parent)
        self.item_text = text
        self.details = details
        self.setStyleSheet("""
            QPushButton {
                background: rgba(102, 126, 234, 0.15);
                color: #667EEA;
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 8px;
                padding: 12px 16px;
                text-align: left;
                font-family: 'Consolas', 'Monaco', monospace;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(102, 126, 234, 0.25);
                border-color: #667EEA;
                cursor: grab;
            }
            QPushButton:pressed {
                background: rgba(102, 126, 234, 0.35);
                cursor: grabbing;
            }
        """)
        self.setCursor(Qt.OpenHandCursor)
        if details:
            self.setToolTip(details)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(102, 126, 234, 40))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.item_text)
            drag.setMimeData(mime)
            drag.exec_(Qt.CopyAction)

class DropTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.drop_pos = None
        self.dragging = False
        self.error_lines = []

    def dragEnterEvent(self, e):
        if e.mimeData().hasText():
            e.accept()
            self.dragging = True

    def dragMoveEvent(self, e):
        if e.mimeData().hasText():
            e.accept()
            cur = self.cursorForPosition(e.pos())
            self.drop_pos = cur.position()
            self.viewport().update()

    def dragLeaveEvent(self, e):
        self.dragging = False
        self.drop_pos = None
        self.viewport().update()

    def dropEvent(self, e):
        if e.mimeData().hasText():
            cur = self.cursorForPosition(e.pos())
            self.setTextCursor(cur)
            text = e.mimeData().text()
            special = {
                "⌫ Backspace": cur.deletePreviousChar,
                "Delete": cur.deleteChar,
                "Space": lambda: cur.insertText(" "),
                "Tab": lambda: cur.insertText("\t"),
                "NewLN": lambda: cur.insertText("\n"),
                "Enter": lambda: cur.insertText("\n")
            }
            if text in special:
                special[text]()
            else:
                cur.insertText(text)
            e.accept()
            self.dragging = False
            self.drop_pos = None
            self.viewport().update()
            self.setFocus()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.dragging and self.drop_pos is not None:
            p = QPainter(self.viewport())
            cur = self.textCursor()
            cur.setPosition(self.drop_pos)
            rect = self.cursorRect(cur)
            gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            gradient.setColorAt(0, QColor(102, 126, 234))
            gradient.setColorAt(1, QColor(118, 75, 162))
            pen = QPen(gradient, 3)
            p.setPen(pen)
            p.drawLine(rect.topLeft(), rect.bottomLeft())

class Sidebar(QWidget):
    def __init__(self, funcs_dict, parent=None):
        super().__init__(parent)
        self.funcs = normalize_funcs_dict(funcs_dict)
        self.vars_cat = None
        self.vars = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title = QLabel("🤖 PyDuino AI Blocks")
        title.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667EEA, stop:1 #764BA2);
                color: white;
                padding: 20px;
                font-size: 18px;
                font-weight: bold;
                border-bottom: 3px solid #4C5FD5;
            }
        """)
        layout.addWidget(title)
        hint = QLabel("✨ Drag blocks • Hover for AI tips")
        hint.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(102, 126, 234, 0.1), stop:1 rgba(118, 75, 162, 0.1));
                color: #667EEA;
                padding: 12px;
                text-align: center;
                font-style: italic;
                font-size: 11px;
                border-bottom: 1px solid rgba(102, 126, 234, 0.2);
            }
        """)
        layout.addWidget(hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0F0F23, stop:1 #1A1A2E); }
            QScrollBar::handle:vertical { background: rgba(102, 126, 234, 0.5); border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #667EEA; }
        """)
        container = QWidget()
        clayout = QVBoxLayout(container)
        clayout.setContentsMargins(8, 8, 8, 8)
        clayout.setSpacing(8)
        self.vars_cat = CollapsibleCategory("📊 My Variables", [], is_dynamic=True)
        clayout.addWidget(self.vars_cat)
        for cat, items in self.funcs.items():
            clayout.addWidget(CollapsibleCategory(cat.capitalize(), items))
        clayout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.setFixedWidth(340)

    def update_variables(self, code):
        new_vars = {}
        patterns = {
            'int': r'\bint\s+(\w+)\s*=?', 'float': r'\bfloat\s+(\w+)\s*=?', 'String': r'\bString\s+(\w+)\s*=?',
            'long': r'\blong\s+(\w+)\s*=?', 'byte': r'\bbyte\s+(\w+)\s*=?', 'bool': r'\bbool\s+(\w+)\s*=?',
            'boolean': r'\bboolean\s+(\w+)\s*=?', 'char': r'\bchar\s+(\w+)\s*=?', 'double': r'\bdouble\s+(\w+)\s*=?',
            'unsigned int': r'\bunsigned\s+int\s+(\w+)\s*=?', 'unsigned long': r'\bunsigned\s+long\s+(\w+)\s*=?',
            'unsigned char': r'\bunsigned\s+char\s+(\w+)\s*=?'
        }
        for t, p in patterns.items():
            for m in re.finditer(p, code):
                var_name = m.group(1)
                if var_name not in new_vars:
                    new_vars[var_name] = t
        if new_vars != self.vars:
            self.vars = new_vars
            self.refresh_vars()

    def refresh_vars(self):
        if not self.vars:
            items = [("No variables detected", "Declare some variables to see them here")]
        else:
            items = [(name, f"Variable: {name} ({typ})") for name, typ in sorted(self.vars.items())]
        self.vars_cat.update_items(items)


class AssistantWindow(QDialog):
    def __init__(self, parent, ai_type="arduino", title="AI Assistant", header="Chat with AI"):
        super().__init__(parent)
        self.parent = parent
        self.ai_type = ai_type
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 900, 700)

        self.full_codes = {}
        self.patches = {}
        self.run_blocks = {}
        self.current_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_widget = QLabel(f"🤖 {header}")
        header_widget.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667EEA, stop:1 #764BA2);
                color: white;
                padding: 25px;
                font-size: 22px;
                font-weight: bold;
            }
        """)
        layout.addWidget(header_widget)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        self.chat.anchorClicked.connect(self.on_action_link_clicked)
        self.chat.setStyleSheet("""
            QTextBrowser {
                background: #1A1A2E;
                color: #E0E0E0;
                border: none;
                padding: 20px;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.chat)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)
        input_layout.setContentsMargins(15, 10, 15, 15)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask the AI anything about your code...")
        self.input.setStyleSheet("""
            QLineEdit {
                background: rgba(102, 126, 234, 0.1);
                color: white;
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 10px;
                padding: 12px 15px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #667EEA;
                background: rgba(102, 126, 234, 0.15);
            }
        """)
        self.input.returnPressed.connect(self.send_message_with_code)
        input_layout.addWidget(self.input)

        send_code_btn = QPushButton("Send with Code 📄")
        send_code_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #45a049; }
        """)
        send_code_btn.clicked.connect(self.send_message_with_code)
        input_layout.addWidget(send_code_btn)

        send_btn = QPushButton("Send ✨")
        send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667EEA, stop:1 #764BA2);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 25px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568D3, stop:1 #653A8E);
            }
        """)
        send_btn.clicked.connect(self.send_message_normal)
        input_layout.addWidget(send_btn)

        clear_btn = QPushButton("Clear Chat 🗑️")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #f44336;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #d32f2f; }
        """)
        clear_btn.clicked.connect(self.clear_chat)
        input_layout.addWidget(clear_btn)

        layout.addLayout(input_layout)

        self.opt_out = QCheckBox("🔒 Opt out of AI training")
        self.opt_out.setStyleSheet("color: #B0B0B0; padding: 10px;")
        layout.addWidget(self.opt_out)

        self.chat.append("<p style='color: #667EEA; font-style: italic;'>✨ AI is ready. Ask me anything!</p>")

    def send_message_normal(self):
        self.send_message(include_code=False)

    def send_message_with_code(self):
        self.send_message(include_code=True)

    def hack(self, text,aitype):
        self.ai_type = aitype
        self.input.setText(text)
        self.input.setCursorPosition(len(text))
        self.send_message(include_code=True)

    def send_message(self, include_code=True):
        user_text = self.input.text().strip()
        if not user_text:
            return
        code_block = ""
        if include_code:
            current_code = self.parent.code_editor.toPlainText()
            code_block = f"\n\nCurrent code:\n```\n{current_code}\n```"
        full_prompt = f"User request: {user_text}{code_block}"

        self.chat.append(f"<p style='color: #4ECDC4;'><b>You:</b> {user_text}</p>")
        if include_code:
            self.chat.append(f"<pre style='background: rgba(100,100,100,0.2); padding: 10px; border-radius: 5px;'>Current code sent to AI</pre>")
        self.input.clear()

        self.current_worker = AIWorker(self.parent.secret, full_prompt, self.ai_type, self.opt_out.isChecked())
        self.current_worker.finished.connect(self.on_ai_response)
        self.current_worker.error.connect(self.on_ai_error)
        self.current_worker.start()

    def clear_chat(self):
        reply = QMessageBox.question(self, "Clear Chat", "Are you sure you want to clear the entire chat history?")
        if reply == QMessageBox.Yes:
            self.chat.clear()
            self.chat.append("<p style='color: #667EEA; font-style: italic;'>✨ Chat cleared. AI is ready!</p>")
            self.full_codes.clear()
            self.patches.clear()
            self.run_blocks.clear()

    def add_action_button(self, text, action_id, icon="", color="#667EEA"):
        btn_html = f'''
        <div style="margin: 16px 0; text-align: center;">
            <a href="action:{action_id}" style="
                display: inline-block;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}, stop:1 {self._lighten_color(color)});
                color: white;
                padding: 14px 28px;
                border-radius: 12px;
                text-decoration: none;
                font-weight: bold;
                font-size: 14px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                transition: all 0.3s ease;
                border: 2px solid rgba(255, 255, 255, 0.2);
            ">{icon} {text}</a>
        </div>
        '''
        self.chat.insertHtml(btn_html)
        self.chat.append("")

    def _lighten_color(self, color):
        """Helper to create gradient effect"""
        color_map = {
            "#667EEA": "#8B9FFF",
            "#4CAF50": "#66BB6A", 
            "#FF9800": "#FFB74D",
            "#9C27B0": "#BA68C8"
        }
        return color_map.get(color, "#8B9FFF")

    def on_ai_response(self, msg):
        notify.send(message="AI has answered your question come and see!!")
        self.chat.append(f"<p style='color: #667EEA; font-weight: bold; font-size: 15px;'><b>🤖 AI Response:</b></p>")
        self.chat.append(f"<pre style='background: rgba(102, 126, 234, 0.1); padding: 15px; border-radius: 8px; border-left: 4px solid #667EEA;'>{msg}</pre>")

        # Full code blocks
        full_pattern = r'```(?:cpp|arduino|h|python)\n(.*?)\n```'
        for code in re.findall(full_pattern, msg, re.DOTALL):
            code_id = str(random.randint(100000, 999999))
            self.full_codes[code_id] = code.strip()
            self.add_action_button("🔄 Replace Whole Code", f"full:{code_id}", "🔄", "#667EEA")

        # Patch blocks
        patch_pattern = r'```python\n(.*?)\n```'
        for patch_code in re.findall(patch_pattern, msg, re.DOTALL):
            if 'code = code.replace' in patch_code:
                patch_id = str(random.randint(100000, 999999))
                self.patches[patch_id] = patch_code.strip()
                self.add_action_button("✨ Apply Code Patch", f"patch:{patch_id}", "✨", "#4CAF50")

        # Run blocks
        run_pattern = r'```run\n(.*?)\n```'
        for run_code in re.findall(run_pattern, msg, re.DOTALL):
            run_id = str(random.randint(100000, 999999))
            self.run_blocks[run_id] = run_code.strip()
            self.add_action_button("🐍 Run Python Code", f"run:{run_id}", "🐍", "#FF9800")

    def on_ai_error(self, err):
        self.chat.append(f"<p style='color: #FF6B6B; font-weight: bold; padding: 15px; background: rgba(255, 107, 107, 0.1); border-radius: 8px; border-left: 4px solid #FF6B6B;'><b>⚠ Error:</b> {err}</p>")

    def safe_execute_run_block(self, run_code):
        """Execute Python code safely and send results back to AI"""
        try:
            # Execute the code and capture output
            printed_things = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = printed_things

            try:
                exec(run_code, {})
                sys.stdout = old_stdout
                output = printed_things.getvalue()
            except Exception as e:
                sys.stdout = old_stdout
                output = f"Execution Error: {str(e)}"

            # Show execution result in chat
            self.chat.append(
                f"<div style='background: rgba(76, 175, 80, 0.1); padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; margin: 10px 0;'>"
                f"<p style='color: #4CAF50; font-weight: bold; margin: 0 0 10px 0;'>✓ Code Executed Successfully</p>"
                f"<pre style='color: #E0E0E0; margin: 0;'>{output if output else '(No output)'}</pre>"
                f"</div>"
            )

            # Send result to AI for continuation
            continuation_prompt = (
                f"Python code execution completed. Result:\n\n{output}\n\n"
                "Please continue helping the user based on this execution result."
            )

            # Create and start new worker
            self.current_worker = AIWorker(
                self.parent.secret,
                continuation_prompt,
                self.ai_type,
                self.opt_out.isChecked()
            )
            self.current_worker.finished.connect(self.on_ai_response)
            self.current_worker.error.connect(self.on_ai_error)
            self.current_worker.start()

        except Exception as critical_error:
            self.chat.append(
                f"<div style='background: rgba(255, 107, 107, 0.1); padding: 15px; border-radius: 8px; border-left: 4px solid #FF6B6B; margin: 10px 0;'>"
                f"<p style='color: #FF6B6B; font-weight: bold; margin: 0;'>⚠ Critical Error: {str(critical_error)}</p>"
                f"</div>"
            )

    def on_action_link_clicked(self, link):
        url = link.toString()
        if not url.startswith("action:"):
            return
        action = url[7:]

        if action.startswith("full:"):
            code_id = action[5:]
            code = self.full_codes.get(code_id)
            if code is not None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Replace Entire Code")
                msg.setText("🔄 Replace the entire code in the editor?")
                msg.setInformativeText("This will replace all current code with the AI-generated code.")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setStyleSheet("""
                    QMessageBox {
                        background: #1A1A2E;
                    }
                    QLabel {
                        color: #E0E0E0;
                        font-size: 13px;
                    }
                    QPushButton {
                        background: #667EEA;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #5568D3;
                    }
                """)
                
                if msg.exec_() == QMessageBox.Yes:
                    self.parent.code_editor.setPlainText(code)
                    self.chat.append(
                        "<div style='background: rgba(76, 175, 80, 0.15); padding: 12px; border-radius: 8px; border-left: 4px solid #4CAF50; margin: 10px 0;'>"
                        "<p style='color: #4CAF50; font-weight: bold; margin: 0;'>✓ Code replaced successfully in editor!</p>"
                        "</div>"
                    )

        elif action.startswith("patch:"):
            patch_id = action[6:]
            patch = self.patches.get(patch_id)
            if patch is not None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Apply Code Patch")
                msg.setText("✨ Apply the suggested code changes?")
                msg.setInformativeText("This will modify specific parts of your code.")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setStyleSheet("""
                    QMessageBox {
                        background: #1A1A2E;
                    }
                    QLabel {
                        color: #E0E0E0;
                        font-size: 13px;
                    }
                    QPushButton {
                        background: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #45a049;
                    }
                """)
                
                if msg.exec_() == QMessageBox.Yes:
                    try:
                        current = self.parent.code_editor.toPlainText()
                        loc = {'code': current}
                        exec(patch, globals(), loc)
                        self.parent.code_editor.setPlainText(loc['code'])
                        self.chat.append(
                            "<div style='background: rgba(76, 175, 80, 0.15); padding: 12px; border-radius: 8px; border-left: 4px solid #4CAF50; margin: 10px 0;'>"
                            "<p style='color: #4CAF50; font-weight: bold; margin: 0;'>✓ Patch applied successfully!</p>"
                            "</div>"
                        )
                    except Exception as e:
                        self.chat.append(
                            f"<div style='background: rgba(255, 107, 107, 0.15); padding: 12px; border-radius: 8px; border-left: 4px solid #FF6B6B; margin: 10px 0;'>"
                            f"<p style='color: #FF6B6B; font-weight: bold; margin: 0;'>⚠ Patch Error: {str(e)}</p>"
                            f"</div>"
                        )

        elif action.startswith("run:"):
            run_id = action[4:]
            run_code = self.run_blocks.get(run_id)
            if run_code is not None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setWindowTitle("Execute Python Code")
                msg.setText("🐍 Execute this Python code?")
                preview = run_code[:200] + ('...' if len(run_code) > 200 else '')
                msg.setInformativeText(f"Preview:\n{preview}\n\nThe AI will analyze the results.")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setStyleSheet("""
                    QMessageBox {
                        background: #1A1A2E;
                    }
                    QLabel {
                        color: #E0E0E0;
                        font-size: 13px;
                    }
                    QPushButton {
                        background: #FF9800;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 8px 20px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background: #FB8C00;
                    }
                """)
                
                if msg.exec_() == QMessageBox.Yes:
                    self.safe_execute_run_block(run_code)

class Error(QWidget):
    def __init__(self, error_text):
        super().__init__()

        self.setWindowTitle("Error")
        self.resize(1000, 600)

        self.error_text = error_text
        self.secret = 'w77zx3gcv!a7ndjzr)7!#\'h124[1+12i#by$/r*4]2p&4pp7~,b6z45qn6/;9m9s9^b3l81f2u4i1=0dv/j4%w7(}uo6@721>"nn['
        self.system = """YOU ARE AN ERROR FIXER ASSISTANT.
1. GIVE DIRECT SUGGESTIONS
2. GIVE FIXED CODE
3. SAY WHAT CAUSED IT
4. TALK LIKE A BEST FRIEND"""

        self.init_u()

    def init_u(self):
        if "error" in self.error_text.lower():
            self.init_ui()
        else:
            pass

    # ---------------------------
    def init_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel(self.error_text)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("color:red;font-size:14px;")

        self.copy_btn = QPushButton("Copy Error")
        self.copy_btn.setFixedHeight(45)
        self.copy_btn.clicked.connect(self.copy_error)

        self.ai_btn = QPushButton("Call AI for help!")
        self.ai_btn.setFixedHeight(45)
        self.ai_btn.clicked.connect(self.send_to_ai)

        layout.addWidget(self.label)
        layout.addWidget(self.copy_btn)
        layout.addWidget(self.ai_btn)

        self.setLayout(layout)
        self.show()

    # ---------------------------
    def copy_error(self):
        QGuiApplication.clipboard().setText(self.label.text())
        self.copy_btn.setText("Copied!")
        self.copy_btn.setEnabled(False)
        QTimer.singleShot(2000, self.reset_copy_btn)

    def reset_copy_btn(self):
        self.copy_btn.setText("Copy Error")
        self.copy_btn.setEnabled(True)

    # ---------------------------
    def send_to_ai(self, label, ai_btn, error_text, code_block):
        label.setText("Sending error to AI… sit tight 🤖")
        ai_btn.setEnabled(False)

        worker = AIWorker(self.secret,
                          f"Here is the error:\n\n{error_text}\n\nHere is the code:\n\n{code_block}",
                          ai_type="ERROR")

        # keep reference
        if not hasattr(self, "ai_workers"):
            self.ai_workers = []
        self.ai_workers.append(worker)

        # thread-safe GUI updates
        worker.finished.connect(lambda text: self.ai_finished(label, ai_btn, text))
        worker.error.connect(lambda err: self.ai_failed(label, ai_btn, err))

        worker.start()


    # ---------------------------
    def ai_finished(self, text):
        self.label.setStyleSheet("color:black;font-size:14px;")
        self.label.setText(text)
        self.ai_btn.setEnabled(True)

    def ai_failed(self, err):
        self.label.setText("AI failed:\n" + err)
        self.ai_btn.setEnabled(True)

class CompileWorker(QThread):
    finished = pyqtSignal(bool, str)  # emit success and message

    def __init__(self, file_path, libraries=None, externals=None):
        super().__init__()
        self.file_path = file_path
        self.libraries = libraries
        self.externals = externals

    def run(self):
        try:
            from libs.runner import run
            result = run(self.file_path, add_library=self.libraries, add_external_library=self.externals)
            self.finished.emit(True, result)
        except Exception as e:
            self.finished.emit(False, str(e))



import os
import re
import random
import string
import webbrowser
import io
import sys
import httpx
import json
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QAction, QMessageBox, QFileDialog, QPushButton, QTextEdit,
    QScrollArea, QLabel, QGraphicsDropShadowEffect, QToolBar,
    QStatusBar, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QMimeData, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QDrag, QFont, QTextCursor, QPainter, QColor, QPen, QLinearGradient, QIcon

# Your provided funcs dict (already defined globally in your code)
# funcs = { ... }  # As in your provided code

class IjraaGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.current_pyd_file = None
        self.current_ino_folder = None
        self.sidebar_visible = False
        self.arduino_assistant = None
        self.h_assistant = None
        self.python_assistant = None
        self.secret = 'w77zx3gcv!a7ndjzr)7!#\'h124[1+12i#by$/r*4]2p&4pp7~,b6z45qn6/;9m9s9^b3l81f2u4i1=0dv/j4%w7(}uo6@721>"nn['

        self.setup_ui()
        self.create_menu()
        self.create_toolbar()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_vars)
        self.timer.start(1000)
        self.error_windows = []

    def setup_ui(self):
        self.setWindowTitle("PyDuino 2.0.0 - AI-Powered Arduino Editor")
        self.setGeometry(100, 100, 1400, 800)
        self.setMinimumSize(1200, 600)
        self.setStyleSheet("""
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0F0F23, stop:1 #1A1A2E); }
            QTextEdit { background: #1A1A2E; color: #E0E0E0; font-family: 'Consolas', 'Monaco', monospace; font-size: 15px; padding: 20px; border: 2px solid rgba(102, 126, 234, 0.2); border-radius: 10px; }
            QStatusBar { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667EEA, stop:1 #764BA2); color: white; font-weight: bold; padding: 10px; font-size: 12px; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        funcs = github()
        self.sidebar = Sidebar(funcs)
        self.sidebar.setVisible(False)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(15, 15, 15, 15)

        self.code_editor = DropTextEdit()
        self.code_editor.setPlaceholderText(
            "✨ PyDuino 2.0.0 – AI-Powered Arduino Editor ✨\n\n"
            "🎯 Drag blocks from the sidebar (Ctrl+B to toggle)\n"
            "🤖 Use AI Assistants for intelligent code help\n"
            "⚡ Write real Arduino C++ code with ease\n\n"
            "Start coding your next amazing project!"
        )
        self.code_editor.setFont(QFont("Consolas", 15))
        self.code_editor.textChanged.connect(self.on_text_changed)
        # store full code blocks from AI
        self.error_full_codes = {}

        # store suggestion patches from AI
        self.error_patches = {}


        right_layout.addWidget(self.code_editor)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 900])

        main_layout.addWidget(splitter)

        self.statusBar().showMessage("🚀 Ready • Ctrl+B = Toggle Blocks • 🤖 AI Assistants Available")
        self.setWindowIcon(QIcon("logo.png"))  # Replace with your actual logo path if available

    def on_text_changed(self):
        current_code = self.code_editor.toPlainText()
        code_block = f"\n\nCurrent code:\n```\n{current_code}\n```"
        # Optional: add auto-save or syntax highlighting here

    def update_vars(self):
        code = self.code_editor.toPlainText()
        self.code = code
        self.sidebar.update_variables(code)

    def generate_random_name(self):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))

    def extract_libraries(self, code):
        libraries = []
        matches = re.findall(r'#include\s*<([^>]+)>', code)
        for match in matches:
            libraries.append(match.replace('.h', ''))
        return libraries

    def compile_and_upload(self):
        def error(self,error):
            # Create a custom About dialog
            about_dialogs = QMessageBox(self)
            about_dialogs.setWindowTitle("Error")

            # Set a fixed size (width x height)
            about_dialogs.setFixedSize(600, 400)  # wider and taller

            # Use a custom widget for richer content
            content = QWidget()
            layout = QVBoxLayout()

            label = QLabel(
                error
            )
            label.setWordWrap(True)
            layout.addWidget(label)
            content.setLayout(layout)

            about_dialogs.layout().addWidget(content)
            about_dialogs.exec_()
        inner = ["Wire","Adafruit_Circuit_Playground", "Bridge", "Esplora", "Ethernet", "Firmata", "GSM", "Keyboard", "LiquidCrystal", "Mouse", "Robot_Control", "Robot_Motor", "RobotIRremote", "SD", "Servo", "SpacebrewYun", "Stepper", "Temboo", "TFT", "WiFi"
]
        code = self.code_editor.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "No Code", "Please write some code first!")
            return
        if not self.current_pyd_file:
            self.save_file()
            if not self.current_pyd_file:
                return

        libraries = self.extract_libraries(code)
        external = []

        for library in libraries:
            if library in inner:
                external.append(fr"libraries\{library}.h")
                libraries.remove(library)

        if self.current_ino_folder and os.path.exists(self.current_ino_folder):
            ino_path = os.path.join(self.current_ino_folder, f"{os.path.basename(self.current_ino_folder)}.ino")
        else:
            QMessageBox.critical(self, "Error", "INO folder not found. Please save the file first.")
            return

        try:
            with open(ino_path, 'w', encoding='utf-8') as f:
                f.write(code)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write .ino file:\n{e}")
            return

        self.statusBar().showMessage("🔄 Compiling and uploading...")
        self.compile_worker = CompileWorker(ino_path, libraries,external)
        self.compile_worker.finished.connect(self.on_compile_finished)
        self.compile_worker.start()

    def start_compile(self, file_path, libraries=None, externals=None):
        self.worker = CompileWorker(file_path, libraries, externals)
        self.worker.finished.connect(self.on_compile_finished)  # thread-safe
        self.worker.start()


    def on_compile_finished(self, success, message):
        # This runs in the GUI thread, safe to touch widgets
        if success:
            QMessageBox.information(self, "Success", f"✅ Compilation and upload successful!\n\n{message}")
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("✅ Upload successful!", 5000)
            self.error_text = message
            self.show_error(message)
        else:
            QMessageBox.critical(self, "Compilation Error", f"❌ Compilation failed:\n\n{message}")
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("❌ Compilation failed", 5000)
            self.error_text = message
            self.show_error(message)


    def show_error(self, error_text):
        self.error_text = error_text

        # Initialize dictionaries if they don't exist
        if not hasattr(self, 'error_full_codes'):
            self.error_full_codes = {}
        if not hasattr(self, 'error_patches'):
            self.error_patches = {}

        w = QWidget()
        w.setWindowTitle("Error")
        w.resize(600, 400)

        # Global QSS
        w.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                font-size: 14px;
                color: #ff4d4d;
            }
            QPushButton {
                background-color: #4a90e2;
                color: #ffffff;
                font-size: 14px;
                border-radius: 8px;
                padding: 8px 16px;
                border: 2px solid #357ABD;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2a5d8f;
            }
        """)
        w.setWindowIcon(QIcon("logo.png"))

        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        label = QLabel(error_text)
        label.setWordWrap(True)
        layout.addWidget(label)

        copy_btn = QPushButton("Copy Error")
        copy_btn.setFixedHeight(45)
        copy_btn.clicked.connect(lambda: self.copy_error(label, copy_btn))
        layout.addWidget(copy_btn)

        ai_btn = QPushButton("Call AI for help!")
        ai_btn.setFixedHeight(45)
        ai_btn.clicked.connect(lambda: self.send_to_ai(label, ai_btn, error_text, copy_btn))
        layout.addWidget(ai_btn)

        w.setLayout(layout)
        w.show()

        if not hasattr(self, "error_windows"):
            self.error_windows = []
        self.error_windows.append(w)


    def copy_error(self, label, btn):
        from PyQt5.QtGui import QGuiApplication
        from PyQt5.QtCore import QTimer

        QGuiApplication.clipboard().setText(label.text())
        btn.setText("Copied!")
        btn.setEnabled(False)
        QTimer.singleShot(2000, lambda: self.reset_copy_btn(btn))


    def reset_copy_btn(self, btn):
        btn.setText("Copy Error")
        btn.setEnabled(True)


    def send_to_ai(self, label, ai_btn, error_text, copy_btn):
        label.setText("Sending error to AI… sit tight 🤖")
        
        # Get current code from editor
        current_code = ""
        if hasattr(self, 'code_editor'):
            current_code = self.code_editor.toPlainText()
        elif hasattr(self, 'code'):
            current_code = self.code
        
        # Store copy_btn reference for later use
        self.current_copy_btn = copy_btn

        self.worker = AIWorker(self.secret,
                               f"Here is the error:\n\n{error_text}\n\nHere is the code:\n\n{current_code}",
                               ai_type="ERROR")
        self.worker.finished.connect(lambda text: self.ai_finished(label, ai_btn, text))
        self.worker.error.connect(lambda err: self.ai_failed(label, ai_btn, err))
        self.worker.start()


    def ai_finished(self, label, ai_btn, text):
        import re
        import random
        
        label.setStyleSheet("color:#00ffae;font-size:14px;")
        label.setText(text)
        ai_btn.setEnabled(True)
        ai_btn.setText("Call AI for help!")
        
        # Update copy button if it exists
        if hasattr(self, 'current_copy_btn') and self.current_copy_btn:
            self.current_copy_btn.setText("Copy AI Answer")
            self.current_copy_btn.clicked.disconnect()
            self.current_copy_btn.clicked.connect(lambda: self.copy_ai_response(text))

        parent_layout = label.parent().layout()

        # -------------------------
        # Full code blocks (cpp / arduino / h)
        full_pattern = r'```(?:cpp|arduino|h)\n(.*?)\n```'
        full_matches = re.findall(full_pattern, text, re.DOTALL)

        for code in full_matches:
            code_id = str(random.randint(100000, 999999))
            self.error_full_codes[code_id] = code.strip()

            replace_btn = QPushButton("🔄 Replace Whole Code")
            replace_btn.setFixedHeight(45)
            replace_btn.setStyleSheet("""
                QPushButton {
                    background-color: #667EEA;
                    color: white;
                    font-size: 14px;
                    border-radius: 8px;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5568D3;
                }
            """)

            replace_btn.clicked.connect(lambda checked, cid=code_id: self.replace_error_code(cid))
            parent_layout.addWidget(replace_btn)

        # -------------------------
        # Patch blocks (python code replacing parts)
        patch_pattern = r'```python\n(.*?)\n```'
        patch_matches = re.findall(patch_pattern, text, re.DOTALL)

        for patch_code in patch_matches:
            if 'code = code.replace' in patch_code:  # only consider patch-like suggestions
                patch_id = str(random.randint(100000, 999999))
                self.error_patches[patch_id] = patch_code.strip()

                patch_btn = QPushButton("✨ Apply Suggestion")
                patch_btn.setFixedHeight(45)
                patch_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-size: 14px;
                        border-radius: 8px;
                        padding: 8px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)

                patch_btn.clicked.connect(lambda checked, pid=patch_id: self.apply_error_patch(pid))
                parent_layout.addWidget(patch_btn)
        from libs import notify
        notify.send(message="AI has answered your question come and see!!")


    def copy_ai_response(self, text):
        from PyQt5.QtGui import QGuiApplication
        
        QGuiApplication.clipboard().setText(text)
        if hasattr(self, 'current_copy_btn') and self.current_copy_btn:
            self.current_copy_btn.setText("Copied!")
            self.current_copy_btn.setEnabled(False)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(2000, lambda: self.reset_ai_copy_btn())


    def reset_ai_copy_btn(self):
        if hasattr(self, 'current_copy_btn') and self.current_copy_btn:
            self.current_copy_btn.setText("Copy AI Answer")
            self.current_copy_btn.setEnabled(True)


    def ai_failed(self, label, ai_btn, err):
        label.setStyleSheet("color:#ff4d4d;font-size:14px;")
        label.setText("AI failed:\n" + err)
        ai_btn.setEnabled(True)
        ai_btn.setText("Call AI for help!")


    def replace_error_code(self, code_id):
        code = self.error_full_codes.get(code_id)
        if not code:
            return

        from PyQt5.QtWidgets import QMessageBox

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Replace Entire Code")
        msg.setText("🔄 Replace the entire code in the editor?")
        msg.setInformativeText("This will overwrite your current code.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox {
                background: #1A1A2E;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 13px;
            }
            QPushButton {
                background: #667EEA;
                color: white;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5568D3;
            }
        """)

        if msg.exec_() == QMessageBox.Yes:
            if hasattr(self, 'code_editor'):
                self.code_editor.setPlainText(code)


    def apply_error_patch(self, patch_id):
        patch = self.error_patches.get(patch_id)
        if not patch:
            return

        from PyQt5.QtWidgets import QMessageBox

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Apply Suggested Code")
        msg.setText("✨ Apply this AI suggestion to your code?")
        msg.setInformativeText("Only the suggested part will be replaced.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox {
                background: #1A1A2E;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 13px;
            }
            QPushButton {
                background: #4CAF50;
                color: white;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #45a049;
            }
        """)

        if msg.exec_() == QMessageBox.Yes:
            if not hasattr(self, 'code_editor'):
                return
                
            try:
                loc = {'code': self.code_editor.toPlainText()}
                exec(patch, globals(), loc)
                self.code_editor.setPlainText(loc['code'])
            except Exception as e:
                # Only append to chat if it exists
                if hasattr(self, 'chat'):
                    self.chat.append(
                        f"<div style='background: rgba(255, 107, 107, 0.15); padding: 12px; border-radius: 8px; border-left: 4px solid #FF6B6B; margin: 10px 0;'>"
                        f"<p style='color: #FF6B6B; font-weight: bold; margin: 0;'>⚠ Patch Error: {str(e)}</p>"
                        f"</div>"
                    )
                else:
                    # Fallback to showing error in message box
                    error_msg = QMessageBox()
                    error_msg.setIcon(QMessageBox.Warning)
                    error_msg.setWindowTitle("Patch Error")
                    error_msg.setText(f"⚠ Failed to apply patch: {str(e)}")
                    error_msg.exec_()

    def seria(self):
        """Serial Monitor with modern GUI"""
        import sys
        import io

        # Create main window
        serial_window = QWidget()
        serial_window.setWindowTitle("PyDuino Serial Monitor")
        serial_window.resize(800, 600)
        serial_window.setWindowIcon(QIcon("logo.png"))

        # Modern dark theme styling
        serial_window.setStyleSheet("""
            QWidget {
                background-color: #1e1e2f;
                color: #ffffff;
                font-family: 'Segoe UI', 'Consolas', monospace;
            }
            QTextEdit {
                background-color: #16213e;
                color: #00ff88;
                border: 2px solid #0f3460;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357ABD;
            }
            QPushButton:pressed {
                background-color: #2a5d8f;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QLabel {
                color: #aaa;
                font-size: 12px;
            }
            QProgressBar {
                border: 2px solid #0f3460;
                border-radius: 5px;
                text-align: center;
                background-color: #16213e;
                color: white;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667EEA, stop:1 #764BA2);
                border-radius: 3px;
            }
        """)

        # Main layout
        layout = QVBoxLayout(serial_window)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("📡 Serial Monitor Output")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #667EEA; margin-bottom: 5px;")
        layout.addWidget(header)

        # Output text area
        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setPlaceholderText("Serial output will appear here...\n\nWaiting for execution...")
        layout.addWidget(output_text)

        # Progress bar
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(True)
        progress.setFormat("Processing: %p%")
        layout.addWidget(progress)

        # Button row
        button_layout = QHBoxLayout()

        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setFixedHeight(40)
        clear_btn.clicked.connect(lambda: output_text.clear())
        button_layout.addWidget(clear_btn)

        copy_btn = QPushButton("📋 Copy Output")
        copy_btn.setFixedHeight(40)
        copy_btn.clicked.connect(lambda: self.copy_serial_output(output_text.toPlainText(), copy_btn))
        button_layout.addWidget(copy_btn)

        close_btn = QPushButton("❌ Close")
        close_btn.setFixedHeight(40)
        close_btn.clicked.connect(serial_window.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        serial_window.setLayout(layout)
        serial_window.show()

        # Animate progress bar
        def update_progress():
            val = progress.value()
            if val < 100:
                progress.setValue(val + 10)
                QTimer.singleShot(100, update_progress)
            else:
                progress.setFormat("✓ Complete")

        update_progress()

        # Execute code interpretation
        try:
            code = self.code_editor.toPlainText().strip()

            if not code:
                output_text.setPlainText("⚠️ No code to execute. Please write some code first.")
                output_text.setStyleSheet(output_text.styleSheet() + "color: #ffaa00;")
                return

            # Interpret the code
            result = self.interpreter(code)

            if result.startswith("Error"):
                output_text.setStyleSheet(output_text.styleSheet() + "color: #ff4d4d;")
                output_text.setPlainText(f"❌ {result}")
            else:
                output_text.setStyleSheet(output_text.styleSheet() + "color: #00ff88;")
                output_text.setPlainText(f"✓ Execution successful!\n\n{result}")

        except Exception as e:
            output_text.setStyleSheet(output_text.styleSheet() + "color: #ff4d4d;")
            output_text.setPlainText(f"❌ Unexpected Error:\n\n{str(e)}")

        # Store reference to prevent garbage collection
        if not hasattr(self, 'serial_windows'):
            self.serial_windows = []
        self.serial_windows.append(serial_window)


    def copy_serial_output(self, text, btn):
        """Copy serial output to clipboard"""
        from PyQt5.QtGui import QGuiApplication
        from PyQt5.QtCore import QTimer

        QGuiApplication.clipboard().setText(text)
        btn.setText("✓ Copied!")
        btn.setEnabled(False)
        QTimer.singleShot(2000, lambda: self.reset_serial_copy_btn(btn))


    def reset_serial_copy_btn(self, btn):
        """Reset copy button"""
        btn.setText("📋 Copy Output")
        btn.setEnabled(True)


    def interpreter(self, text):
        """Interpret PyDuino serial code"""
        import sys
        import io
        import re

        # 1. Check entry point
        if "Serial.code_begin()" not in text:
            return "Error: Serial.code_begin() not found in code.\n\nPlease add 'Serial.code_begin()' to mark the start of your serial code."

        # 2. Remove language marker
        text = text.replace("Serial.code_begin()", "")

        # 3. Replace initialize syntax
        text = re.sub(
            r"initialize\s+(\w+)\s+@py",
            r"\1 = serials.Serial()",
            text
        )

        # 4. Auto-import serial
        final_code = "import serial as serials\n" + text

        # 5. Capture output
        stdout_backup = sys.stdout
        stderr_backup = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            exec(final_code, {}, {})
            output = sys.stdout.getvalue()
            errors = sys.stderr.getvalue()
        except Exception as e:
            output = ""
            errors = str(e)
        finally:
            sys.stdout = stdout_backup
            sys.stderr = stderr_backup

        if errors:
            return f"Error during execution:\n\n{errors}"

        if not output:
            return "(No output produced)"

        return output.strip()

    def create_menu(self):
        mb = self.menuBar()

        # File menu
        file = mb.addMenu("📁 File")
        for text, shortcut, func in [
            ("🆕 New", "Ctrl+N", self.new_file),
            ("📂 Open...", "Ctrl+O", self.open_file),
            ("💾 Save", "Ctrl+S", self.save_file),
            ("💾 Save As...", "Ctrl+Shift+S", self.save_as),
            ("🚪 Exit", "Ctrl+Q", self.close)
        ]:
            a = QAction(text, self)
            a.setShortcut(shortcut)
            a.triggered.connect(func)
            file.addAction(a)

        # Edit menu
        edit = mb.addMenu("✏️ Edit")
        undo_act = QAction("↶ Undo", self)
        undo_act.setShortcut("Ctrl+Z")
        undo_act.triggered.connect(self.code_editor.undo)
        edit.addAction(undo_act)

        redo_act = QAction("↷ Redo", self)
        redo_act.setShortcut("Ctrl+Y")
        redo_act.triggered.connect(self.code_editor.redo)
        edit.addAction(redo_act)

        # View menu
        view = mb.addMenu("👁️ View")
        self.toggle_sidebar_act = QAction("🧩 Show Blocks Panel", self)
        self.toggle_sidebar_act.setShortcut("Ctrl+B")
        self.toggle_sidebar_act.triggered.connect(self.toggle_sidebar)
        view.addAction(self.toggle_sidebar_act)

        # Tools menu
        tools = mb.addMenu("🔧 Tools")
        compile_act = QAction("⚡ Compile & Upload", self)
        compile_act.setShortcut("Ctrl+U")
        compile_act.triggered.connect(self.compile_and_upload)
        tools.addAction(compile_act)
        tools.addSeparator()
        serial = QAction("Serial", self)
        serial.setShortcut("Ctrl+Shift+S")
        serial.triggered.connect(self.seria)
        tools.addAction(serial)
        tools.addSeparator()

        arduino_act = QAction("🤖 Arduino AI Assistant", self)
        arduino_act.setShortcut("Ctrl+Shift+A")
        arduino_act.triggered.connect(self.open_arduino_assistant)
        tools.addAction(arduino_act)

        h_act = QAction("📄 .h Header AI Assistant", self)
        h_act.setShortcut("Ctrl+Shift+H")
        h_act.triggered.connect(self.open_h_assistant)
        tools.addAction(h_act)

        python_act = QAction("🐍 Python Serial AI Assistant", self)
        python_act.setShortcut("Ctrl+Shift+P")
        python_act.triggered.connect(self.open_python_assistant)
        tools.addAction(python_act)

        tools.addSeparator()
        setup_arduino = QAction("🛠️ Setup Arduino CLI And Install Dependencies of Pyduino IDE (One-time only)", self)
        setup_arduino.setShortcut("Ctrl+Shift+L")
        setup_arduino.triggered.connect(self.set_up_arduino_cli)
        tools.addAction(setup_arduino)

        # Help menu
        help_menu = mb.addMenu("❓ Help")
        about_pyduino_act = QAction("ℹ️ About PyDuino IDE", self)
        about_pyduino_act.triggered.connect(self.about_pyduino)
        help_menu.addAction(about_pyduino_act)

        about_arduino_act = QAction("🔌 About Arduino", self)
        about_arduino_act.triggered.connect(self.about_arduino)
        help_menu.addAction(about_arduino_act)

    def about_pyduino(self):
        # Create a custom About dialog
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("About PyDuino IDE")

        # Set a fixed size (width x height)
        about_dialog.setFixedSize(600, 400)  # wider and taller

        # Use a custom widget for richer content
        content = QWidget()
        layout = QVBoxLayout()

        label = QLabel(
            "<h1 style='color: #2E8B57;'>PyDuino IDE 2.0.0</h1>"
            "<h3>AI-Powered Arduino Development Environment</h3>"
            "<p>A modern IDE for writing, compiling, and uploading Arduino sketches with block-based help and AI assistants.</p>"
            "<p>Features:🧩 Blocks + Text code • 🤖 AI suggestions • Blocks having their on description on hover • 3 Different AI's to help you with 3 different tasks • When you click send with code the AI understands the code and gives you a code and buttons will appear like replace a segment or replace whole code or even run code. • Added Error AI to help with Errors</p>"
            "<p>Want to use the AI at max use these commands:'use your code runner feature to do: (x)' now the AI can run python code using your permission if denied the code wont run,'use your replacing feature to fix/add (x)': now the AI can replace things on oyur permission so you dont have to do that manually!</p>"
            "<hr>"
            "<p>Built with PyQt5 • © 2025 PyDuino Project </p>"
            "<p>Have doubts? Contact us at pyduino.contact@gmail.com !</p>"
            "<p style='font-style:italic;'>Enjoy coding smarter and faster! 🚀</p>"
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        content.setLayout(layout)

        about_dialog.layout().addWidget(content)
        about_dialog.exec_()


    def about_arduino(self):
        QMessageBox.about(self, "About Arduino",
                          "<h2 style='color:#00979D;'>Arduino Platform</h2>"
                          "<p><img src='https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Arduino_Logo_Registered.svg/1200px-Arduino_Logo_Registered.svg.png' width='200' align='right' style='margin-left:20px;'></p>"
                          "<p><b>Arduino</b> is an open-source electronics platform based on easy-to-use hardware and software.</p>"
                          "<p>Created in 2005 at the Interaction Design Institute Ivrea (Italy) to make prototyping accessible to students, artists, and hobbyists.</p>"
                          "<ul>"
                          "<li><b>Hardware:</b> Microcontroller boards (Uno, Nano, Mega, etc.)</li>"
                          "<li><b>Software:</b> Arduino IDE (C++-based) and compatible tools</li>"
                          "<li><b>Community:</b> Millions of users worldwide</li>"
                          "<li><b>Website:</b> <a href='https://www.arduino.cc'>www.arduino.cc</a></li>"
                          "</ul>"
                          "<p>Common applications: robotics, IoT, sensors, home automation, interactive art, and education.</p>"
                          "<hr>"
                          "<p>PyDuino enhances the Arduino experience with AI assistance and modern UI! ✨</p>")

    def create_toolbar(self):
        toolbar = self.addToolBar("Quick Tools")
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setMovable(False)

        blocks_btn = QPushButton("🧩 Blocks")
        blocks_btn.clicked.connect(self.toggle_sidebar)
        blocks_btn.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #667EEA,stop:1 #764BA2); "
            "color:white; border:none; border-radius:8px; padding:10px 20px; font-weight:bold;")
        toolbar.addWidget(blocks_btn)
        toolbar.addSeparator()

        compile_btn = QPushButton("⚡ Compile & Upload")
        compile_btn.clicked.connect(self.compile_and_upload)
        compile_btn.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00D9FF,stop:1 #0099FF); "
            "color:white; border:none; border-radius:8px; padding:12px 25px; font-weight:bold;")
        toolbar.addWidget(compile_btn)
        toolbar.addSeparator()

        gradient_style = blocks_btn.styleSheet()
        for text, func in [
            ("🤖 Arduino AI", self.open_arduino_assistant),
            ("📄 .h AI", self.open_h_assistant),
            ("🐍 Python AI", self.open_python_assistant)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            btn.setStyleSheet(gradient_style)
            toolbar.addWidget(btn)

    def toggle_sidebar(self):
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        self.toggle_sidebar_act.setText("🧩 Hide Blocks Panel" if visible else "🧩 Show Blocks Panel")

    def set_up_arduino_cli(self):
        ZIP_URL = "https://github.com/programmercoder945/libraries/archive/refs/heads/main.zip"
        ZIP_FILE = "libraries.zip"
        EXTRACT_DIR = "libraries"


        def download_zip(url, out_file):
            print(f"⬇️ Downloading from {url}")

            with httpx.stream("GET", url, follow_redirects=True) as response:
                response.raise_for_status()
                with open(out_file, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)

            print(f"✅ Saved as {out_file}")


        def unzip(zip_path, extract_to):
            print(f"📂 Extracting to {extract_to}")
            os.makedirs(extract_to, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_to)
        download_zip(ZIP_URL, ZIP_FILE)
        unzip(ZIP_FILE, EXTRACT_DIR)

        os.makedirs("libs",exist_ok=True)
        with open(r"libs\notify.py","w") as f:
            f.write("""
from win10toast import ToastNotifier
import os

toaster = ToastNotifier()

icon_path = os.path.abspath("logo.ico")  # must be .ico

def send(message, title="PyDuino IDE", durations=6):
    toaster.show_toast(
        title,
        message,
        icon_path=icon_path,
        duration=durations,
        threaded=True
    )


""".strip())

        try:
            os.makedirs("assets",exist_ok=True)
        except Exception:
            pass
        funcs = github()
        with open(r"libs\runner.py","w",encoding="utf-8") as f:
            f.write(r"""import subprocess
import os
import shutil
import serial.tools.list_ports

arduino_cli = "arduino-cli.exe"


# =========================
# Custom Error Class
# =========================
class ArduinoError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


# =========================
# Error Wrapper Algorithm
# =========================
def error_guard(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ArduinoError:
            raise
        except Exception as e:
            raise ArduinoError(f"[{func.__name__}] Unexpected error:\n{e}")
    return wrapper


# =========================
# 1. Find Arduino Port
# =========================
@error_guard
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description:
            return port.device
    raise ArduinoError("Arduino not detected on any COM port.")


# =========================
# 2. Install Libraries
# =========================
@error_guard
def install_libraries(libraries):
    for lib in libraries:
        cmd = [arduino_cli, "lib", "install", lib]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ArduinoError(
                f"Failed to install library '{lib}':\n{result.stderr}"
            )


# =========================
# 3. Install External Libraries
# =========================
@error_guard
def install_external_libraries(sketch_path, external_libraries):
    sketch_dir = os.path.dirname(sketch_path)

    for lib_path in external_libraries:
        if not os.path.exists(lib_path):
            raise ArduinoError(f"External library not found: {lib_path}")

        lib_name = os.path.basename(lib_path)
        dest_path = os.path.join(sketch_dir, lib_name)

        try:
            shutil.copy2(lib_path, dest_path)
        except Exception as e:
            raise ArduinoError(f"Failed copying {lib_name}:\n{e}")


# =========================
# 4. Compile Sketch
# =========================
@error_guard
def compile_sketch(sketch_path):
    cmd = [
        arduino_cli,
        "compile",
        "--fqbn",
        "arduino:avr:uno",
        sketch_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise ArduinoError(
            f"Compilation failed:\n{result.stderr}"
        )


# =========================
# 5. Upload Sketch
# =========================
@error_guard
def upload_sketch(sketch_path, port):
    cmd = [
        arduino_cli,
        "upload",
        "-p",
        port,
        "--fqbn",
        "arduino:avr:uno",
        sketch_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise ArduinoError(
            f"Upload failed:\n{result.stderr}"
        )


# =========================
# Main Runner
# =========================
def run(sketch, add_library=None, add_external_library=None):
    try:
        if add_library:
            install_libraries(add_library)

        if add_external_library:
            install_external_libraries(sketch, add_external_library)

        port = find_arduino_port()
        compile_sketch(sketch)
        upload_sketch(sketch, port)

        return "✅ Build & Upload Successful"

    except ArduinoError as e:
        return f"❌ ERROR:\n{e.message}"

            """.strip())
        with open("arduino_clis.py","w") as f:
            f.write("""import subprocess

arduino_cli = "arduino-cli.exe"

commands = [
    [arduino_cli, "core", "update-index"],
    [arduino_cli, "core", "install", "arduino:avr"]
]

for cmd in commands:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("Error:", result.stderr)
    
    if result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        break
""".strip())
        try:
            import arduino_clis  # Your custom module
            QMessageBox.information(self, "Arduino CLI Setup", "Arduino-CLI setup completed successfully!")
        except ImportError:
            reply = QMessageBox.question(
                self, "Arduino-CLI Not Found",
                "The 'arduino_clis' module was not found.\n\n"
                "Would you like to open the official Arduino CLI installation guide?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                webbrowser.open("https://arduino.github.io/arduino-cli/latest/installation/")
        except Exception as e:
            QMessageBox.critical(self, "Setup Failed", f"An error occurred during Arduino CLI setup:\n\n{str(e)}")

    def open_arduino_assistant(self):
        if not self.arduino_assistant:
            self.arduino_assistant = AssistantWindow(self, "arduino", "Arduino AI Assistant", "Arduino Code Expert")
        self.arduino_assistant.show()
        self.arduino_assistant.raise_()
        self.arduino_assistant.activateWindow()

    def open_h_assistant(self):
        if not self.h_assistant:
            self.h_assistant = AssistantWindow(self, "h", "Arduino .h AI Assistant", ".h Header Expert")
        self.h_assistant.show()
        self.h_assistant.raise_()
        self.h_assistant.activateWindow()

    def open_python_assistant(self):
        if not self.python_assistant:
            self.python_assistant = AssistantWindow(self, "python", "Python Serial AI Assistant", "Python Serial Expert")
        self.python_assistant.show()
        self.python_assistant.raise_()
        self.python_assistant.activateWindow()

    def new_file(self):
        if self.code_editor.toPlainText().strip():
            if QMessageBox.question(self, "New File", "Discard current unsaved code?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                return
        self.code_editor.clear()
        self.current_file = None
        self.current_pyd_file = None
        self.current_ino_folder = None
        self.setWindowTitle("PyDuino 2.0.0 - Untitled")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PyDuino File", "", "PyDuino Files (*.pyd);;Arduino Files (*.ino);;All Files (*)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.code_editor.setPlainText(f.read())
                if path.endswith('.pyd'):
                    self.current_pyd_file = path
                    base_name = os.path.splitext(os.path.basename(path))[0]
                    dir_path = os.path.dirname(path)
                    for item in os.listdir(dir_path):
                        item_path = os.path.join(dir_path, item)
                        if os.path.isdir(item_path) and item.startswith(base_name):
                            self.current_ino_folder = item_path
                            break
                else:
                    self.current_file = path
                self.setWindowTitle(f"PyDuino 2.0.0 - {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")

    def save_file(self):
        if not self.current_pyd_file:
            return self.save_as()
        try:
            code = self.code_editor.toPlainText()
            with open(self.current_pyd_file, "w", encoding="utf-8") as f:
                f.write(code)
            if self.current_ino_folder:
                ino_path = os.path.join(self.current_ino_folder, f"{os.path.basename(self.current_ino_folder)}.ino")
                with open(ino_path, "w", encoding="utf-8") as f:
                    f.write(code)
            self.statusBar().showMessage("✅ Saved successfully!", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Sketch As", "", "PyDuino Files (*.pyd)")
        if path:
            if not path.lower().endswith(".pyd"):
                path += ".pyd"
            try:
                code = self.code_editor.toPlainText()
                with open(path, "w", encoding="utf-8") as f:
                    f.write(code)
                self.current_pyd_file = path
                base_name = os.path.splitext(os.path.basename(path))[0]
                random_suffix = self.generate_random_name()
                folder_name = f"{base_name}_{random_suffix}"
                dir_path = os.path.dirname(path)
                self.current_ino_folder = os.path.join(dir_path, folder_name)
                os.makedirs(self.current_ino_folder, exist_ok=True)
                ino_path = os.path.join(self.current_ino_folder, f"{folder_name}.ino")
                with open(ino_path, "w", encoding="utf-8") as f:
                    f.write(code)
                self.setWindowTitle(f"PyDuino 2.0.0 - {os.path.basename(path)}")
                self.statusBar().showMessage("✅ Saved as new file!", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    from PyQt5.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(26, 26, 46))
    palette.setColor(QPalette.WindowText, QColor(224, 224, 224))
    palette.setColor(QPalette.Base, QColor(26, 26, 46))
    palette.setColor(QPalette.Text, QColor(224, 224, 224))
    palette.setColor(QPalette.Button, QColor(42, 42, 64))
    palette.setColor(QPalette.ButtonText, QColor(224, 224, 224))
    palette.setColor(QPalette.Highlight, QColor(102, 126, 234))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    win = IjraaGUI()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
