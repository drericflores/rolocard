By Dr. Eric O. Flores email: <eoftoro@gmail.com>

MIT License

Copyright (c) 2024 drericflores

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
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTextEdit, QListWidget, QWidget, QMenuBar, QAction,
    QFileDialog, QMessageBox, QInputDialog, QComboBox
)
from PyQt5.QtGui import QTextCharFormat, QFont, QTextOption
from PyQt5.QtCore import Qt
import json

class RolodexApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Rolodex Index Card Application")
        self.setGeometry(100, 100, 600, 600)

        self.cards = []
        self.current_card_index = 0
        self.tags = []

        self.initUI()

    def initUI(self):
        # Create Menu
        self.create_menu()

        # Create Main Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Layouts
        main_layout = QVBoxLayout(main_widget)

        # Card Number Label
        self.card_number_label = QLabel("Card 1", self)
        main_layout.addWidget(self.card_number_label)

        # Text Edit for Card Content
        self.card_text = QTextEdit(self)
        self.card_text.setWordWrapMode(QTextOption.WordWrap)  # Enable word wrapping
        main_layout.addWidget(self.card_text)

        # Tags and Attachments
        self.tag_label = QLabel("Tags: None", self)
        main_layout.addWidget(self.tag_label)

        self.attachment_label = QLabel("Attachments: None", self)
        main_layout.addWidget(self.attachment_label)

        # Card Overview
        self.card_listbox = QListWidget(self)
        self.card_listbox.itemSelectionChanged.connect(self.select_card_from_overview)
        main_layout.addWidget(self.card_listbox)

        # Tool Buttons
        self.create_tool_buttons(main_layout)

        # Initialize with the first card
        self.new_card()

    def create_menu(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("File")

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_stack_file)
        file_menu.addAction(open_action)

        close_action = QAction("Close", self)
        close_action.triggered.connect(self.close_card_deck)
        file_menu.addAction(close_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_stack_file)
        file_menu.addAction(save_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Help Menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def create_tool_buttons(self, layout):
        toolbar_layout = QHBoxLayout()

        btn_open = QPushButton("Open Card Deck", self)
        btn_open.clicked.connect(self.open_stack_file)
        toolbar_layout.addWidget(btn_open)

        btn_close = QPushButton("Close Card Deck", self)
        btn_close.clicked.connect(self.close_card_deck)
        toolbar_layout.addWidget(btn_close)

        btn_save = QPushButton("Save Card Deck", self)
        btn_save.clicked.connect(self.save_stack_file)
        toolbar_layout.addWidget(btn_save)

        btn_next = QPushButton("Next", self)
        btn_next.clicked.connect(self.next_card)
        toolbar_layout.addWidget(btn_next)

        btn_previous = QPushButton("Previous", self)
        btn_previous.clicked.connect(self.previous_card)
        toolbar_layout.addWidget(btn_previous)

        btn_delete = QPushButton("Delete Card", self)
        btn_delete.clicked.connect(self.delete_card)
        toolbar_layout.addWidget(btn_delete)

        btn_add_tag = QPushButton("Add Tag", self)
        btn_add_tag.clicked.connect(self.add_tag_to_card)
        toolbar_layout.addWidget(btn_add_tag)

        btn_attach_file = QPushButton("Attach File", self)
        btn_attach_file.clicked.connect(self.attach_file)
        toolbar_layout.addWidget(btn_attach_file)

        btn_attach_image = QPushButton("Attach Image", self)
        btn_attach_image.clicked.connect(self.attach_image)
        toolbar_layout.addWidget(btn_attach_image)

        btn_bold = QPushButton("Bold", self)
        btn_bold.clicked.connect(lambda: self.toggle_format(QFont.Bold))
        toolbar_layout.addWidget(btn_bold)

        btn_italic = QPushButton("Italic", self)
        btn_italic.clicked.connect(lambda: self.toggle_format(QFont.StyleItalic))
        toolbar_layout.addWidget(btn_italic)

        btn_underline = QPushButton("Underline", self)
        btn_underline.clicked.connect(lambda: self.toggle_format('underline'))
        toolbar_layout.addWidget(btn_underline)

        layout.addLayout(toolbar_layout)

    def new_card(self):
        # Only save current card if cards already exist
        if self.cards:
            self.save_current_card()
        # Add a new card to the list
        self.cards.append({"content": "", "tags": [], "attachments": []})
        self.current_card_index = len(self.cards) - 1
        self.update_card_display()

    def update_card_display(self):
        self.reindex_cards()
        self.card_number_label.setText(f"Card {self.current_card_index + 1}")
        self.card_text.setHtml(self.cards[self.current_card_index]["content"])  # Load the HTML content
        tags = ', '.join(self.cards[self.current_card_index].get("tags", []))
        self.tag_label.setText(f"Tags: {tags if tags else 'None'}")
        self.update_attachments_display(self.cards[self.current_card_index].get("attachments", []))
        self.update_card_overview()

    def update_card_overview(self):
        self.card_listbox.clear()
        for i, card in enumerate(self.cards):
            summary = f"Card {i + 1}: {card['content'][:30]}..."
            self.card_listbox.addItem(summary)

    def reindex_cards(self):
        for i, card in enumerate(self.cards):
            card["index"] = i + 1

    def save_current_card(self):
        # Ensure that there is a card to save
        if 0 <= self.current_card_index < len(self.cards):
            content = self.card_text.toHtml().strip()  # Save the content as HTML
            self.cards[self.current_card_index]["content"] = content

    def next_card(self):
        self.save_current_card()
        if self.current_card_index < len(self.cards) - 1:
            self.current_card_index += 1
        else:
            self.new_card()
        self.update_card_display()

    def previous_card(self):
        self.save_current_card()
        if self.current_card_index > 0:
            self.current_card_index -= 1
        self.update_card_display()

    def delete_card(self):
        if len(self.cards) > 0:
            del self.cards[self.current_card_index]
            self.current_card_index = min(self.current_card_index, len(self.cards) - 1)
            self.update_card_display()

    def select_card_from_overview(self):
        selected_index = self.card_listbox.currentRow()
        if selected_index != -1:
            self.save_current_card()
            self.current_card_index = selected_index
            self.update_card_display()

    def save_stack_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Card Deck", "", "JSON files (*.json)")
        if filename:
            with open(filename, 'w') as file:
                json.dump(self.cards, file, indent=4)

    def open_stack_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Card Deck", "", "JSON files (*.json)")
        if filename:
            with open(filename, 'r') as file:
                self.cards = json.load(file)
                self.current_card_index = 0
                self.update_card_display()

    def attach_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select File")
        if filename:
            self.cards[self.current_card_index]["attachments"].append(filename)
            self.update_attachments_display(self.cards[self.current_card_index]["attachments"])

    def attach_image(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Image Files (*.png;*.jpg;*.jpeg;*.gif)")
        if filename:
            self.cards[self.current_card_index]["attachments"].append(filename)
            self.update_attachments_display(self.cards[self.current_card_index]["attachments"])

    def update_attachments_display(self, attachments):
        attachment_names = [self.extract_filename(a) for a in attachments]
        self.attachment_label.setText(f"Attachments: {', '.join(attachment_names) if attachments else 'None'}")

    def extract_filename(self, path):
        return path.split("/")[-1]

    def toggle_format(self, format_type):
        cursor = self.card_text.textCursor()
        if cursor.hasSelection():
            format = cursor.charFormat()
            if format_type == QFont.Bold:
                format.setFontWeight(QFont.Bold if format.fontWeight() != QFont.Bold else QFont.Normal)
            elif format_type == QFont.StyleItalic:
                format.setFontItalic(not format.fontItalic())
            elif format_type == 'underline':
                format.setFontUnderline(not format.fontUnderline())
            cursor.mergeCharFormat(format)
        else:
            QMessageBox.information(self, "No Selection", "Please select text to format.")

    def close_card_deck(self):
        self.cards = []
        self.current_card_index = 0
        self.new_card()

    def show_about_dialog(self):
        about_text = (
            "Rolodex Index Card Application\n"
            "Author: Dr. Eric O. Flores\n"
            "Date: August 24, 2024\n"
            "Version: 1.8\n\n"
            "Programming Language: Python 3 \n"
            "original  C++ Converted to Python3 \n"
            "GUI Framework: PyQt5 (for Python version), Qt (for C++ version)\n\n"
            "License: MIT License"
        )

        technologies_text = (
            "Applicable Technologies:\n"
            "- JSON for data storage\n"
            "- Tkinter (early Python GUI)\n"
            "- Object-Oriented Programming (OOP)\n"
            "- Cross-Platform Compatibility"
        )

        QMessageBox.about(self, "About", about_text)
        QMessageBox.about(self, "Technologies Used", technologies_text)

    def add_tag_to_card(self):
        tag, ok = QInputDialog.getText(self, "Add Tag", "Enter a tag for this card:")
        if ok and tag:
            tag = tag.strip()
            if tag not in self.cards[self.current_card_index]["tags"]:
                self.cards[self.current_card_index]["tags"].append(tag)
                self.update_card_display()

    def filter_by_tag(self, selected_tag):
        if selected_tag == "All":
            self.current_card_index = 0
            self.update_card_display()
        else:
            for index, card in enumerate(self.cards):
                if selected_tag in card["tags"]:
                    self.current_card_index = index
                    self.update_card_display()
                    break

    def search_cards(self):
        search_term = self.search_entry.text().lower()
        self.card_listbox.clear()
        for index, card in enumerate(self.cards):
            if search_term in card["content"].lower():
                excerpt = card["content"][:50].replace("\n", " ") + "..."
                self.card_listbox.addItem(f"Card {index + 1}: {excerpt}")

    def highlight_search_term(self):
        search_term = self.search_entry.text().lower()
        content = self.card_text.toPlainText().lower()
        cursor = self.card_text.textCursor()

        cursor.beginEditBlock()
        cursor.setPosition(0)
        while True:
            cursor = self.card_text.find(search_term, cursor)
            if cursor.isNull():
                break
            cursor.movePosition(cursor.WordRight, cursor.KeepAnchor)
            format = cursor.charFormat()
            format.setBackground(Qt.yellow)
            cursor.mergeCharFormat(format)
        cursor.endEditBlock()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = RolodexApp()
    main_window.show()
    sys.exit(app.exec_())

