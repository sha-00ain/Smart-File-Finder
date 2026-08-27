# 🔎 Smart File Finder

Smart File Finder is a fast and lightweight Windows desktop application for searching files and detecting duplicate files.

Built with Python and PySide6.

---

## ✨ Features

### 🔎 File Search

- Search files by name
- Search inside a selected folder
- Search across all available drives
- Filter files by category
- Custom file extension filtering
- Live search results
- Open files directly
- Open file location
- Copy file path

---

## ♻️ Duplicate Detection

Smart File Finder provides three duplicate detection modes.

### ⚡ Name Search — Fastest

Detects files with the same filename.

The application keeps the first/original file and identifies the additional files as duplicates.

Example:

    report.pdf
    report - Copy.pdf
    report (1).pdf
    report (2).pdf

The original file remains unselected, while the additional duplicate files can be selected for deletion.

---

### 🚀 Quick Search

Quick Search compares files using:

- File size
- First part of the file
- Last part of the file

This allows the application to quickly identify likely duplicate files.

Files with different names can also be detected when their content matches.

---

### 🔐 Hash Search — Exact

Hash Search uses a complete BLAKE2b hash of the file.

Files with identical content are grouped together even when their filenames are different.

Example:

    photo.jpg
    vacation.jpg
    image_backup.jpg

If their complete contents are identical, they are detected as duplicates.

---

## 🗑️ Smart Duplicate Selection

The Select All Duplicate Files button automatically selects only duplicate files.

The original/first file in each duplicate group remains unselected.

Available controls:

- Select All Duplicate Files
- Clear Selection
- Delete Selected

Deleted files are moved to the Windows Recycle Bin instead of being permanently deleted.

---

## 🛡️ Safe Deletion

Smart File Finder uses the Windows Recycle Bin when deleting files.

Files are not permanently deleted directly by the application.

Before deleting duplicate files, always review the selected files carefully.

---

## 🖥️ Screenshots

Screenshots can be added here.

---

## ⚙️ Technologies

- Python
- PySide6
- BLAKE2b
- ThreadPoolExecutor
- send2trash
- PyInstaller

---

## 📦 Download

The Windows executable is available in the GitHub Releases section.

Download:

    Smart File Finder.exe

No Python installation is required when using the packaged Windows executable.

---

## 🚀 Run from Source

### 1. Clone the repository

    git clone https://github.com/sha-00ain/Smart-File-Finder.git
    cd Smart-File-Finder

### 2. Create a virtual environment

    python -m venv .venv

### 3. Activate the virtual environment

Windows PowerShell:

    .venv\Scripts\Activate.ps1

### 4. Install dependencies

    pip install -r requirements.txt

### 5. Run the application

    python app.py

---

## 🔨 Build Windows EXE

To create a single-file Windows executable:

    pyinstaller --noconfirm --clean --onefile --windowed --name "Smart File Finder" --icon "icon.ico" app.py

The executable will be created at:

    dist/
    └── Smart File Finder.exe

---

## 📁 Project Structure

    Smart-File-Finder/
    │
    ├── app.py
    ├── duplicate_finder.py
    ├── file_searcher.py
    ├── icon_generator.py
    ├── icon.ico
    ├── requirements.txt
    ├── README.md
    └── .gitignore

---

## 💻 System Requirements

- Windows 10 or later
- Python 3.x for running from source
- No Python installation required for the packaged EXE

---

## 👨‍💻 Developer

Developed by: Md. Shakil Hossain

Email: shakil.hossain2417@gmail.com

---

## 📄 License

This project is provided for educational and personal use.