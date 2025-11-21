# Infera

**Infera** is a **Django-based web application** for analyzing codebases.  
It can upload zip files of projects, generate file/folder structure summaries, and produce class-based **ERD diagrams** (Entity Relationship Diagrams) for Python projects.

---

## Features

- Upload codebases in `.zip` format.
- Generate detailed **file and folder structure**.
- Extract Python classes, methods, and inheritance.
- Generate **Mermaid.js class diagrams (ERD)** for visual code structure.
- Simple and clean **web interface** built with Django templates.

---

## Tech Stack

- **Backend:** Django (Python 3.10+)
- **Frontend:** HTML, CSS, JavaScript, Mermaid.js
- **Database:** SQLite (default)
- **Other tools:** Temporary file extraction, zip handling, regex-based parsing

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/sedegah/Infera.git
cd Infera
