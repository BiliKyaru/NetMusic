# webapp/__init__.py
from flask import Flask, render_template
from config import Config
from .extensions import db, login_manager, socketio, csrf
from .models import User
from datetime import timedelta
import os

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False,
                static_folder='static',
                template_folder='templates')

    app.jinja_env.add_extension('jinja2.ext.do')
    app.config.from_object(config_class)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True

    if not os.path.exists(os.path.join(app.root_path, '..', 'instance')):
        os.makedirs(os.path.join(app.root_path, '..', 'instance'))
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)
    csrf.init_app(app)

    # 配置 LoginManager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = None

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 注册蓝图
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    from .main import main_bp
    app.register_blueprint(main_bp)

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    return app