# Pipecat-AI 基础项目模板

## 简介

Pipecat 是一个用于构建实时语音和多模态对话代理的开源 Python 框架。它可以帮助你快速集成语音识别、文本转语音、LLM、WebRTC/WebSocket 等服务，专注于打造独特的 AI 体验。

- 官方文档: https://docs.pipecat.ai/
- GitHub: https://github.com/pipecat-ai/pipecat

## 主要特性
- 语音优先设计，内置语音识别、TTS 和对话处理
- 支持多种 AI 服务（如 OpenAI、Anthropic、Deepgram 等）
- 管道式架构，易于扩展和组合
- 实时流式处理，低延迟
- 支持本地和云端部署

## 快速开始

### 1. 使用 Python 虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pipecat-ai
```

### 2. 运行示例

创建 `app.py`：

```python
import asyncio
from pipecat.frames.frames import TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner

async def main():
    # 这里可以添加你的 Pipecat 组件和逻辑
    print("Pipecat 基础项目已启动！")

if __name__ == "__main__":
    asyncio.run(main())
```

运行：
```bash
python app.py
```

### 3. Docker 部署

本项目已包含 Dockerfile 和 docker-compose.yml，支持一键部署。

#### 构建镜像
```bash
docker build -t pipecat-app .
```

#### 使用 Docker Compose 启动
```bash
docker-compose up --build
```

## 目录结构
```
├── app.py              # 主程序入口
├── requirements.txt    # Python 依赖
├── Dockerfile          # Docker 镜像构建文件
├── docker-compose.yml  # Docker Compose 配置
├── .env.example        # 环境变量模板
├── .gitignore          # Git 忽略文件
└── README.md           # 项目说明
```

## 参考与社区
- [Pipecat 官方文档](https://docs.pipecat.ai/)
- [Pipecat GitHub](https://github.com/pipecat-ai/pipecat)
- [PyPI: pipecat-ai](https://pypi.org/project/pipecat-ai/)

---

如需集成更多 AI 服务或高级用法，请参考官方文档。 