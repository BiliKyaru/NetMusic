# webapp/main.py
from flask import Blueprint, render_template, redirect, url_for, request, send_from_directory, abort, \
    current_app, jsonify, session
from flask_login import login_required, current_user
from .models import User, Music
from .auth import ChangeUsernameForm, ChangePasswordForm
from .extensions import db, socketio
import os, uuid, hashlib, io
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.flac import FLAC
from pydub import AudioSegment
from werkzeug.utils import secure_filename
from sqlalchemy import or_, asc, desc
from unidecode import unidecode
import re

main_bp = Blueprint('main', __name__)


def _get_music_query(search_query='', sort_by='upload_time', order='desc', page=1, per_page=20, file_type='all'):
    """封装音乐搜索和排序逻辑"""
    sort_map = {
        'title': Music.romanized_name,
        'duration': Music.duration,
        'upload_time': Music.upload_time
    }
    sort_column = sort_map.get(sort_by, Music.upload_time)
    order_expression = asc(sort_column) if order == 'asc' else desc(sort_column)
    music_query = Music.query.order_by(order_expression)

    if file_type == 'flac':
        music_query = music_query.filter(Music.stored_name.ilike('%.flac'))
    elif file_type == 'mp3':
        music_query = music_query.filter(Music.stored_name.ilike('%.mp3'))

    if search_query:
        search_term = f'%{search_query}%'
        music_query = music_query.filter(
            or_(
                Music.original_name.ilike(search_term),
                Music.romanized_name.ilike(search_term),
                Music.romanized_initials.ilike(search_term)
            )
        )

    return music_query.paginate(page=page, per_page=per_page, error_out=False)


def _process_flac_audio(file_content, original_name):
    """处理高质量FLAC文件，进行标准化转换"""
    if not current_app.config.get('FLAC_ENABLE_NORMALIZATION', False):
        # 如果在配置中禁用了，则直接返回原始内容
        return file_content, False

    target_rate = current_app.config.get('FLAC_TARGET_SAMPLE_RATE', 44100)
    target_bits = current_app.config.get('FLAC_TARGET_BITS_PER_SAMPLE', 16)
    target_width = current_app.config.get('FLAC_TARGET_SAMPLE_WIDTH', 2)
    hq_params = current_app.config.get('FLAC_HQ_FFMPEG_PARAMS', [])

    is_converted = False
    try:
        audio_info = FLAC(io.BytesIO(file_content))

        if audio_info.info.bits_per_sample > target_bits or audio_info.info.sample_rate > target_rate:
            sound = AudioSegment.from_file(io.BytesIO(file_content), format="flac")

            standard_sound = sound.set_sample_width(target_width).set_frame_rate(target_rate)
            buffer = io.BytesIO()
            standard_sound.export(buffer, format="flac", parameters=hq_params)

            file_content = buffer.getvalue()
            is_converted = True

    except Exception as e:
        current_app.logger.error(f"处理FLAC文件 {original_name} 失败: {str(e)}")
        raise ValueError(f"处理文件 {original_name} 失败")
    return file_content, is_converted


def _check_pagination_validity(pagination, endpoint):
    """检查分页是否有效，如果无效则返回重定向"""
    page = request.args.get('page', 1, type=int)
    if not pagination.items and page > 1:
        args = request.args.copy()
        args['page'] = 1
        return redirect(url_for(endpoint, **args))
    return None


def _get_sorting_and_search_params():
    """从请求和session中获取排序和搜索参数"""
    # (这是你改进后的版本)
    sort_by_raw = request.args.get('sort_by', session.get('sort_by', 'upload_time'))
    order_raw = request.args.get('order', session.get('order', 'desc'))
    type_raw = request.args.get('type', session.get('file_type', 'all'))

    valid_sort_by = ['title', 'duration', 'upload_time']
    valid_order = ['asc', 'desc']
    valid_types = ['all', 'flac', 'mp3']

    sort_by = sort_by_raw if sort_by_raw in valid_sort_by else 'upload_time'
    order = order_raw if order_raw in valid_order else 'desc'
    file_type = type_raw if type_raw in valid_types else 'all'

    session['sort_by'] = sort_by
    session['order'] = order
    session['file_type'] = file_type

    search_query = request.args.get('q', '')

    return search_query, sort_by, order, file_type


