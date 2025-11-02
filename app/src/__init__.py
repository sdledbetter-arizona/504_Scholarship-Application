from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import os, secrets


db = SQLAlchemy()

def create_app():

    from .views.core import core
    from .views.auth import auth
    from .data.models import User

    app = Flask(__name__)

    
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Use your email server
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'sdledbetter0616@gmail.com'
    app.config['MAIL_PASSWORD'] = 'qxak ahkp lnke uagl'
    app.config['MAIL_DEFAULT_SENDER'] = 'sdledbetter0616@gmail.com'

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this application.'
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    app.register_blueprint(core, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(DATA_DIR,"scholarship.db")}"
    db.init_app(app)

    with app.app_context():
        db.create_all()

    return app