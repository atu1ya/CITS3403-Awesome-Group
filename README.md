# UniSync 🗓️
> **CITS3403 Group Project — Work in Progress**

A collaborative scheduling platform for university students. Combines course timetable generation with group availability planning so you don't need five different tools just to organise your week.

> ⚠️ **This project is under active development. Features, structure, and scope are subject to change.**

---

## The Idea

Students spend way too much time trying to coordinate schedules with friends — figuring out which tutorials to pick, finding shared days off, and scheduling group meetings across separate tools. UniSync aims to bring all of that into one place.

The core concept:
- Input your course options
- Generate a clash-free timetable based on your preferences
- Form a group with friends and optimise your schedules together
- Schedule meetings using a built-in availability grid (think When2Meet, but integrated)

---

## Planned Features

> These are planned/in-progress — not all are implemented yet.

- **User Auth** — register, login, profile management
- **Course Timetable Input** — add courses and their available time slots
- **Timetable Generation** — generates valid, clash-free combinations ranked by preferences (e.g. avoid early mornings, maximise days off)
- **Group Scheduling** — create a group with up to 4 students, run a collaborative timetable optimisation
- **Meeting Scheduler** — When2Meet-style availability grid, built directly into the platform
- **Best Time Calculator** — automatically surfaces the best meeting slots based on group availability

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | HTML, CSS, Bootstrap |
| Client-side | JavaScript, jQuery, AJAX |
| Backend | Python, Flask |
| Database | SQLite, SQLAlchemy |
| Optional | WebSockets |

---

## Project Structure

> Will be updated as the project develops.

```
unisync/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes/
│   └── templates/
├── static/
│   ├── css/
│   └── js/
├── tests/
├── config.py
└── run.py
```

---

## Getting Started

> Setup instructions are a work in progress.

```bash
# Clone the repo
git clone https://github.com/your-group/unisync.git
cd unisync

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
flask run
```

---

## Group Members

| Name | Student Number |
|---|---|
| TBD | TBD |
| TBD | TBD |
| TBD | TBD |
| TBD | TBD |

---

## Status

- [ ] Project setup
- [ ] User authentication
- [ ] Course input + storage
- [ ] Timetable generation algorithm
- [ ] Group creation and management
- [ ] Collaborative timetable optimisation
- [ ] Meeting scheduler (availability grid)
- [ ] Best meeting time calculator
- [ ] UI polish
- [ ] Testing

---

*CITS3403 — Agile Web Development, University of Western Australia*