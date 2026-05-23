# Role-Based QR Smart Attendance Management System

A production-grade full-stack web application for educational institutions with QR-based attendance tracking.

## Features

- **Role-Based Access Control** — Admin, Teacher, Student roles with separate dashboards
- **QR Attendance** — Teachers generate expiring QR codes; students scan to mark attendance
- **Analytics** — Chart.js powered dashboards for attendance trends
- **Reports** — Filterable attendance records with CSV export
- **Secure Auth** — Flask-Login + Werkzeug password hashing
- **Responsive UI** — Mobile-friendly sidebar layout

## Tech Stack

| Layer      | Technology                    |
|------------|-------------------------------|
| Frontend   | HTML5, CSS3, Vanilla JS       |
| Backend    | Python Flask                  |
| Database   | SQLite (upgradeable to PG/MySQL) |
| Auth       | Flask-Login, Werkzeug         |
| QR         | qrcode library + html5-qrcode |
| Charts     | Chart.js                      |

## Setup & Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
python app.py

# 3. Open browser
http://localhost:5000
```

## Default Credentials

| Role    | Email                    | Password  |
|---------|--------------------------|-----------|
| Admin   | admin@attendance.com     | admin123  |

Admin can create Teacher accounts, Teachers can create Student accounts.

## Project Structure

```
attendance-system/
├── app.py              # Flask app factory + seed
├── models.py           # SQLAlchemy models
├── routes/
│   ├── auth.py         # Login/logout
│   ├── admin.py        # Admin panel
│   ├── teacher.py      # Teacher dashboard
│   ├── student.py      # Student dashboard
│   └── attendance.py   # QR status API
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── sidebar.html
│   ├── admin/
│   ├── teacher/
│   └── student/
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── qr/             # Generated QR images
├── requirements.txt
└── README.md
```

## Workflow

### QR Attendance Flow
1. Teacher selects subject → clicks Generate QR
2. QR code created with unique session ID (expires in N minutes)
3. Students open Scan QR page → allow camera
4. Student scans QR → backend validates session → marks attendance
5. Duplicate prevention: one attendance per student per session per day

## Database Schema

- **User** — id, name, email, password_hash, role
- **Student** — user_id, roll_number, department, semester
- **Teacher** — user_id, department
- **Subject** — subject_name, subject_code, teacher_id
- **Attendance** — student_id, subject_id, date, status, marked_by
- **QRSession** — session_id, subject_id, teacher_id, expires_at, is_active
