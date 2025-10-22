FROM python:3.12-slim

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

RUN apt-get update && \
    apt-get install -y ffmpeg --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

EXPOSE 3355

CMD [ "gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:3355", "run:app" ]