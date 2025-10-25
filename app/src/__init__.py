from flask import Flask
from flask_login import LoginManager


def create_app():

    from .views.core import core
    from .views.auth import auth

    app = Flask(__name__)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this application.'
    login_manager.login_message_category = "warning"
    #login_manager.init_app(app)

    app.register_blueprint(core, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')


    return app