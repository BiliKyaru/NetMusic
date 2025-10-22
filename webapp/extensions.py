# webapp/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(async_mode='threading')
csrf = CSRFProtect()