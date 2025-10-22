import os

# 获取当前文件所在目录的绝对路径
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("未设置 SECRET_KEY 环境变量。应用无法在不安全的状态下启动。")

    # 数据库和上传配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'instance', 'music.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')

    # 登录失败锁定配置: {失败次数: 锁定秒数}
    LOCKOUT_SCHEDULE = {3: 60, 4: 300, 5: 900}

    # 如果为True，所有超过目标阈值的FLAC文件都将被转换。
    # 设为 False 以禁用此功能。
    FLAC_ENABLE_NORMALIZATION = True

    # 定义“高质量”FLAC的阈值，也是转换的目标值。
    # 任何超过此处定义的 采样率 或 位深 的文件都将被转换。
    FLAC_TARGET_SAMPLE_RATE = 44100
    FLAC_TARGET_BITS_PER_SAMPLE = 16

    # 16 bits = 2 bytes。 24 bits = 3 bytes。
    # 请确保此值与上面的 FLAC_TARGET_BITS_PER_SAMPLE 对应。
    FLAC_TARGET_SAMPLE_WIDTH = 2

    # 转换时使用的高质量 FFmpeg (pydub) 参数
    # 'soxr' 提供了高质量的重采样 (resampling)
    FLAC_HQ_FFMPEG_PARAMS = ['-af', 'aresample=resampler=soxr:precision=28:dither_method=triangular_hp']