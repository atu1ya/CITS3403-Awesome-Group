# SmartMeet — CITS3403 Group Project

## Description

SmartMeet is a collaborative scheduling web app that allows users to create meeting rooms, invite participants, collect availability via an interactive grid, and find the best meeting time. Built with Flask, SQLAlchemy and Bootstrap 5.

---

## Members

| UWA ID   | Name                          | GitHub Username |
|----------|-------------------------------|-----------------|
| 24306853 | Suhrid Mahmood Pushan         | suhrid07        |
| 24277844 | Muhammad Imran Bin Ismail     | cereal-addict   |
| 24225113 | Atulya Chaturvedi             | atu1ya          |
| 24182536 | Hyun Lee                      | hyunl33         |

---

## Project Contributions

The project was developed in two phases:

**Phase 1 — UI Mockups**
Suhrid and Hyun collaborated on the initial HTML/CSS mockups to establish the visual design and layout of the application before backend development began.

**Phase 2 — Full Implementation**
The full application was built across four feature branches:

| Member | Branch | Responsibility |
|---|---|---|
| Suhrid | `feature/suhrid-scaffold-auth-base` | Project scaffold, database models, base templates, CSS, authentication system |
| Imran | `feature/imran-rooms` | Room creation, availability grid, submit availability |
| Atulya | `feature/atulya-dashboard-results` | Dashboard, results heatmap, confirm time, notify participants |
| Hyun | `feature/hyun-social` | Friends, notifications, schedule, settings |

---

## Getting Started

Make sure Python 3.10+ is installed on your machine.

---

### 1. Clone the repository

```bash
git clone https://github.com/atu1ya/CITS3403-Awesome-Group.git
cd CITS3403-Awesome-Group
```

---

### 2. Create and activate a virtual environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Set up the database

```bash
flask db upgrade
```

---

### 5. Create test accounts

```bash
python seed.py
```

This creates 4 pre-verified test accounts for testing the full workflow — creating rooms, inviting participants, submitting availability and confirming meeting times.

| Username   | Password  | Display Name |
|------------|-----------|--------------|
| testuser1  | Test123!  | Alice        |
| testuser2  | Test123!  | Bob          |
| testuser3  | Test123!  | Charlie      |
| testuser4  | Test123!  | Diana        |

> Safe to run multiple times — skips accounts that already exist.

---

### 6. Run the application

```bash
python run.py
```

The app will be available at `http://127.0.0.1:5000/`

---

## Email Functionality

The signup and password reset flows require email credentials to send verification codes. The `.env` file containing these credentials is not included in the repository.

To test the full signup flow, contact a team member to obtain the `.env` file. Otherwise use the pre-seeded test accounts above which bypass email verification entirely.

---

## Running the Tests

### Unit tests

```bash
python -m pytest tests/unit
```

### Selenium tests

Make sure the app is running first, then:

```bash
python -m pytest tests/selenium
```

---

## Workflow

1. Create a new branch for your feature: `git checkout -b feature/your-feature`
2. Activate your virtual environment
3. Make changes and commit with meaningful messages following the convention: `feat(scope): description`
4. Push your branch and open a Pull Request on GitHub
5. Get at least one approval before merging into `main`

Separate your changes into meaningful commits rather than one large commit. Every merge into `main` should leave the app in a working state.

---

## Notes

- Never commit `.env`, `*.db`, or `.venv/` — these are in `.gitignore`
- Always commit the `migrations/` folder
- The local server URL is printed in the terminal after startup
- Runtime errors and tracebacks are shown in the terminal
