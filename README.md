# Eisenhower Matrix Planner

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-Modern_UI-512BD4?logo=python)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![MIT License](https://img.shields.io/github/license/farok/EisenhowerMatrixPlannerPy)
![Stars](https://img.shields.io/github/stars/farok/EisenhowerMatrixPlannerPy?style=social)

> **A stunning, modern, and truly continuous 10×10 Eisenhower Matrix** — built with **Python + CustomTkinter**

Unlike traditional 4-quadrant apps, this planner uses a **smooth, fully continuous 10×10 priority grid** where every task is precisely positioned based on its **Importance** and **Urgency** scores — no more forced quadrants!

Tasks appear as **minimal colored dots** — hover to reveal full details. Pure elegance.

### Features

- **True 10×10 continuous matrix** — drag anywhere with pixel-perfect precision
- **Hover-to-reveal** — clean dots, beautiful popup cards on hover
- Smooth drag & drop with instant snap-to-grid
- Auto-increase urgency for near-deadline tasks (every 30 minutes)
- Edit / Delete tasks with one click
- Full dark/light mode support (system sync)
- Export entire matrix as PNG
- 100% offline — SQLite persistence
- Professional logging (structlog + rich)
- Zero external UI frameworks — pure Python + CustomTkinter

### Tech Stack

| Technology             | Purpose                          |
|------------------------|----------------------------------|
| Python 3.11+           | Core language                    |
| CustomTkinter          | Modern, beautiful UI             |
| SQLAlchemy + SQLite    | Local persistence                |
| APScheduler            | Background urgency updates       |
| structlog + rich       | Professional colored logging     |
| Tkinter Canvas         | Smooth drag & drop + hover zones |




> Minimal dots → hover → full task card. Pure Figma/Notion vibes.

### Installation & Run

```bash
# 1. Clone the repo
git clone https://github.com/farok/EisenhowerMatrixPlannerPy.git
cd EisenhowerMatrixPlannerPy

# 2. Create virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\activate    # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python main.py
```

### Build Executable (Optional)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico main.py
```

### Project Structure

```
EisenhowerMatrixPlannerPy/
├── main.py                 # Entry point
├── ui/                     # All UI components
│   ├── main_window.py
│   ├── matrix_canvas.py    # 10×10 matrix with hover zones
│   ├── task_card.py        # Dot + hover popup logic
│   └── task_dialog.py
├── database/               # SQLAlchemy models & engine
├── services/               # Task logic + auto-urgency
├── utils/logger.py         # Professional structured logging
├── data/eisenhower.db      # Created automatically
└── logs/                   # Daily log files
```

### Logging

All actions are logged beautifully in console + daily files:
- Task created/moved/deleted
- Resize events
- Theme changes
- Export actions
- Errors & crashes

### Why This App?

Because most Eisenhower apps are stuck in 1980s thinking: **4 rigid boxes**.

This one understands that priority is a **spectrum**, not a category.

You deserve a planner that feels like **Notion, Figma, and Obsidian had a baby** — and that baby speaks Python.

---

Made with passion by **farok** — for people who take priorities seriously, but hate ugly apps.

---

**Star this repo if you believe productivity tools should be beautiful!**
```
