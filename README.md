# AI 文档智能审校系统

基于大语言模型（LLM）的智能文档校对与润色工具，专为处理 Word (`.docx`) 文档而设计。支持批注和修订两种输出模式，可对接市面上主流的 AI 服务商，也支持本地部署的 Ollama 模型。

---

## ✨ 核心特性

- 🚀 **多模型支持**: 兼容 OpenAI、Anthropic、DeepSeek、通义千问 (Qwen)、智谱 AI (GLM)、Ollama 及任意 OpenAI 兼容 API
- 📝 **Word 文档原生处理**: 上传 `.docx`，输出带批注或修订痕迹的 `.docx`，格式完整保留
- 📊 **两套审阅模式**:
  - **批注模式**: 以 Word 批注悬挂建议，原文不变（适合严肃审核）
  - **修订模式**: 生成 Track Changes 修订痕迹，可逐条接受/拒绝
- ⚙️ **完全可视化配置**: 所有参数（模型、API Key、审阅风格）均可在网页界面直接设置，无需编辑代码
- 🔄 **智能重试与回退**: 内置 API 限速重试（指数退避）和备用模型切换机制

---

## 🚀 快速开始（推荐）

> 唯一的前提：电脑上已安装 **Python 3.9 或更高版本**。
>
> 下载地址：https://www.python.org/downloads/
>
> ⚠️ Windows 安装时请务必勾选 **"Add Python to PATH"**。

### Windows 用户

双击项目文件夹中的 **`start.bat`**，脚本会自动完成：
1. 创建隔离的 Python 虚拟环境（仅首次运行）
2. 安装所有依赖包（仅首次运行）
3. 生成初始配置文件（仅首次运行）
4. 启动应用并自动打开浏览器

### macOS / Linux 用户

在终端中进入项目目录，运行：

```bash
bash start.sh
```

---

## ⚙️ 配置你的 API Key

**首次运行**时脚本会自动生成 `config.yaml`。用任意文本编辑器打开（如记事本），找到以下部分并填入你的信息：

```yaml
llm:
  provider: openai     # 你使用的服务商，详见下方说明
  model: gpt-4o        # 模型名称
  api_key: ""          # ← 在引号内填入你的 API Key
  base_url: ""         # 如使用中转服务，填写其地址；否则留空
```

**或者**，直接在应用启动后，在左侧面板"模型设置"中填写，点击"保存"即可，无需手动编辑文件。

### 各服务商信息

| 服务商 | provider 值 | 申请 API Key |
|--------|-------------|--------------|
| OpenAI | `openai` | https://platform.openai.com/api-keys |
| Anthropic | `anthropic` | https://console.anthropic.com/ |
| DeepSeek | `deepseek` | https://platform.deepseek.com/keys |
| 通义千问 | `qwen` | https://dashscope.aliyun.com/apiKey |
| 智谱 AI | `glm` | https://open.bigmodel.cn/ |
| Ollama（本地）| `ollama` | 无需 Key，本地运行 |
| 其他兼容服务 | `openai` | 填写 `base_url` 为对应地址 |

---

## ✏️ 自定义审阅指令

系统的所有 AI 指令（Prompt）保存在项目根目录的 **`prompts.json`** 文件中，可以用文本编辑器直接修改，无需任何编程知识。

### 文件结构说明

```
prompts.json
├── "system"           → AI 的角色设定（你是谁、要做什么）
├── "user_prompts"
│   ├── "standard"     → 标准模式的处理指令
│   ├── "detailed"     → 精细模式的处理指令（更严格的校对）
│   └── "minimal"      → 简洁模式的处理指令
└── "reference_system" → 参考文献格式化专用指令
```

### 修改示例

如果你希望 AI 专注于**学术论文风格**，可以修改 `"system"` 字段：

```json
{
  "system": "你是一位专注于学术论文审校的专家编辑。你的任务是...",
  ...
}
```

如果你希望 AI **只检查标点不修改表达**，可以修改 `"user_prompts"` 中的 `"standard"`：

```json
"standard": "请仅检查以下文本的标点符号错误，不要修改任何字词表达：\n{text}\n\n返回 JSON：{\"original\": \"\", \"revised\": \"\", \"comment\": \"\"}"
```

> ⚠️ **注意**：JSON 中换行符需用 `\n` 表示，引号需用 `\"` 转义。  
> 修改后，在运行的应用页面底部点击"重载 Prompt"按钮立即生效，无需重启。

你也可以直接在应用界面的"Prompt 设置"面板中在线编辑，更加直观。

---

## 🔧 进阶配置

`config.yaml` 中还有以下实用参数（均可在 Web 界面中调整）：

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `chunk_size` | 每次发给 AI 的字数 | 300-800 |
| `batch_size` | 同时发出的并发请求数 | 3-5 |
| `mode` | 审阅模式：`comments` 或 `track_changes` | `comments` |
| `fallback_preset` | 主模型失败时的备用模型 | 可选 |

启用**测试模式**（`test_mode.enabled: true`）可以只处理文件前几段，节省 token 用于验证 Prompt 效果。

---

## ❓ 常见问题

**Q: 修订模式（Track Changes）提示缺少组件？**  
A: 该模式需要额外安装可选库：
```bash
# 进入项目目录，激活虚拟环境后运行：
pip install docx-editor
```

**Q: 如何在不同文档之间切换不同的模型？**  
A: 在"模型设置"中保存多套"预设"，一键切换即可。

**Q: 如何降低费用？**  
A: 先用测试模式（只处理前 2-3 段）验证 Prompt 效果，满意后再处理全文；同时可以适当增大 `chunk_size` 减少 API 调用次数。

---

## 📜 开源许可证

本项目基于 [MIT License](LICENSE) 开源。你可以自由使用、修改和分发，保留版权声明即可。欢迎提交 Issue 和 Pull Request！
