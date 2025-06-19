FROM python:3.12

WORKDIR /app

# 复制依赖文件
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 暴露正确的端口（根据 server.py 中的默认端口）
EXPOSE 7860

# 使用正确的命令启动服务器
CMD ["python", "src/server.py", "run"]