MAX_FILENAME_LENGTH = 200


def _validate_upload_file(original_name_full):
    """验证上传的文件名和类型 (修改为只接收文件名)"""
    display_name = os.path.splitext(original_name_full)[0]
    filename_lower = original_name_full.lower()

    if len(display_name) > MAX_FILENAME_LENGTH:
        msg = f'文件名过长（超过{MAX_FILENAME_LENGTH}字符），已跳过：{original_name_full}'
        return None, None, msg

    if not filename_lower.endswith(('.mp3', '.flac')):
        msg = f'文件 {original_name_full} 不是支持的音乐格式'
        return None, None, msg

    # 返回验证通过的名称
    return display_name, filename_lower, None


def _process_audio(file_content, filename_lower, original_name_full):
    """处理音频内容（FLAC转换、读取时长、计算MD5）"""
    is_converted = False
    if filename_lower.endswith('.flac'):
        processed_content, is_converted = _process_flac_audio(file_content, original_name_full)
        if processed_content is None:
            return None, None, None, False, f"处理FLAC文件 {original_name_full} 失败，已跳过"
        file_content = processed_content

    try:
        file_obj = io.BytesIO(file_content)
        if filename_lower.endswith('.mp3'):
            audio = MP3(file_obj)
        else:
            audio = FLAC(file_obj)
        duration = int(audio.info.length)
        file_obj.seek(0)
    except (HeaderNotFoundError, Exception) as e:
        current_app.logger.error(f"文件可能已损坏 {original_name_full}: {str(e)}")
        return None, None, None, False, f'文件可能已损坏，已跳过：{original_name_full}'

    file_hash = hashlib.md5(file_content).hexdigest()
    return file_content, duration, file_hash, is_converted, None


def _create_music_record(display_name, safe_name, unique_name, file_hash, duration, user_id):
    """创建 Music 数据库记录对象"""
    romanized_name = unidecode(display_name)
    initials_list = re.findall(r'\b\w', romanized_name)
    romanized_initials = "".join(initials_list)

    music = Music(
        original_name=display_name,
        romanized_name=romanized_name,
        romanized_initials=romanized_initials,
        filename=safe_name,
        stored_name=unique_name,
        md5_hash=file_hash,
        duration=duration,
        user_id=user_id
    )
    return music


