"""
By Dr. Eric O. Flores email: <eoftoro@gmail.com>
Version 3.2
Updated:  12/24/2025
Copyright (c) 2024 drericflores
MIT License

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import sys
import os
import json
import uuid
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QListWidget, QListWidgetItem, QPushButton, QLabel,
    QFileDialog, QMessageBox, QAction, QToolBar, QInputDialog, QMenu,
    QDialog, QDialogButtonBox
)
from PyQt5.QtGui import (
    QTextDocument, QImage, QDesktopServices, QFont,
    QPainter, QPen, QBrush, QTextCursor, QTextImageFormat
)
from PyQt5.QtCore import Qt, QUrl, QRect, QSize, QPoint


APP_NAME = "Rolocard"
APP_VERSION = "3.2"
SCHEMA_VERSION = 3


# ---------------- Utilities ----------------

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_basename(path: str) -> str:
    try:
        return os.path.basename(path)
    except Exception:
        return str(path)


def new_card() -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "content": "",
        "images": {},          # {img_id: {"filename": "...", "data": "<base64>"}}
        "attachments": [],     # list[str]
        "tags": [],            # list[str] (kept for forward compatibility)
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def ensure_card_shape(card: Any) -> Dict[str, Any]:
    """
    Normalize older decks and tolerate mixed schemas.
    Oldest legacy: {"content": "...", "attachments": [...]}
    New schema:    {"id":..., "content":..., "images":{...}, ...}
    """
    if not isinstance(card, dict):
        return new_card()

    out = dict(card)

    if not out.get("id"):
        out["id"] = str(uuid.uuid4())

    content = out.get("content", "")
    if not isinstance(content, str):
        content = str(content)
    out["content"] = content

    attachments = out.get("attachments", [])
    if not isinstance(attachments, list):
        attachments = []
    out["attachments"] = [str(a).strip() for a in attachments if str(a).strip()]

    tags = out.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    out["tags"] = [str(t).strip() for t in tags if str(t).strip()]

    images = out.get("images", {})
    if not isinstance(images, dict):
        images = {}
    # keep whatever keys exist; validate basic shape
    clean_images = {}
    for k, v in images.items():
        if not isinstance(k, str):
            continue
        if isinstance(v, dict) and isinstance(v.get("data", ""), str):
            clean_images[k] = {
                "filename": str(v.get("filename", "")),
                "data": v.get("data", ""),
            }
    out["images"] = clean_images

    out.setdefault("created_at", "")
    out.setdefault("updated_at", "")

    return out


def load_deck_any(data: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Accept:
      - dict with "cards": schema decks
      - list of cards: legacy decks
    Returns: (cards, meta)
    """
    if isinstance(data, dict) and isinstance(data.get("cards"), list):
        cards = [ensure_card_shape(c) for c in data["cards"]]
        meta = dict(data)
        meta.pop("cards", None)
        return cards, meta

    if isinstance(data, list):
        return [ensure_card_shape(c) for c in data], {}

    raise ValueError("Unrecognized deck format (expected list, or dict with 'cards').")


# ---------------- Document with image loader ----------------

class CardDocument(QTextDocument):
    def __init__(self, card: Dict[str, Any]):
        super().__init__()
        self.card = card

    def loadResource(self, res_type, name):
        if res_type == QTextDocument.ImageResource:
            key = name.toString()
            # We store images as image://<id>
            if key.startswith("image://"):
                img_id = key.replace("image://", "", 1)
                info = self.card.get("images", {}).get(img_id)
                if info and isinstance(info.get("data", ""), str):
                    try:
                        raw = base64.b64decode(info["data"])
                        img = QImage()
                        img.loadFromData(raw)
                        return img
                    except Exception:
                        pass
        return super().loadResource(res_type, name)


# ---------------- Attachment Manager Dialog ----------------

