# ICD-10-CM Diagnosis Search

A desktop application for searching and looking up ICD-10-CM diagnosis codes quickly and accurately. Built with Python, Tkinter, FastAPI, and SQLite.

## Features

- **Fast Diagnosis Search**: Instant fuzzy and keyword matching on ICD-10-CM diagnosis codes and descriptions.
- **Medical Abbreviation Support**: Automatically expands common medical abbreviations (e.g., HTN, CKD, T2DM, COPD, CHF, CAD, UTI, AKI, ESRD, GERD).
- **Desktop UI**: Clean Tkinter desktop user interface with results display, details drawer, and keyboard navigation.
- **Embedded API**: Integrated local FastAPI service querying an optimized SQLite database (`icd.db`).
- **Standalone Packaging**: Preconfigured PyInstaller specifications (`ICD_Search.spec`, `ICD_Search_Debug.spec`) for building single-executable Windows applications.

## Project Structure

```
icd_search/
├── backend/
│   ├── main.py          # FastAPI server & Tkinter UI
│   └── database.py      # SQLite connection & search logic
├── icd.db               # SQLite database with ICD-10-CM codes
├── requirements.txt     # Python dependencies
├── ICD_Search.spec      # PyInstaller build specification
└── .gitignore
```

## Installation & Running

1. **Clone the repository**:
   ```bash
   git clone https://github.com/61974253/icd_search.git
   cd icd_search
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   python -m backend.main
   ```

## Building Executable

To build a standalone Windows executable using PyInstaller:
```bash
pip install pyinstaller
pyinstaller ICD_Search.spec
```
The generated `.exe` will be located in the `dist/` directory.