def _process_uploaded_file_task(app, file_content, original_name_full, user_id):
    """
    在后台线程中处理上传的文件。
    需要传入 app 对象来创建数据库和应用上下文。
    """
    with app.app_context():
        try:
            upload_folder = current_app.config['UPLOAD_FOLDER']

            # 验证文件名
            display_name, filename_lower, error_msg = _validate_upload_file(original_name_full)
            if error_msg:
                raise ValueError(error_msg)  # 抛出异常由 try/except 捕获

            # 处理音频 (FLAC转换, MD5, 时长)
            file_content, duration, file_hash, is_converted, error_msg = _process_audio(
                file_content, filename_lower, original_name_full
            )
            if error_msg:
                raise ValueError(error_msg)

            # 检查MD5是否重复
            if Music.query.filter_by(md5_hash=file_hash).first():
                current_app.logger.info(f"后台跳过重复文件: {original_name_full}")
                socketio.emit('upload_status', {
                    'message': f'文件 {original_name_full} 已存在，已跳过。',
                    'category': 'info'
                })
                return

            # 保存文件
            safe_name = secure_filename(original_name_full)
            file_ext = os.path.splitext(filename_lower)[1]
            unique_name = f"{uuid.uuid4()}{file_ext}"
            save_path = os.path.join(upload_folder, unique_name)

            with open(save_path, 'wb') as f:
                f.write(file_content)

            # 创建数据库记录
            music = _create_music_record(
                display_name, safe_name, unique_name, file_hash, duration, user_id
            )
            db.session.add(music)
            db.session.commit()

            # 通知所有客户端
            socketio.emit('music_added', {'new_ids': [music.id]})
            socketio.emit('upload_status', {
                'message': f'文件 {original_name_full} 已成功上传！',
                'category': 'success'
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"后台处理文件 {original_name_full} 失败: {str(e)}")
            socketio.emit('upload_status', {
                'message': f'文件 {original_name_full} 处理失败: {str(e)}',
                'category': 'danger'
            })


# --- 路由和视图函数 ---
@main_bp.route('/')
def root():
    if not User.query.first():
        return redirect(url_for('auth.setup'))
    return redirect(url_for('main.index'))


@main_bp.route('/index/')
def index():
    if not User.query.first():
        return redirect(url_for('auth.setup'))
    if current_user.is_authenticated:
        return redirect(url_for('main.admin'))

    page = request.args.get('page', 1, type=int)
    search_query, sort_by, order, file_type = _get_sorting_and_search_params()
    pagination = _get_music_query(search_query, sort_by, order, page=page, file_type=file_type)

    redirect_or_none = _check_pagination_validity(pagination, 'main.index')
    if redirect_or_none:
        return redirect_or_none

    music_list = pagination.items

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_music_list.html', music_list=music_list, pagination=pagination,
                               search_query=search_query, sort_by=sort_by, order=order, file_type=file_type)

    return render_template('index.html', music_list=music_list, pagination=pagination, search_query=search_query,
                           sort_by=sort_by, order=order, file_type=file_type)


@main_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    if not current_user.is_admin:
        abort(403)

    upload_folder = current_app.config['UPLOAD_FOLDER']
    files = request.files.getlist('file')
    response_messages = []

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    if not files or all(f.filename == '' for f in files):
        response_messages.append({'message': '请先选择要上传的文件。', 'category': 'danger'})
        return jsonify({'success': False, 'messages': response_messages})

    # 获取真实的 app 对象，用于传递给后台任务
    real_app = current_app._get_current_object()

    files_submitted_count = 0

    try:
        for file in files:
            if file.filename == '':
                continue

            # 在请求上下文中快速完成 I/O 和数据准备
            original_name_full = file.filename
            file_content = file.read()
            user_id = current_user.id

            # 将所有耗时任务交给后台线程
            socketio.start_background_task(
                _process_uploaded_file_task,
                real_app,  # 传入 app 对象
                file_content,  # 传入文件内容
                original_name_full,  # 传入文件名
                user_id  # 传入用户 ID
            )
            files_submitted_count += 1

        if files_submitted_count == 0:
            response_messages.append({'message': '未选择任何有效文件。', 'category': 'danger'})
            return jsonify({'success': False, 'messages': response_messages})

    except Exception as e:
        # 这个 catch 块只捕获提交任务之前的错误 (例如 file.read() 失败)
        current_app.logger.error(f'提交上传任务时发生严重错误: {str(e)}')
        response_messages.append({'message': '提交任务失败，请检查服务器日志。', 'category': 'danger'})
        return jsonify({'success': False, 'messages': response_messages})

    # 立即返回成功响应，告知用户任务已提交
    response_messages.append(
        {'message': f'已成功提交 {files_submitted_count} 个文件到后台处理。', 'category': 'success'})
    return jsonify({'success': True, 'messages': response_messages})


@main_bp.route('/music/<filename>')
def music(filename):
    mimetype = 'audio/mpeg' if filename.lower().endswith('.mp3') else \
        'audio/flac' if filename.lower().endswith('.flac') else None
    if not mimetype:
        abort(404)
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        filename,
        mimetype=mimetype
    )


