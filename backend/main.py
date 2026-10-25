
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import re
import requests
import uvicorn

from fastapi import FastAPI, Query, HTTPException
from backend.database import search_diagnoses, DB_PATH


# ==================================================
# CONFIGURATION
# ==================================================

API_HOST = "127.0.0.1"
API_PORT = 8001
API_URL = f"http://{API_HOST}:{API_PORT}"
MAX_RESULTS = 100   

NAVY = "#16324F"
TEAL = "#0D9488"
BG = "#F3F6FA"
WHITE = "#FFFFFF"
TEXT = "#243449"
MUTED = "#718096"
BORDER = "#DCE4ED"
ROW_ALT = "#F0F6FC"


# ==================================================
# FASTAPI BACKEND
# ==================================================

app = FastAPI(title="ICD-10-CM Diagnosis Search")


@app.get("/search")
def search_api(q: str = Query(..., min_length=1, max_length=100)):
    query = q.strip()

    if not query:
        return {"results": []}

    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database not found: {DB_PATH}"
        )

    try:
        return {
            "results": search_diagnoses(query, limit=MAX_RESULTS)
        }
    except Exception as error:
        print("DATABASE SEARCH ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Local database search failed"
        )



def start_backend():
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_config=None,
        access_log=False
    )



# ==================================================
# CLEAN DUPLICATE DESCRIPTION
# ==================================================

def clean_description(code, document):
    text = str(document or "").strip()
    code = str(code or "").strip()

    if not text:
        return ""

    # Remove "ICD-10-CM code" prefix
    text = re.sub(
        r"^ICD-10-CM\s+code\s*[:\-]?\s*",
        "",
        text,
        flags=re.IGNORECASE
    ).strip()

    # Remove ICD code from the beginning of the description
    if code:
        text = re.sub(
            rf"^{re.escape(code)}(?:\s*[-:.,]\s*|\s+)?",
            "",
            text,
            count=1,
            flags=re.IGNORECASE
        ).strip()

    # Normalize extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    # Remove duplicated full text, e.g. "Diabetes Diabetes"
    words = text.split()

    if len(words) >= 2 and len(words) % 2 == 0:
        midpoint = len(words) // 2
        first = " ".join(words[:midpoint])
        second = " ".join(words[midpoint:])

        normalize = lambda value: re.sub(
            r"[\W_]+", "", value
        ).casefold()

        if normalize(first) and normalize(first) == normalize(second):
            text = first

    # Remove repeated sentences while preserving the first occurrence
    sentences = re.split(r"(?<=[.!?])\s+", text)
    unique_sentences = []
    seen = set()

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        key = re.sub(r"\s+", " ", sentence).casefold()
        key = re.sub(r"[^\w\s]", "", key)

        if key not in seen:
            seen.add(key)
            unique_sentences.append(sentence)

        if "." in text:
             text = text.rsplit(".", 1)[1].strip()

    return " ".join(unique_sentences).strip()


# ==================================================
# TKINTER APPLICATION
# ==================================================

