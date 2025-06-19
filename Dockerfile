FROM python:3.12

WORKDIR /app

# 安装系统依赖（OpenCV需要）
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    gfortran \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制所有requirements文件
COPY requirements.txt ./
COPY src/webapp/requirements.txt ./src/webapp/
COPY src/bots/requirements.txt ./src/bots/

# 安装依赖
RUN pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制源代码
COPY src/ ./src/

# 暴露正确的端口（根据 server.py 中的默认端口）
EXPOSE 7860

# 使用正确的命令启动服务器
CMD ["python", "src/server.py", "run"]