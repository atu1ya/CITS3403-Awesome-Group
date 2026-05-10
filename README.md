# CITS3403-Awesome-Group

## Description
This repository hosts the necessary files for the assessed project related to CITS3403. This project is a build of the website "SmartMeet", where people are allowed to collaborate and schedule meetings with each other based on their own individual schedules.

## Members

| Name           | Surname    | ID       | Role               |
| -------------- | ---------- | -------- | ------------------ |
| Muhammad Imran | Bin Ismail | 24277844 | Backend developer  |
| Suhrid         | Pushan     | 24306853 | Frontend developer |
| Hyun           | Lee        | 24182536 | Frontend developer |
| Atulya         | Chaturvedi | 24225113 | Backend developer  |
|                |            |          |                    |

*Note that the roles column does not imply the developer has only worked within that role; It outlines which category their most significant contributions fall under.

## Getting Started
Make sure Python 3.10+ is installed on your machine.

1. Clone this repository and open it in VS Code (or your terminal).
2. Create and activate a virtual environment.
3. Install dependencies from `requirements.txt`.
4. Add environment variables for email + secret key.
5. Run the app.

### Windows quick setup
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set SECRET_KEY=replace-with-a-random-secret
set MAIL_USERNAME=your-email@gmail.com
set MAIL_PASSWORD=your-app-password
python run.py
```

### macOS/Linux quick setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY='replace-with-a-random-secret'
export MAIL_USERNAME='your-email@gmail.com'
export MAIL_PASSWORD='your-app-password'
python run.py
```

### Notes
- The local server URL is printed in the terminal after startup.
- In development, the app reloads when files change.
- Runtime errors and tracebacks are shown in the terminal.

## Workflow
The general workflow is outlined in steps below.

1. Create a new branch for your feature/change.
2. Activate your virtual environment (heavily recommended) using the command ``venv/Scripts/activate``.
3. Make your changes and commit.
4. Create a new PR on the repository.

You may not necessarily have to make all your changes in one commit. Instead you are recommended to separate your changes into different, meaningful commits. 

Creating a virtual environment is recommended (along with installing packages via requirements.txt) to ensure everyone has, and is using the same packages and their corresponding versions.
