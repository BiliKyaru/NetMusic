# webapp/models.py
from .extensions import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

# --- 数据库模型 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Music(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_name = db.Column(db.String(200))
    romanized_name = db.Column(db.String(400), index=True)
    romanized_initials = db.Column(db.String(200), index=True)
    filename = db.Column(db.String(100))
    stored_name = db.Column(db.String(100), unique=True)
    md5_hash = db.Column(db.String(32), unique=True, nullable=True)
    duration = db.Column(db.Integer)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    @property
    def local_upload_time(self):
        """将存储的UTC时间转换为中国时区的时间"""
        if not self.upload_time:
            return None
        # 从数据库取出的时间是“朴素”的，我们首先告知它这是UTC时区
        utc_time = pytz.utc.localize(self.upload_time)
        # 将其转换为“Asia/Shanghai”时区
        china_tz = pytz.timezone('Asia/Shanghai')
        return utc_time.astimezone(china_tz)


class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(100), unique=True, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    lockout_until = db.Column(db.DateTime(timezone=True), nullable=True)
