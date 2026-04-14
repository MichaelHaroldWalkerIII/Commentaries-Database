#!/usr/bin/env python3
"""
Simple Tkinter GUI for browsing Douay Rheims with Catena Aurea exegesis popup.

Left pane: Douay Rheims text (book/chapter/verse selection)
Right pane: Catena Aurea exegesis for the selected verse

Usage:
    python catena_gui.py /path/to/Commentaries-Database
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from extract_catena_aurea import CatenaParser


class CatenaGUI:
    def __init__(self, root: tk.Tk, db_root: Path):
        self.root = root
        self.root.title("Douay Rheims + Catena Aurea")
        self.root.geometry("1200x800")

        self.db_root = Path(db_root)
        self.parser = CatenaParser(self.db_root)

        # Load Douay Rheims
        with open(self.db_root / "Douay_Rheims.json", encoding="utf-8") as f:
            self.drb = json.load(f)

        self.books = sorted(self.drb.keys())
        self.current_book = None
        self.current_chapter = None
        self.current_verse = None

        self._build_ui()

    def _build_ui(self):
        # Main horizontal split
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left pane: Douay Rheims
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)

        # Controls for book/chapter
        controls = ttk.Frame(left_frame)
        controls.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(controls, text="Book:").pack(side=tk.LEFT)
        self.book_var = tk.StringVar()
        self.book_combo = ttk.Combobox(controls, textvariable=self.book_var, values=self.books, width=20)
        self.book_combo.pack(side=tk.LEFT, padx=5)
        self.book_combo.bind("<<ComboboxSelected>>", self._on_book_change)

        ttk.Label(controls, text="Chapter:").pack(side=tk.LEFT, padx=(10, 0))
        self.chapter_var = tk.StringVar()
        self.chapter_spin = ttk.Spinbox(controls, from_=1, to=150, textvariable=self.chapter_var, width=5)
        self.chapter_spin.pack(side=tk.LEFT, padx=5)
        self.chapter_spin.bind("<Return>", self._on_chapter_change)
        self.chapter_spin.bind("<FocusOut>", self._on_chapter_change)

        ttk.Button(controls, text="Load", command=self._load_chapter).pack(side=tk.LEFT, padx=5)

        # Douay Rheims text display
        drb_label = ttk.Label(left_frame, text="Douay Rheims", font=("TkDefaultFont", 12, "bold"))
        drb_label.pack(anchor=tk.W, padx=5)

        self.drb_text = tk.Text(left_frame, wrap=tk.WORD, font=("Georgia", 11), padx=10, pady=10)
        self.drb_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.drb_text.bind("<Button-1>", self._on_verse_click)

        # Scrollbar for DRB
        drb_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.drb_text.yview)
        self.drb_text.configure(yscrollcommand=drb_scroll.set)
        drb_scroll.pack(side=tk.RIGHT, fill=tk.Y, before=self.drb_text)

        # Right pane: Catena Aurea
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)

        catena_label = ttk.Label(right_frame, text="Catena Aurea Exegesis", font=("TkDefaultFont", 12, "bold"))
        catena_label.pack(anchor=tk.W, padx=5)

        self.catena_text = tk.Text(right_frame, wrap=tk.WORD, font=("Georgia", 10), padx=10, pady=10, state=tk.DISABLED)
        self.catena_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        catena_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.catena_text.yview)
        self.catena_text.configure(yscrollcommand=catena_scroll.set)
        catena_scroll.pack(side=tk.RIGHT, fill=tk.Y, before=self.catena_text)

        # Status bar
        self.status = ttk.Label(self.root, text="Select a book and chapter, then click a verse number.")
        self.status.pack(fill=tk.X, padx=5, pady=2)

        # Default selection
        if self.books:
            self.book_combo.set(self.books[0])
            self.chapter_var.set("1")
            self._load_chapter()

    def _on_book_change(self, event=None):
        self._load_chapter()

    def _on_chapter_change(self, event=None):
        self._load_chapter()

    def _load_chapter(self):
        book = self.book_var.get()
        try:
            chapter = int(self.chapter_var.get())
        except ValueError:
            chapter = 1
            self.chapter_var.set("1")

        if book not in self.drb:
            messagebox.showerror("Error", f"Book '{book}' not found in Douay Rheims.")
            return

        if str(chapter) not in self.drb[book]:
            messagebox.showerror("Error", f"Chapter {chapter} not found in {book}.")
            return

        self.current_book = book
        self.current_chapter = chapter
        self.current_verse = None

        # Clear and populate text
        self.drb_text.config(state=tk.NORMAL)
        self.drb_text.delete("1.0", tk.END)

        verses = self.drb[book][str(chapter)]
        for vnum in sorted(int(k) for k in verses.keys()):
            vtext = verses[str(vnum)]
            # Insert verse number as a tagged clickable element
            start = self.drb_text.index(tk.INSERT)
            self.drb_text.insert(tk.END, f"[{vnum}] ", f"verse_{vnum}")
            self.drb_text.insert(tk.END, vtext + "\n\n")
            # Store verse number in tag
            self.drb_text.tag_bind(f"verse_{vnum}", "<Button-1>", lambda e, v=vnum: self._select_verse(v))

        self.drb_text.config(state=tk.DISABLED)
        self.status.config(text=f"{book} {chapter} — Click a verse number to view Catena Aurea.")

    def _on_verse_click(self, event):
        # Find which verse was clicked based on cursor position
        index = self.drb_text.index(f"@{event.x},{event.y}")
        # Look for nearby verse tags
        for tag in self.drb_text.tag_names(index):
            if tag.startswith("verse_"):
                vnum = int(tag.split("_")[1])
                self._select_verse(vnum)
                return

    def _select_verse(self, verse: int):
        if not self.current_book or not self.current_chapter:
            return

        self.current_verse = verse
        self.status.config(text=f"Loading Catena Aurea for {self.current_book} {self.current_chapter}:{verse}...")

        # Highlight the selected verse in DRB pane
        self.drb_text.tag_remove("highlight", "1.0", tk.END)
        for tag in self.drb_text.tag_names():
            if tag.startswith("verse_"):
                v = int(tag.split("_")[1])
                if v == verse:
                    # Find the range of this verse
                    ranges = self.drb_text.tag_ranges(tag)
                    if ranges:
                        self.drb_text.tag_add("highlight", ranges[0], ranges[-1])
                        self.drb_text.tag_config("highlight", background="#ffff99")

        # Query CatenaParser
        try:
            results = self.parser.get_catena_for_verse(self.current_book, self.current_chapter, verse)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to query Catena Aurea: {e}")
            return

        # Display results in right pane
        self.catena_text.config(state=tk.NORMAL)
        self.catena_text.delete("1.0", tk.END)

        if not results:
            self.catena_text.insert(tk.END, "No Catena Aurea exegesis found for this verse.\n")
        else:
            self.catena_text.insert(tk.END, f"Found {len(results)} entries:\n\n")
            for i, r in enumerate(results, 1):
                name = r["father_name"]
                append = r.get("append_to_author_name", "")
                if append:
                    name += f" {append}"
                quote = r["quote"]
                source = r.get("source_title", "")
                url = r.get("source_url", "")

                self.catena_text.insert(tk.END, f"{i}. {name}\n", "father")
                self.catena_text.insert(tk.END, f"{quote}\n", "quote")
                if source:
                    self.catena_text.insert(tk.END, f"Source: {source}\n", "source")
                if url:
                    self.catena_text.insert(tk.END, f"URL: {url}\n", "url")
                self.catena_text.insert(tk.END, "\n" + "—" * 40 + "\n\n")

        # Configure tags for styling
        self.catena_text.tag_config("father", font=("TkDefaultFont", 10, "bold"), foreground="#1a5276")
        self.catena_text.tag_config("quote", font=("Georgia", 10))
        self.catena_text.tag_config("source", font=("TkDefaultFont", 9, "italic"), foreground="#555555")
        self.catena_text.tag_config("url", font=("TkDefaultFont", 9), foreground="#2874a6")

        self.catena_text.config(state=tk.DISABLED)
        self.status.config(text=f"{self.current_book} {self.current_chapter}:{verse} — {len(results)} Catena Aurea entries")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python catena_gui.py <path/to/Commentaries-Database>")
        sys.exit(1)

    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"Database root not found: {db_path}")
        sys.exit(1)

    root = tk.Tk()
    app = CatenaGUI(root, db_path)
    app.run()