class ICDSearchApp:

    def __init__(self, root):
        self.root = root
        self.search_after_id = None

        self.root.title("MedCode | ICD-10-CM Search")
        self.root.geometry("1120x720")
        self.root.minsize(800, 520)
        self.root.configure(bg=BG)

        self.setup_styles()
        self.build_header()
        self.build_search_area()
        self.build_results()
        self.build_status()

        self.root.bind("<Control-f>", self.focus_search)
        self.root.bind("<Escape>", self.clear_search)

    # ==================================================
    # STYLES
    # ==================================================

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Medical.Treeview",
            background=WHITE,
            foreground=TEXT,
            fieldbackground=WHITE,
            font=("Segoe UI", 11),
            rowheight=42,
            borderwidth=0
        )

        style.configure(
            "Medical.Treeview.Heading",
            background="#E9F0F7",
            foreground=NAVY,
            font=("Segoe UI", 10, "bold"),
            padding=(12, 14),
            relief="flat"
        )

        style.map(
            "Medical.Treeview",
            background=[("selected", "#D4F1EE")],
            foreground=[("selected", NAVY)]
        )

        style.configure(
            "Medical.Vertical.TScrollbar",
            background="#D9E3ED",
            troughcolor=BG,
            borderwidth=0,
            arrowsize=14
        )

    # ==================================================
    # HEADER
    # ==================================================

    def build_header(self):
        header = tk.Frame(self.root, bg=NAVY, height=112)
        header.pack(fill="x")
        header.pack_propagate(False)

        content = tk.Frame(header, bg=NAVY)
        content.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=16
        )

        brand = tk.Frame(content, bg=NAVY)
        brand.pack(side="left", fill="y")

        logo = tk.Label(
            brand,
            text="IHC",
            font=("Segoe UI", 22, "bold"),
            bg=TEAL,
            fg=WHITE,
            width=3,
            height=1
        )
        logo.pack(side="left", padx=(0, 14), pady=5)

        title_frame = tk.Frame(brand, bg=NAVY)
        title_frame.pack(side="left", fill="y")

        tk.Label(
            title_frame,
            text="INCESSANT PRODUCTIVITY",
            font=("Segoe UI", 21, "bold"),
            bg=NAVY,
            fg=WHITE
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="ICD-10-CM DIAGNOSIS LOOKUP",
            font=("Segoe UI", 9, "bold"),
            bg=NAVY,
            fg="#B9CDDF"
        ).pack(anchor="w", pady=(2, 0))

    # ==================================================
    # SEARCH AREA
    # ==================================================

    def build_search_area(self):
        area = tk.Frame(self.root, bg=BG)
        area.pack(fill="x", padx=30, pady=(20, 8))

        tk.Label(
            area,
            text="Find a diagnosis",
            font=("Segoe UI", 17, "bold"),
            bg=BG,
            fg=NAVY
        ).pack(anchor="w")

        # Description moved slightly upward
        tk.Label(
            area,
            text="Search by ICD-10-CM code or diagnosis description.",
            font=("Segoe UI", 10),
            bg=BG,
            fg=MUTED
        ).pack(anchor="w", pady=(1, 8))

        # Compact outer search box
        search_card = tk.Frame(
            area,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        search_card.pack(anchor="w")

        search_inner = tk.Frame(search_card, bg=WHITE)
        search_inner.pack(
            fill="none",
            padx=10,
            pady=8
        )

        tk.Label(
            search_inner,
            text="⌕",
            font=("Segoe UI", 23),
            bg=WHITE,
            fg=TEAL
        ).pack(side="left", padx=(2, 8))

        self.search_var = tk.StringVar()

        # Only one Entry widget; width reduced
        self.search_entry = tk.Entry(
            search_inner,
            textvariable=self.search_var,
            font=("Segoe UI", 13),
            width=22,
            bg=WHITE,
            fg=TEXT,
            insertbackground=TEAL,
            relief="flat",
            highlightthickness=0,
            bd=0
        )
        self.search_entry.pack(
            side="left",
            fill="none",
            expand=False,
            ipady=8
        )

        self.search_entry.bind(
            "<KeyRelease>",
            self.on_typing
        )

        self.clear_button = tk.Button(
            search_inner,
            text="Clear",
            font=("Segoe UI", 10, "bold"),
            bg=WHITE,
            fg=MUTED,
            activebackground=WHITE,
            activeforeground=NAVY,
            relief="flat",
            cursor="hand2",
            padx=10,
            command=self.clear_search
        )
        self.clear_button.pack(side="left", padx=(6, 0))

        self.search_entry.focus_set()

        tk.Label(
            area,
            text="TIP   Click any result to copy its ICD code.",
            font=("Segoe UI", 9),
            bg=BG,
            fg=MUTED
        ).pack(anchor="w", pady=(6, 0))

    # ==================================================
    # RESULTS TABLE
    # ==================================================

    def build_results(self):
        container = tk.Frame(self.root, bg=BG)
        container.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(8, 15)
        )

        table_header = tk.Frame(container, bg=BG)
        table_header.pack(fill="x", pady=(0, 10))

        tk.Label(
            table_header,
            text="Search results",
            font=("Segoe UI", 13, "bold"),
            bg=BG,
            fg=NAVY
        ).pack(side="left")

        self.count_label = tk.Label(
            table_header,
            text="Ready to search",
            font=("Segoe UI", 9, "bold"),
            bg=BG,
            fg=TEAL
        )
        self.count_label.pack(side="right")

        table_card = tk.Frame(
            container,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        table_card.pack(fill="both", expand=True)

        columns = ("code", "description")

        self.results = ttk.Treeview(
            table_card,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Medical.Treeview"
        )

        self.results.heading("code", text="ICD-10-CM CODE")
        self.results.heading(
            "description",
            text="DIAGNOSIS DESCRIPTION"
        )

        self.results.column(
            "code",
            width=155,
            minwidth=115,
            stretch=False,
            anchor="center"
        )

        self.results.column(
            "description",
            width=800,
            minwidth=300,
            anchor="w",
            stretch=True
        )

        self.results.tag_configure("even", background=WHITE)
        self.results.tag_configure("odd", background=ROW_ALT)

        scrollbar = ttk.Scrollbar(
            table_card,
            orient="vertical",
            command=self.results.yview,
            style="Medical.Vertical.TScrollbar"
        )

        self.results.configure(yscrollcommand=scrollbar.set)

        self.results.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(1, 0),
            pady=1
        )

        scrollbar.pack(side="right", fill="y")

        self.results.bind(
            "<ButtonRelease-1>",
            self.copy_icd_code
        )

    # ==================================================
    # STATUS BAR
    # ==================================================

    def build_status(self):
        footer = tk.Frame(self.root, bg=WHITE, height=38)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self.status = tk.Label(
            footer,
            text="Ready",
            font=("Segoe UI", 9),
            bg=WHITE,
            fg=MUTED,
            anchor="w"
        )
        self.status.pack(
            side="left",
            fill="both",
            expand=True,
            padx=30
        )

        tk.Label(
            footer,
            text="ICD-10-CM SEARCH",
            font=("Segoe UI", 8, "bold"),
            bg=WHITE,
            fg=TEAL
        ).pack(side="right", padx=30)

    # ==================================================
    # FOCUS / CLEAR SEARCH
    # ==================================================

    def focus_search(self, event=None):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, tk.END)
        return "break"

    def clear_search(self, event=None):
        self.search_var.set("")
        self.clear_results()
        self.status.config(text="Search cleared")
        self.count_label.config(text="Ready to search")
        self.search_entry.focus_set()
        return "break"

    # ==================================================
    # SEARCH AS USER TYPES
    # ==================================================

    def on_typing(self, event=None):
        query = self.search_var.get().strip()

        if self.search_after_id is not None:
            try:
                self.root.after_cancel(self.search_after_id)
            except tk.TclError:
                pass

            self.search_after_id = None

        if not query:
            self.clear_results()
            self.status.config(text="Ready")
            self.count_label.config(text="Ready to search")
            return

        self.status.config(text=f"Searching for: {query}")

        self.search_after_id = self.root.after(
            50,
            lambda q=query: self.search_local_api(q)
        )

    # ==================================================
    # API SEARCH
    # ==================================================

    def search_local_api(self, query):
        self.search_after_id = None

        try:
            response = requests.get(
                f"{API_URL}/search",
                params={"q": query},
                timeout=10
            )

            response.raise_for_status()
            rows = response.json().get("results", [])

            if query != self.search_var.get().strip():
                return

            self.clear_results()

            for index, row in enumerate(rows):
                code = str(row.get("id", "")).strip()
                document = str(row.get("document", "")).strip()

                description = clean_description(code, document)
                tag = "even" if index % 2 == 0 else "odd"

                self.results.insert(
                    "",
                    "end",
                    values=(code, description),
                    tags=(tag,)
                )

            self.count_label.config(
                text=f"{len(rows):,} result(s)"
            )
            self.status.config(
                text="Search completed successfully"
            )

        except requests.RequestException as error:
            self.status.config(
                text="Cannot connect to the local search backend"
            )
            self.count_label.config(text="Connection error")
            print("API CONNECTION ERROR:", repr(error))

        except Exception as error:
            self.status.config(text="Search error")
            self.count_label.config(text="Error")
            print("SEARCH ERROR:", repr(error))

    # ==================================================
    # COPY ICD CODE ON CLICK
    # ==================================================

    def copy_icd_code(self, event=None):
        if event is not None:
            row_id = self.results.identify_row(event.y)

            if not row_id:
                return

            self.results.selection_set(row_id)
        else:
            selected = self.results.selection()
            row_id = selected[0] if selected else ""

        if not row_id:
            return

        values = self.results.item(row_id, "values")

        if not values:
            return

        code = str(values[0]).strip()

        if not code:
            self.status.config(text="ICD code not available")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(code)
            self.root.update()

            self.status.config(
                text=f"Copied ICD-10-CM code: {code}"
            )
            print("COPIED ICD CODE:", code)

        except tk.TclError as error:
            self.status.config(text="Could not copy code")
            print("CLIPBOARD ERROR:", repr(error))

    # ==================================================
    # CLEAR RESULTS
    # ==================================================

    def clear_results(self):
        for item in self.results.get_children():
            self.results.delete(item)


# ==================================================
# START APPLICATION
# ==================================================


if __name__ == "__main__":
    if not DB_PATH.exists():
        startup_root = tk.Tk()
        startup_root.withdraw()
        messagebox.showerror(
            "Database Missing",
            f"Local database not found:\n{DB_PATH}"
        )
        startup_root.destroy()
        raise SystemExit(1)

    root = tk.Tk()
    application = ICDSearchApp(root)

    def start_backend_safely():
        try:
            start_backend()
        except Exception as error:
            root.after(
                0,
                lambda err=error: messagebox.showerror(
                    "Backend Error",
                    f"Backend could not start:\n{err}"
                )
            )

    backend_thread = threading.Thread(
        target=start_backend_safely,
        daemon=True
    )
    backend_thread.start()

    def check_backend_ready(attempts=20):
        try:
            response = requests.get(
                f"{API_URL}/docs",
                timeout=1
            )
            if response.ok:
                return
        except requests.RequestException:
            pass

        if attempts > 0:
            root.after(
                500,
                lambda: check_backend_ready(attempts - 1)
            )
        else:
            messagebox.showerror(
                "Backend Connection Error",
                "The local backend did not start. "
                "Please restart the application."
            )

    root.after(500, check_backend_ready)
    root.mainloop()
