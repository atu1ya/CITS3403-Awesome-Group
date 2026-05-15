from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
migrate = Migrate()
login_manager.login_view = 'main.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    from .routes import main
    app.register_blueprint(main)

    return app

@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))