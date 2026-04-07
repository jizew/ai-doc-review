# AI 文档智能审校系统 (AI Document Review System)

基于大语言模型（LLM）的智能文档校对与润色工具，专为处理 Word (`.docx`) 文档而设计。
无论你是需要修正错别字、改善中文语法排版，还是希望为长篇文档附加批量智能批注，本项目都能帮你高效处理。

## ✨ 核心特性

- 🚀 **全面拥抱大语言模型生态**: 原生支持 OpenAI, Anthropic, DeepSeek, 通义千问 (Qwen), 智谱 AI (GLM) 以及 Ollama 本地化大模型。
- 📝 **开箱即用的 Word 文档支持**: 一键上传 `.docx` 文件，系统将自动进行分块解析与语义校验。
- 📊 **两套强大的审阅视角**:
  - **批注模式 (Comments)**: 直接在原文对应处悬挂 Word 批注，不破坏原始文档面貌（极其适合严肃审核）。
  - **修订模式 (Track Changes)**: 还原真实的人工修订痕迹，可“接受/拒绝”每项修改。
- ⚙️ **配置灵活性与健壮性**: 支持动态备用回退模型（Fallback）、自定义 API 端点中继、支持高并发并内建 API 速率重试保护。
- 💻 **可视化交互**: 基于 Streamlit 开发的浅色/深色护眼仪表盘，包含实时的 Token 开销、API 处理进度与错误统计。

---

## 🛠 初始化与安装

本项目对系统侵入极小。我们推荐通过标准 Python 虚拟环境进行隔离安装。

**1. 克隆代码或下载项目**

```bash
git clone https://github.com/YourUsername/AI-Doc-Review.git
cd AI-Doc-Review
```

**2. 创建并激活虚拟环境（推荐）**

```bash
python -m venv venv

# Windows 下激活：
venv\Scripts\activate
# Linux/macOS 下激活：
source venv/bin/activate
```

**3. 安装核心依赖**

```bash
pip install -r requirements.txt
```

> **🔥 为什么还需要 `ruamel.yaml` 依赖项？**  
> 因为本项目包含 Web 界面供你动态修改系统参数，传统的 Python Yaml 解析器在重写配置时**会彻底抹除掉 `#` 开头的所有人工说明注释**。  
> 我们在 `requirements.txt` 中已预装 `ruamel.yaml` （它是保留格式的安全解析器），能确保您保存配置后，您的 `config.yaml` 依然美观并带有提示信息。

---

## 🚀 启动与使用

在应用根目录下，执行我们提供的 Streamlit 启动指令：

```bash
streamlit run app.py
```

服务通常会启动在 `http://localhost:8501`。接下来您只需：
1. 在左侧面板填写您的模型 API 密钥（如 DeepSeek 或 OpenAI）以及生成参数配置。
2. 上传一个或一批待审阅的 `.docx` 文档。
3. 点击“开始审校”按钮，坐享其成。

---

## 🔧 系统配置 (`config.yaml`)

你可以通过 Web 界面右侧直接修改配置，也可以手动使用编辑器修改根目录生成的 `config.yaml`。

配置项极其直白，下面是一些关键项：
* **`llm`**: 管理模型调度。支持 `api_key` 鉴权与 `base_url` （用于接入 SiliconFlow 等中转站或自建镜像服务器）。
* **`proofreading.mode`**: 可以选择 `comments` 或者 `track_changes` 风格。
* **`proofreading.chunk_size`**: 分块字数（越短越精准但也消耗更多 token，建议保持在 500～800 字）。
* **`fallback_preset`**: 独家亮点！允许您设定一个备选模型预设；当默认智能模型遭遇内容安全拦截或结构破坏时，系统自动切走降维保护以防进程崩溃。

---

## 📚 常见问题解答 (FAQ)

### 1. 修改跟踪 (Track Changes) 怎么报错或不可用？
修订模式因为要深度修改 Word 原生 XML，需要可选模块包的支持。如果你非常需要它，请安装更高级的模块：
```bash
pip install docx-editor
```
或者
```bash
pip install docx-revisions==0.1.3
```

### 2. 本地跑 Ollama 要怎么填信息？
将 Provider 选为 `ollama`，Model 可以写你自己的本地模型如 `qwen:7b-chat`，无需 API Key（留空），基地址通常为 `http://localhost:11434`。详见左侧边栏对应说明。

### 3. 如何省钱 / 控制 Token 花销？
建议降低并发（`batch_size` 调小），利用**测试模式**（能锁定只审阅前两段）先观测目前设定的 AI Prompt 是否能输出有效结果。如果不满意，你可以在页面底部随时悬停编辑提示词。

---

## 📜 开源许可证
本项目采用 [MIT License](LICENSE) 授权，意味着你可以自由地进行个人魔改及用于大部分商业场景，请保留本项目声明即可。欢迎发 Pull Request 贡献你的绝妙点子！
