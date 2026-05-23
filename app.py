from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from models import db, User
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.teacher import teacher_bp
from routes.student import student_bp
from routes.attendance import attendance_bp
import os

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'qr-attendance-secret-key-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['QR_FOLDER'] = os.path.join(app.static_folder, 'qr')

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(attendance_bp)

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('auth.dashboard_redirect'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()
        seed_admin(app)

    return app

def seed_admin(app):
    from werkzeug.security import generate_password_hash
    from models import User
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            name='System Admin',
            email='admin@attendance.com',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin seeded: admin@attendance.com / admin123")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
