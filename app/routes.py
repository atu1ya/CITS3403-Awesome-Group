from app import app
import flask as flk

@app.route("/")
def home():
    return flk.send_from_directory("static", "index.html")

