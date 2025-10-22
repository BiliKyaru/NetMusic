from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, current_user
from .models import User, LoginAttempt
from .extensions import db
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from flask_wtf import FlaskForm
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)


# --- 表单类 ---
class SetupForm(FlaskForm):
    username = StringField('管理员用户名', validators=[
        DataRequired(message='用户名不能为空。'),
        Length(min=4, max=20, message='用户名长度必须在4到20个字符之间。'),
        Regexp('^[A-Za-z0-9_]+$', message='用户名只能包含字母、数字和下划线。')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='密码不能为空。'),
        Length(min=6, message='密码长度不能少于6个字符。'),
        Regexp('^[\x21-\x7E]+$', message='密码只能包含英文字母、数字和常用符号。')
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(message='请再次输入密码。'),
        EqualTo('password', message='两次输入的密码不一致。')
    ])
    submit = SubmitField('创建管理员账户')


class LoginForm(FlaskForm):
    username = StringField('管理员账户', validators=[DataRequired()])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')


class ChangeUsernameForm(FlaskForm):
    new_username = StringField('新用户名', validators=[
        DataRequired(message='用户名不能为空。'),
        Length(min=4, max=20, message='用户名长度必须在4到20个字符之间。'),
        Regexp('^[A-Za-z0-9_]+$', message='用户名只能包含字母、数字和下划线。')
    ])

    # noinspection PyMethodMayBeStatic
    def validate_new_username(self, field):
        if current_user.is_authenticated and field.data == current_user.username:
            raise ValidationError('新用户名不能与当前用户名相同。')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('当前密码', validators=[DataRequired(message='请输入当前密码。')])
    new_password = PasswordField('新密码', validators=[
        DataRequired(message='新密码不能为空。'),
        Length(min=6, message='密码长度不能少于6个字符。'),
        Regexp('^[\x21-\x7E]+$', message='密码只能包含英文字母、数字和常用符号。')
    ])
    confirm_password = PasswordField('确认新密码', validators=[
        DataRequired(message='请再次输入新密码。'),
        EqualTo('new_password', message='两次输入的密码不一致。')
    ])

    def validate_current_password(self, field):
        # field.data 是用户在“当前密码”输入框中填写的值
        if not current_user.check_password(field.data):
            # 如果密码不正确，就引发一个验证错误
            raise ValidationError('当前密码不正确。')
# --- 路由和视图函数 ---

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.first():
        flash('管理员账户已存在，请直接登录。', 'info')
        return redirect(url_for('auth.login'))

    form = SetupForm()
    if form.validate_on_submit():
        admin_user = User(username=form.username.data, is_admin=True)
        admin_user.set_password(form.password.data)
        db.session.add(admin_user)
        db.session.commit()

        flash('创建成功！请使用刚才设置的账户进行登录。', 'success')
        return redirect(url_for('auth.login'))

    return render_template('setup.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if not User.query.first():
        return redirect(url_for('auth.setup'))
    if current_user.is_authenticated:
        return redirect(url_for('main.admin'))

    form = LoginForm()
    ip_address = request.remote_addr
    attempt_info = db.session.query(LoginAttempt).filter_by(ip_address=ip_address).first()
    lockout_schedule = current_app.config['LOCKOUT_SCHEDULE']

    # --- 检查IP是否已被锁定 ---
    if attempt_info and attempt_info.lockout_until and attempt_info.lockout_until > datetime.utcnow():
        lockout_end_iso = attempt_info.lockout_until.isoformat() + "Z"
        return render_template('login.html', form=form, lockout_end=lockout_end_iso)

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        # --- 验证密码 ---
        if user and user.is_admin and user.check_password(form.password.data):
            # --- 登录成功 ---
            remember_me_checked = form.remember_me.data
            login_user(user, remember=remember_me_checked)
            session.permanent = remember_me_checked

            # 清除该IP的登录失败记录
            if attempt_info:
                db.session.delete(attempt_info)
                db.session.commit()

            return redirect(url_for('main.admin'))
        else:
            # --- 登录失败 ---
            flash('无效的管理员账户或密码', 'danger')

            if not attempt_info:
                attempt_info = LoginAttempt(ip_address=ip_address, attempts=0)
                db.session.add(attempt_info)

            attempt_info.attempts += 1
            lockout_duration = lockout_schedule.get(attempt_info.attempts)

            if lockout_duration:
                attempt_info.lockout_until = datetime.utcnow() + timedelta(seconds=lockout_duration)

            db.session.commit()
            return redirect(url_for('auth.login'))

    # --- 页面加载逻辑 (GET请求) ---
    return render_template('login.html', form=form, lockout_end=None)


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('您已成功退出登录。', 'success')
    return redirect(url_for('auth.login'))