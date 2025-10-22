# 💿 网络音乐机

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue)](https://www.python.org/)
[![Flask 2.3+](https://img.shields.io/badge/Flask-2.3%2B-green)](https://flask.palletsprojects.com/)
[![AI Assisted](https://img.shields.io/badge/AI%20Assisted-lightgrey?logo=google-gemini&logoColor=white&color=4285F4)](https://gemini.google.com/app)

## 📖 项目简介
基于Flask框架开发，为[网络音乐机](https://www.mcmod.cn/class/4935.html)模组提供一个现代化的、安全易部署的本地音乐链接生成与管理后台。<br>
[CurseForge](https://www.curseforge.com/minecraft/mc-mods/net-music) | [Modrinth](https://modrinth.com/mod/net-music)

## 🌟 功能特性
本项目在原作者的核心功能上，进行了全面的现代化重构和功能增强。
* **现代化架构**：采用应用工厂 (Application Factory) 和 蓝图 (Blueprints) 的模块化结构，代码可维护性极高。
* **实时无刷新**：全站基于`Socket.IO`实现实时通信。音乐的上传、删除操作会即时、无刷新地同步到所有客户端。
* **音乐管理**：
  - 支持 MP3 / FLAC 格式的音乐文件上传，并能进行多文件批量上传。
  - 上传时通过 MD5 哈希检测重复文件，避免数据冗余。
  - 自动将高码率/高采样率的 FLAC 文件标准化为 16-bit/44.1kHz，保证兼容性。
* **安全认证**：
  - 完善的管理员账户系统。
  - 安全密钥管理，通过 .env 文件进行安全的环境变量配置。
  - 防暴力破解，内置登录失败次数限制与 IP 临时锁定机制。
* **Docker 一键部署**：提供`Dockerfile`和`docker-compose`，实现零配置一键启动。
* **企业级 Web 服务**：使用`gunicorn`和`eventlet`作为 Web 服务器，性能远超 Flask 原生开发服务器。

---

## 🚀 快速开始

### Docker 部署

推荐使用`Docker Compose`一键部署。<br>
为了加速在中国大陆的构建速度，`Dockerfile`使用了清华大学镜像源。 <br>
如果你在中国大陆以外的地区，请修改以下内容：

**移除 apt 镜像源**：
   ```
   RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources
   ```
**修改 pip 镜像源**：
   ```
   RUN pip install --no-cache-dir -r requirements.txt
   ```

1. 确保您已安装 [Docker](https://www.docker.com/get-started) 和 [Docker Compose](https://docs.docker.com/compose/install/)。
2. 克隆仓库
    ```bash
    https://github.com/BiliKyaru/NetMusic.git
    cd NetMusic
    ```
3. 在项目根目录创建一个名为`.env`的文件。
4. 获取密钥
    ```bash
   # Linux / macOS
    python3 -c "import secrets; print(secrets.token_hex(32))"
    ```
    你将得到一长串随机字符，例如 f8e23b6b...<br>
    将这个密钥复制到 .env 文件。
    ```bash
    SECRET_KEY=[your key]
    ```
4. 启动服务
    ```bash
    docker-compose up --build -d
    ```

---

## 🛠️ 本地开发

### Windows

1. 确保您已安装 Python 3.12+、Git 和 FFmpeg
2. 克隆仓库
   ```bash
    https://github.com/BiliKyaru/NetMusic.git
    cd NetMusic
    ```
3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```
4. 与 Docker 部署 3、4 步骤相同，在项目根目录创建 .env 文件并填入 SECRET_KEY。
   ```bash
   # Windows
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. 启动应用:
   ```bash
   python run.py
   ```
   应用将在 http://127.0.0.1:3355 启动

---

## ⚙️ 应用配置

你可以在`config.py`调整配置：
* **FLAC_ENABLE_NORMALIZATION**: 是否启用高规格 FLAC 自动转换功能。
* **FLAC_TARGET_SAMPLE_RATE**: 转换目标采样率。
* **FLAC_TARGET_BITS_PER_SAMPLE**: 转换目标位深。
* **LOCKOUT_SCHEDULE**: 登录失败锁定策略。