class AttachmentManagerDialog(QDialog):
    def __init__(self, parent: QWidget, attachments: List[str]):
        super().__init__(parent)
        self.setWindowTitle("Attachment Manager")
        self.resize(640, 420)
        self._attachments = attachments

        layout = QVBoxLayout(self)
        self.listbox = QListWidget(self)
        layout.addWidget(self.listbox)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add…", self)
        self.btn_remove = QPushButton("Remove", self)
        self.btn_open = QPushButton("Open", self)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_open)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_add.clicked.connect(self.add_attachment)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_open.clicked.connect(self.open_selected)
        self.listbox.itemDoubleClicked.connect(lambda _: self.open_selected())

        self.refresh()

    def refresh(self):
        self.listbox.clear()
        for p in self._attachments:
            item = QListWidgetItem(f"{safe_basename(p)}   —   {p}")
            item.setToolTip(p)
            item.setData(Qt.UserRole, p)
            self.listbox.addItem(item)

    def add_attachment(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Attachment")
        if filename:
            if filename not in self._attachments:
                self._attachments.append(filename)
            self.refresh()

    def remove_selected(self):
        item = self.listbox.currentItem()
        if not item:
            return
        p = item.data(Qt.UserRole)
        if not p:
            return
        try:
            self._attachments.remove(p)
        except ValueError:
            pass
        self.refresh()

    def open_selected(self):
        item = self.listbox.currentItem()
        if not item:
            return
        p = item.data(Qt.UserRole)
        if not p:
            return
        if not os.path.exists(p):
            QMessageBox.warning(self, "Missing File", f"File not found:\n{p}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(p))


# ---------------- Rich editor with mouse-resize handle ----------------

class CardTextEdit(QTextEdit):
    """
    Inline-image editor with:
      - Drag & drop images into the document (embedded, base64 in card)
      - Click image to select (shows resize handles)
      - Drag bottom-right handle to resize with mouse
      - Ctrl+click a link to open it (attachments are links)

    This implements mouse-resize in a robust way by:
      - selecting CharacterUnderCursor at the object replacement char
      - applying QTextImageFormat width/height back to that char
    """
    HANDLE = 10          # handle square size
    HANDLE_HIT_PAD = 6   # extra hit padding around handle
    MIN_W = 24
    MIN_H = 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        self._img_pos: Optional[int] = None           # selectionStart of image char
        self._resizing: bool = False
        self._drag_start_mouse: Optional[QPoint] = None
        self._drag_start_size: Optional[QSize] = None

    def _cursor_image(self, pos: QPoint) -> Optional[QTextCursor]:
        c = self.cursorForPosition(pos)
        c.select(QTextCursor.CharacterUnderCursor)
        fmt = c.charFormat()
        if not fmt.isImageFormat():
            return None
        imgfmt = QTextImageFormat(fmt)
        if not imgfmt.name():
            return None
        return c

    def _image_rect(self, c: QTextCursor) -> Optional[QRect]:
        if not c or not c.charFormat().isImageFormat():
            return None
        r = self.cursorRect(c)
        if r.isNull():
            return None

        imgfmt = QTextImageFormat(c.charFormat())
        w = float(imgfmt.width() or 0)
        h = float(imgfmt.height() or 0)
        if w > 0:
            r.setWidth(int(round(w)))
        if h > 0:
            r.setHeight(int(round(h)))
        return r

    def _handle_rect(self, img_rect: QRect) -> QRect:
        return QRect(
            img_rect.right() - self.HANDLE,
            img_rect.bottom() - self.HANDLE,
            self.HANDLE,
            self.HANDLE
        )

    def _hit_handle(self, img_rect: QRect, pos: QPoint) -> bool:
        hr = self._handle_rect(img_rect).adjusted(
            -self.HANDLE_HIT_PAD, -self.HANDLE_HIT_PAD,
            self.HANDLE_HIT_PAD, self.HANDLE_HIT_PAD
        )
        return hr.contains(pos)

    def _apply_image_size(self, img_pos: int, w: float, h: float) -> bool:
        doc = self.document()
        c = QTextCursor(doc)
        c.setPosition(img_pos)
        c.select(QTextCursor.CharacterUnderCursor)

        if not c.charFormat().isImageFormat():
            return False

        imgfmt = QTextImageFormat(c.charFormat())
        if not imgfmt.name():
            return False

        imgfmt.setWidth(float(w))
        imgfmt.setHeight(float(h))
        c.setCharFormat(imgfmt)
        self.setTextCursor(c)

        parent = self.parent()
        if parent and hasattr(parent, "_mark_dirty"):
            parent._mark_dirty()

        self.viewport().update()
        return True

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._img_pos is None:
            return

        c = QTextCursor(self.document())
        c.setPosition(self._img_pos)
        c.select(QTextCursor.CharacterUnderCursor)
        if not c.charFormat().isImageFormat():
            self._img_pos = None
            return

        r = self._image_rect(c)
        if not r:
            return

        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(Qt.blue, 1, Qt.DashLine))
        p.drawRect(r.adjusted(0, 0, -1, -1))

        handle = self._handle_rect(r)
        p.setPen(QPen(Qt.blue, 1))
        p.setBrush(QBrush(Qt.white))
        p.drawRect(handle)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            img_cursor = self._cursor_image(e.pos())
            if img_cursor:
                self._img_pos = img_cursor.selectionStart()
                r = self._image_rect(img_cursor)
                if r and self._hit_handle(r, e.pos()):
                    self._resizing = True
                    self._drag_start_mouse = e.pos()

                    imgfmt = QTextImageFormat(img_cursor.charFormat())
                    w = int(imgfmt.width() or r.width() or 1)
                    h = int(imgfmt.height() or r.height() or 1)
                    self._drag_start_size = QSize(max(1, w), max(1, h))

                    self.viewport().setCursor(Qt.SizeFDiagCursor)
                    self.viewport().update()
                    return
                else:
                    self._resizing = False
                    self.viewport().setCursor(Qt.ArrowCursor)
                    self.viewport().update()

        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        img_cursor = self._cursor_image(e.pos())
        if not self._resizing and img_cursor:
            r = self._image_rect(img_cursor)
            if r and self._hit_handle(r, e.pos()):
                self.viewport().setCursor(Qt.SizeFDiagCursor)
            else:
                self.viewport().setCursor(Qt.ArrowCursor)

        if self._resizing and self._img_pos is not None and self._drag_start_mouse and self._drag_start_size:
            dx = e.pos().x() - self._drag_start_mouse.x()
            dy = e.pos().y() - self._drag_start_mouse.y()
            new_w = max(self.MIN_W, self._drag_start_size.width() + dx)
            new_h = max(self.MIN_H, self._drag_start_size.height() + dy)
            self._apply_image_size(self._img_pos, float(new_w), float(new_h))
            return

        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        # Ctrl+click: open link/attachment
        if e.button() == Qt.LeftButton and (e.modifiers() & Qt.ControlModifier):
            href = self.anchorAt(e.pos())
            if href:
                QDesktopServices.openUrl(QUrl(href))
                return

        if self._resizing:
            self._resizing = False
            self._drag_start_mouse = None
            self._drag_start_size = None
            self.viewport().unsetCursor()
            self.viewport().update()

        super().mouseReleaseEvent(e)

    def contextMenuEvent(self, e):
        menu = self.createStandardContextMenu()
        img_cursor = self._cursor_image(e.pos())
        if img_cursor:
            menu.addSeparator()
            act_resize = QAction("Resize…", self)
            act_reset = QAction("Reset Size (intrinsic)", self)
            act_remove = QAction("Remove Image", self)
            menu.addAction(act_resize)
            menu.addAction(act_reset)
            menu.addAction(act_remove)

            def do_resize():
                r = self._image_rect(img_cursor) or QRect(0, 0, 200, 200)
                imgfmt = QTextImageFormat(img_cursor.charFormat())
                cur_w = int(imgfmt.width() or r.width() or 200)
                cur_h = int(imgfmt.height() or r.height() or 200)
                w, ok = QInputDialog.getInt(self, "Resize Image", "Width (px):", cur_w, 20, 5000, 1)
                if not ok:
                    return
                h, ok = QInputDialog.getInt(self, "Resize Image", "Height (px):", cur_h, 20, 5000, 1)
                if not ok:
                    return
                self._apply_image_size(img_cursor.selectionStart(), float(w), float(h))

            def do_reset():
                pos = img_cursor.selectionStart()
                doc = self.document()
                c = QTextCursor(doc)
                c.setPosition(pos)
                c.select(QTextCursor.CharacterUnderCursor)
                if not c.charFormat().isImageFormat():
                    return
                imgfmt = QTextImageFormat(c.charFormat())
                imgfmt.setWidth(0.0)
                imgfmt.setHeight(0.0)
                c.setCharFormat(imgfmt)
                parent = self.parent()
                if parent and hasattr(parent, "_mark_dirty"):
                    parent._mark_dirty()
                self.viewport().update()

            def do_remove():
                doc = self.document()
                c = QTextCursor(doc)
                c.setPosition(img_cursor.selectionStart())
                c.select(QTextCursor.CharacterUnderCursor)
                c.removeSelectedText()
                self._img_pos = None
                parent = self.parent()
                if parent and hasattr(parent, "_mark_dirty"):
                    parent._mark_dirty()
                self.viewport().update()

            act_resize.triggered.connect(do_resize)
            act_reset.triggered.connect(do_reset)
            act_remove.triggered.connect(do_remove)

        menu.exec_(e.globalPos())

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            return
        super().dragEnterEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            parent = self.parent()
            for u in e.mimeData().urls():
                p = u.toLocalFile()
                if p and os.path.isfile(p):
                    if is_image_path(p):
                        if parent and hasattr(parent, "insert_image_from_file"):
                            parent.insert_image_from_file(p)
                    else:
                        if parent and hasattr(parent, "attach_file_path"):
                            parent.attach_file_path(p)
            e.acceptProposedAction()
            return
        super().dropEvent(e)


# ---------------- Main Application ----------------


class RolocardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1100, 820)

        self.cards: List[Dict[str, Any]] = []
        self.index: int = 0
        self.deck_path: Optional[str] = None
        self.deck_meta: Dict[str, Any] = {}

        self._loading_guard = False
        self.deck_dirty = False

        self.init_ui()
        self.new_deck()

    # ---------------- UI ----------------

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Top row: title + basic actions
        top = QHBoxLayout()
        self.card_label = QLabel("Card 1", self)
        top.addWidget(self.card_label)
        top.addStretch(1)
        root.addLayout(top)

        # Editor (single “surface” for text + media)
        self.editor = CardTextEdit(self)
        self.editor.setAcceptRichText(True)
        self.editor.setUndoRedoEnabled(True)
        self.editor.textChanged.connect(self._mark_dirty)
        root.addWidget(self.editor, 1)

        # Bottom: overview list (this is your “second pane” concept)
        root.addWidget(QLabel("Cards (overview):", self))
        self.overview = QListWidget()
        self.overview.itemSelectionChanged.connect(self.select_card)
        root.addWidget(self.overview, 0)

        # Bottom controls
        row = QHBoxLayout()
        root.addLayout(row)

        for label, fn in [
            ("New", self.new_card),
            ("Prev", self.prev_card),
            ("Next", self.next_card),
            ("Duplicate", self.duplicate_card),
            ("Insert Image", self.insert_image),
            ("Attach File", self.attach_file),
            ("Manage Attachments", self.manage_attachments),
            ("Save", self.save_deck),
            ("Open", self.open_deck),
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            row.addWidget(b)

        self.create_menus_and_toolbar()

    def create_menus_and_toolbar(self):
        # Menus
        mb = self.menuBar()

        filem = mb.addMenu("File")
        act_open = QAction("Open…", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.open_deck)
        filem.addAction(act_open)

        act_save = QAction("Save", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self.save_deck)
        filem.addAction(act_save)

        act_save_as = QAction("Save As…", self)
        act_save_as.triggered.connect(self.save_deck_as)
        filem.addAction(act_save_as)

        filem.addSeparator()

        act_new = QAction("New Deck", self)
        act_new.triggered.connect(self.new_deck)
        filem.addAction(act_new)

        act_close = QAction("Close Deck", self)
        act_close.setShortcut("Ctrl+W")
        act_close.triggered.connect(self.close_deck)
        filem.addAction(act_close)

        filem.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        filem.addAction(act_quit)

        editm = mb.addMenu("Edit")
        act_undo = QAction("Undo", self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(self.editor.undo)
        editm.addAction(act_undo)

        act_redo = QAction("Redo", self)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(self.editor.redo)
        editm.addAction(act_redo)

        act_dup = QAction("Duplicate Card", self)
        act_dup.setShortcut("Ctrl+D")
        act_dup.triggered.connect(self.duplicate_card)
        editm.addAction(act_dup)

        insertm = mb.addMenu("Insert")
        act_ins_img = QAction("Image…", self)
        act_ins_img.setShortcut("Ctrl+I")
        act_ins_img.triggered.connect(self.insert_image)
        insertm.addAction(act_ins_img)

        act_attach = QAction("Attachment…", self)
        act_attach.triggered.connect(self.attach_file)
        insertm.addAction(act_attach)

        helpm = mb.addMenu("Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self.show_about)
        helpm.addAction(act_about)

        # Toolbar (formatting)
        tb = QToolBar("Formatting", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        act_bold = QAction("B", self)
        act_bold.setCheckable(True)
        act_bold.triggered.connect(self.toggle_bold)
        tb.addAction(act_bold)

        act_italic = QAction("I", self)
        act_italic.setCheckable(True)
        act_italic.triggered.connect(self.toggle_italic)
        tb.addAction(act_italic)

        act_under = QAction("U", self)
        act_under.setCheckable(True)
        act_under.triggered.connect(self.toggle_underline)
        tb.addAction(act_under)

        tb.addSeparator()

        act_ins_img2 = QAction("Img", self)
        act_ins_img2.triggered.connect(self.insert_image)
        tb.addAction(act_ins_img2)

        tb.addSeparator()

        act_undo2 = QAction("Undo", self)
        act_undo2.triggered.connect(self.editor.undo)
        tb.addAction(act_undo2)

        act_redo2 = QAction("Redo", self)
        act_redo2.triggered.connect(self.editor.redo)
        tb.addAction(act_redo2)

        self._fmt_actions = (act_bold, act_italic, act_under)
        self.editor.currentCharFormatChanged.connect(self._sync_format_actions)

    def _sync_format_actions(self, fmt):
        if not hasattr(self, "_fmt_actions"):
            return
        b, i, u = self._fmt_actions
        b.blockSignals(True)
        i.blockSignals(True)
        u.blockSignals(True)
        try:
            b.setChecked(fmt.fontWeight() == QFont.Bold)
            i.setChecked(fmt.fontItalic())
            u.setChecked(fmt.fontUnderline())
        finally:
            b.blockSignals(False)
            i.blockSignals(False)
            u.blockSignals(False)

    # ---------------- Formatting ----------------

    def toggle_bold(self):
        c = self.editor.textCursor()
        fmt = c.charFormat()
        fmt.setFontWeight(QFont.Normal if fmt.fontWeight() == QFont.Bold else QFont.Bold)
        c.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_italic(self):
        c = self.editor.textCursor()
        fmt = c.charFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        c.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_underline(self):
        c = self.editor.textCursor()
        fmt = c.charFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        c.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    # ---------------- Dirty / close protection ----------------

    def _mark_dirty(self):
        if self._loading_guard:
            return
        self.deck_dirty = True

    def _confirm_discard_or_save(self, action_name: str) -> bool:
        if not self.deck_dirty:
            return True
        m = QMessageBox(self)
        m.setIcon(QMessageBox.Warning)
        m.setWindowTitle("Unsaved Changes")
        m.setText(f"You have unsaved changes. What would you like to do before {action_name}?")
        b_save = m.addButton("Save", QMessageBox.AcceptRole)
        b_discard = m.addButton("Discard", QMessageBox.DestructiveRole)
        b_cancel = m.addButton("Cancel", QMessageBox.RejectRole)
        m.exec_()
        clicked = m.clickedButton()
        if clicked == b_save:
            return self.save_deck()
        if clicked == b_discard:
            return True
        return False

    def closeEvent(self, e):
        if self._confirm_discard_or_save("quitting"):
            e.accept()
        else:
            e.ignore()

    # ---------------- Card handling ----------------

    def new_deck(self):
        if not self._confirm_discard_or_save("creating a new deck"):
            return
        self.cards = [new_card()]
        self.index = 0
        self.deck_path = None
        self.deck_meta = {}
        self.deck_dirty = False
        self.load_card()


    def close_deck(self):
        """Close the current deck and start a fresh one (keeps the app open)."""
        if not self._confirm_discard_or_save("closing the deck"):
            return
        self.cards = [new_card()]
        self.index = 0
        self.deck_path = None
        self.deck_meta = {}
        self.deck_dirty = False
        self.load_card()

    def new_card(self):
        self.save_card()
        self.cards.append(new_card())
        self.index = len(self.cards) - 1
        self.deck_dirty = True
        self.load_card()

    def duplicate_card(self):
        self.save_card()
        orig = json.loads(json.dumps(self.cards[self.index]))
        orig["id"] = str(uuid.uuid4())
        orig["created_at"] = now_iso()
        orig["updated_at"] = now_iso()
        self.cards.insert(self.index + 1, ensure_card_shape(orig))
        self.index += 1
        self.deck_dirty = True
        self.load_card()

    def load_card(self):
        if not self.cards:
            self.cards = [new_card()]
            self.index = 0

        self.index = max(0, min(self.index, len(self.cards) - 1))
        card = self.cards[self.index]

        self._loading_guard = True
        try:
            doc = CardDocument(card)
            doc.setHtml(card.get("content", ""))
            self.editor.setDocument(doc)
            self.card_label.setText(f"Card {self.index + 1} / {len(self.cards)}")
            self.refresh_overview()
        finally:
            self._loading_guard = False

    def save_card(self):
        if not self.cards:
            return
        card = self.cards[self.index]
        card["content"] = self.editor.document().toHtml()
        card["updated_at"] = now_iso()

    def prev_card(self):
        if self.index > 0:
            self.save_card()
            self.index -= 1
            self.load_card()

    def next_card(self):
        if self.index < len(self.cards) - 1:
            self.save_card()
            self.index += 1
            self.load_card()
        else:
            self.new_card()

    def select_card(self):
        if self._loading_guard:
            return
        row = self.overview.currentRow()
        if row >= 0 and row < len(self.cards):
            self.save_card()
            self.index = row
            self.load_card()

    def refresh_overview(self):
        # Guard against recursive signals
        self.overview.blockSignals(True)
        try:
            self.overview.clear()
            for i, c in enumerate(self.cards):
                tmp = QTextDocument()
                tmp.setHtml(c.get("content", ""))
                summary = tmp.toPlainText().strip().replace("\n", " ")
                summary = " ".join(summary.split())
                summary = summary[:70] + ("…" if len(summary) > 70 else "")
                if not summary:
                    summary = "(empty)"
                item = QListWidgetItem(f"{i + 1}: {summary}")
                item.setData(Qt.UserRole, i)
                self.overview.addItem(item)
            self.overview.setCurrentRow(self.index)
        finally:
            self.overview.blockSignals(False)

    # ---------------- Image insertion ----------------

    def insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if not path:
            return
        self.insert_image_from_file(path)

    def insert_image_from_file(self, path: str):
        if not self.cards:
            return

        try:
            with open(path, "rb") as f:
                raw = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Insert Image", f"Could not read file:\n{e}")
            return

        img = QImage()
        if not img.loadFromData(raw):
            QMessageBox.critical(self, "Insert Image", "Unsupported or corrupted image file.")
            return

        # Store image into current card as base64
        img_id = f"img_{uuid.uuid4().hex[:10]}"
        encoded = base64.b64encode(raw).decode("ascii")

        card = self.cards[self.index]
        card.setdefault("images", {})
        card["images"][img_id] = {
            "filename": safe_basename(path),
            "data": encoded,
        }

        # Insert with a reasonable starting size (cap width)
        max_w = 520
        w = img.width()
        h = img.height()
        if w > max_w:
            scale = max_w / float(w)
            w = int(w * scale)
            h = int(h * scale)

        c = self.editor.textCursor()
        c.insertHtml(f'<img src="image://{img_id}" width="{w}" height="{h}">')
        self.deck_dirty = True
        self.save_card()
        self.refresh_overview()

    # ---------------- Attachments ----------------

    def attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Attach File")
        if not path:
            return
        card = self.cards[self.index]
        card.setdefault("attachments", [])
        if path not in card["attachments"]:
            card["attachments"].append(path)
            self.deck_dirty = True

    def manage_attachments(self):
        card = self.cards[self.index]
        card.setdefault("attachments", [])
        dlg = AttachmentManagerDialog(self, card["attachments"])
        dlg.exec_()
        self.deck_dirty = True

    # ---------------- Persistence ----------------

    def save_deck(self) -> bool:
        if not self.deck_path:
            return self.save_deck_as()

        self.save_card()
        payload = dict(self.deck_meta or {})
        payload["schema_version"] = SCHEMA_VERSION
        payload["app"] = APP_NAME
        payload["app_version"] = APP_VERSION
        payload["cards"] = self.cards

        try:
            with open(self.deck_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            self.deck_dirty = False
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save deck:\n{e}")
            return False

    def save_deck_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Save Deck As", "", "JSON (*.json)")
        if not path:
            return False
        self.deck_path = path
        return self.save_deck()

    def open_deck(self):
        if not self._confirm_discard_or_save("opening a deck"):
            return

        path, _ = QFileDialog.getOpenFileName(self, "Open Deck", "", "JSON (*.json)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cards, meta = load_deck_any(data)
            if not cards:
                cards = [new_card()]

            self.cards = cards
            self.deck_meta = meta
            self.deck_path = path
            self.index = 0
            self.deck_dirty = False
            self.load_card()

        except Exception as e:
            QMessageBox.critical(self, "Open Error", f"Could not open deck:\n{e}")

    # ---------------- About ----------------

    def show_about(self):
        QMessageBox.about(
            self, "About",
            f"{APP_NAME} {APP_VERSION}\n"
            f"Author: Dr. Eric O. Flores\n"
            f"Schema: v{SCHEMA_VERSION}\n\n"
            "Key features:\n"
            "• Single editor surface (text + embedded images)\n"
            "• Drag & drop image files into the card\n"
            "• Click image: resize handle (bottom-right) — drag to resize\n"
            "• Right-click image: resize/reset/remove\n"
            "• Loads legacy JSON decks and schema decks\n"
            "• Undo/Redo + formatting toolbar\n"
            "• Attachment manager\n\n"
            "License: MIT"
        )


# ---------------- Entry ----------------

def main():
    app = QApplication(sys.argv)
    win = RolocardApp()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