@main_bp.route('/delete/batch', methods=['POST'])
@login_required
def delete_batch_music():
    if not current_user.is_admin:
        abort(403)

    data = request.json
    music_ids = data.get('music_ids')
    try:
        current_page = int(data.get('current_page', 1))
    except (ValueError, TypeError):
        current_page = 1
    per_page = 20

    if not music_ids or not isinstance(music_ids, list):
        return jsonify({'success': False, 'message': '未提供有效的音乐ID列表。'}), 400

    deleted_ids = []
    errors = []
    total_music_count_before = Music.query.count()

    for music_id in music_ids:
        music = db.session.get(Music, music_id)
        if music:
            try:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], music.stored_name)
                if os.path.exists(file_path):
                    os.remove(file_path)

                db.session.delete(music)
                db.session.commit()
                deleted_ids.append(music_id)
            except Exception as e:
                db.session.rollback()
                errors.append(music.original_name)
                current_app.logger.error(f"删除音乐 {music.original_name} (ID: {music_id}) 失败: {str(e)}")

    total_music_count_after = total_music_count_before - len(deleted_ids)

    if deleted_ids:
        socketio.emit('remove_music_items_batch', {
            'music_ids': deleted_ids,
            'total_music_count_after': total_music_count_after
        })

    total_pages_after = max(1, (total_music_count_after + per_page - 1) // per_page)
    redirect_page = min(current_page, total_pages_after)

    response_data = {
        'success': not errors,
        'redirect_page': redirect_page
    }

    if not errors:
        response_data['message'] = f'成功删除 {len(deleted_ids)} 首音乐！'
    else:
        failed_names = ', '.join(errors[:2]) + ('...' if len(errors) > 2 else '')
        response_data['message'] = f'操作完成。成功删除 {len(deleted_ids)} 首，失败 {len(errors)} 首 ({failed_names})。'

    status_code = 200 if not errors else 207
    return jsonify(response_data), status_code


@main_bp.route('/admin/')
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)

    page = request.args.get('page', 1, type=int)
    search_query, sort_by, order, file_type = _get_sorting_and_search_params()

    tab_param = request.args.get('tab')
    if tab_param not in ['username', 'password']:
        active_tab = 'username'
    else:
        active_tab = tab_param

    pagination = _get_music_query(search_query, sort_by, order, page=page, file_type=file_type)

    redirect_or_none = _check_pagination_validity(pagination, 'main.admin')
    if redirect_or_none:
        return redirect_or_none

    music_list = pagination.items
    username_form = ChangeUsernameForm()
    password_form = ChangePasswordForm()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_music_list.html', music_list=music_list, pagination=pagination,
                               search_query=search_query, sort_by=sort_by, order=order, file_type=file_type)

    return render_template('admin.html',
                           music_list=music_list,
                           pagination=pagination,
                           search_query=search_query,
                           sort_by=sort_by,
                           order=order,
                           file_type=file_type,
                           username_form=username_form,
                           password_form=password_form,
                           active_tab=active_tab)


@main_bp.route('/admin/change-username', methods=['POST'])
@login_required
def change_username():
    form = ChangeUsernameForm()
    if form.validate_on_submit():
        current_user.username = form.new_username.data
        db.session.commit()
        return jsonify({'success': True, 'messages': [{'message': '用户名已成功修改！', 'category': 'success'}]})
    else:
        messages = [{'message': error, 'category': 'danger'} for errors in form.errors.values() for error in errors]
        return jsonify({'success': False, 'messages': messages})


@main_bp.route('/admin/change-password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user = current_user
        if user.check_password(form.new_password.data):
            return jsonify(
                {'success': False, 'messages': [{'message': '新密码不能与当前密码相同。', 'category': 'danger'}]})

        user.set_password(form.new_password.data)
        db.session.commit()
        return jsonify({'success': True, 'messages': [{'message': '密码已成功修改！', 'category': 'success'}]})

    else:
        if 'current_password' in form.errors:
            messages = [{'message': error, 'category': 'danger'} for error in form.errors['current_password']]
        else:
            messages = [{'message': error, 'category': 'danger'} for errors in form.errors.values() for error in errors]

        return jsonify({'success': False, 'messages': messages})