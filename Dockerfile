FROM python:3.9.19-slim AS base

RUN apt-get update \
    && apt-get install -y python3-dev default-libmysqlclient-dev build-essential pkg-config libgl1-mesa-glx libglib2.0-0 \
    && apt-get install -y bash curl wget vim \
    && apt-get install -y antiword \
    && apt-get autoremove \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/usr/lib/python3/dist-packages/:$PYTHONPATH

RUN pip install nltk  # 如果基础镜像还没装nltk
RUN python -m nltk.downloader -d /usr/local/share/nltk_data stopwords punkt
ENV NLTK_DATA=/usr/local/share/nltk_data


COPY requirements.txt /env/requirements.txt


# 使用官方pip源，如果网络慢可以改为国内镜像源
# RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/


RUN cd /env && pip install -r requirements.txt

# 设置时区
RUN rm -rf /etc/localtime
RUN ln -s /usr/share/zoneinfo/Asia/Shanghai /etc/localtime


EXPOSE 8080

WORKDIR /app

# 复制项目文件
COPY app/ ./app/
COPY common/ ./common/
COPY bella_rag/ ./bella_rag/
COPY deep_rag/ ./deep_rag/
COPY init/ ./init/
COPY conf/ ./conf/
COPY template/ ./template/
COPY resources/ ./resources/

# 复制启动文件
COPY manage.py ./
COPY app.py ./
COPY gunicorn.conf.py ./

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
