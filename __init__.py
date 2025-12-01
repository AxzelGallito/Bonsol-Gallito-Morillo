from flask import Flask, render_template, send_from_directory
from flask_login import LoginManager
from .extensions import db
import os

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # -------------------- BASIC CONFIG -------------------- #
    app.config['SECRET_KEY'] = 'your_secret_key'

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # -------------------- DATABASE SETUP -------------------- #
    db_path = os.path.join(app.instance_path, 'database.sqlite3')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # -------------------- MEDIA FOLDER -------------------- #
    media_folder = os.path.join(app.root_path, 'media')
    os.makedirs(media_folder, exist_ok=True)
    app.config['MEDIA_FOLDER'] = media_folder

    @app.route('/media/<path:filename>')
    def media(filename):
        return send_from_directory(app.config['MEDIA_FOLDER'], filename)

    # -------------------- LOGIN MANAGER -------------------- #
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import Customer
    @login_manager.user_loader
    def load_user(user_id):
        return Customer.query.get(int(user_id))

    # -------------------- BLUEPRINTS -------------------- #
    from .views import views
    from .auth import auth
    from .admin import admin

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(admin, url_prefix='/')

    # -------------------- DATABASE CREATION -------------------- #
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all()
            print("Database created!")
    else:
        print("Existing database detected — using it.")

    return app