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

## Getting started
Make sure you have python installed on your machine.

1. Run ``python -m venv venv`` in the project directory. A folder called venv should pop up.
2. Activate your virtual environment by running ``venv/Scripts/activate`` in the project directory.
3. Run ``pip install -r requirements.txt`` in the project directory.
4. You're good to go.

### Notes
To run the server, you can do so by simply running ``python run.py``. The URL you'll need to use will be listed in your terminal (if you're on VSCode, you may simply CTRL + Click the link). The server will indefinitely run until either the terminal is closed, you manually exit, or it crashes. 

The server automatically listens for changes and will restart accordingly after you've saved a file. This allows you to make changes dynamically.

Error logs and tracebacks should already be listed in the terminal when they happen. You may not need to use the developer console on the browser (unless you prefer it).

## Workflow
The general workflow is outlined in steps below.

1. Create a new branch for your feature/change.
2. Activate your virtual environment (heavily recommended) using the command ``venv/Scripts/activate``.
3. Make your changes and commit.
4. Create a new PR on the repository.

You may not necessarily have to make all your changes in one commit. Instead you are recommended to separate your changes into different, meaningful commits. 

Creating a virtual environment is recommended (along with installing packages via requirements.txt) to ensure everyone has, and is using the same packages and their corresponding versions.
