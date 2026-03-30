# 反重力剧本生成器

这是一个轻量级、高级感、一键生成充满宿命感电影剧本的工具应用。基于纯原生的 HTML 界面和轻量的 Python FastAPI 后端构建。

## 运行环境准备

在运行之前，确保你已经获取了 Gemini API Key（或者兼容格式的其他 LLM API Key）。

### 方法 1: 使用 Docker 一键运行 (推荐)

只需要将代码目录配置为 Docker 项目，运行以下命令即可：

```bash
# 1. 构建 Docker 镜像
docker build -t antigravity-script .

# 2. 运行并注入关键配置 (请替换你的 GEMINI_API_KEY)
docker run -d -p 8000:8000 -e GEMINI_API_KEY="AIzaSyXXXXXXXXXXXXXXXX" antigravity-script
```
访问 http://localhost:8000 开始创作。

### 方法 2: VS Code 本地运行

在终端或 VS Code 终端内运行：

```bash
# 1. 安装项目依赖
pip install -r requirements.txt

# 2. 声明 API 变量 (Windows PowerShell 示例:)
$env:GEMINI_API_KEY="AIzaSyXXXXXXXXXXXXXXXX"

# 3. 启动应用
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
访问 http://localhost:8000 即可。

## 操作说明
1. 填入四个变量（时代背景、具体地点、底层身份、逆袭元素）。
2. 点击发光按钮 "一键生成宿命"。
3. 文本生成支持一键复制，内容直出大段落排版。
