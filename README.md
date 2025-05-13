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
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
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

## 文件结构与命名说明

在 Pipecat 及类似 AI/Agent 框架中，常见的文件命名如 `server.py`、`runner.py`、`bot.py`，是为了清晰表达每个模块的职责和分层，便于开发、维护和扩展。

### 1. server.py
- **作用**：通常作为服务端入口，负责启动 HTTP/WebSocket/WebRTC 等服务，监听外部请求，管理会话生命周期。
- **典型内容**：API 路由、会话管理、与前端/客户端通信的逻辑。
- **好处**：将服务启动和网络通信逻辑与业务逻辑分离，便于部署和横向扩展。

### 2. runner.py
- **作用**：负责"运行"或调度核心流程，比如会话管道、任务队列、异步事件循环等。
- **典型内容**：流程控制、任务调度、异步执行、资源管理。
- **好处**：将流程调度与业务实现解耦，便于测试和复用。

### 3. bot.py
- **作用**：定义"智能体"或"机器人"的具体行为和逻辑。
- **典型内容**：对话策略、消息处理、与 AI 服务的集成、事件响应。
- **好处**：聚焦于业务和交互逻辑，便于扩展不同类型的 bot。

### 这样设计的优点
- **单一职责**：每个文件只做一件事，易于理解和维护。
- **可扩展性**：可以很方便地增加新的 bot、runner 或 server 实现。
- **解耦**：网络、调度、业务逻辑分离，便于团队协作和单元测试。
- **社区惯例**：很多 Python/AI 项目都采用类似命名，降低学习和迁移成本。

> 参考：
> - [Pipecat 官方文档](https://docs.pipecat.ai/)
> - [Pipecat GitHub 源码结构](https://github.com/pipecat-ai/pipecat)
> - 其他主流 AI/Agent 框架（如 langchain、fastapi、transformers）也有类似分层设计

---

如需集成更多 AI 服务或高级用法，请参考官方文档。 