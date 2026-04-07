# AI 文档智能审校系统

基于大语言模型的智能文档校对工具，支持多种 LLM 提供商和 Word 文档审校。

## 功能特性

- 🚀 **多 LLM 支持**: OpenAI、Anthropic、DeepSeek、通义千问 (Qwen)、Ollama
- 📝 **Word 文档处理**: 上传 .docx 文件进行智能审校
- 📊 **两种审校模式**:
  - 批注模式: 在原文中添加批注，保留原貌
  - 修订模式: 显示 Track Changes，直观展示修改
- 🧪 **测试模式**: 仅处理前几个段落用于测试 prompt
- ⚙️ **灵活配置**: 自定义 LLM 参数、分块大小、并发数等
- 📈 **实时进度**: 显示处理进度和统计信息

## 安装

```bash
# 克隆项目
git clone <repository-url>
cd doc_review

# 激活 conda 环境（如果使用默认环境 ai312）
conda activate ai312

# 安装依赖
pip install -r requirements.txt
```

### 推荐安装：ruamel.yaml

**强烈推荐安装 `ruamel.yaml`** 以保留配置文件的注释：

```bash
pip install ruamel.yaml
```

**重要修复**：
- 已修复配置保存时注释丢失的 bug
- 使用 `ruamel.yaml` 可以保留所有格式和注释
- 不安装 `ruamel.yaml` 时功能不受影响，但会丢失注释

### 可选: 安装 Track Changes 支持 (推荐 docx-editor)

**推荐使用 docx-editor (更新的库):**

```bash
pip install docx-editor
```

**或使用 docx-revisions:**

```bash
pip install docx-revisions==0.1.3
```

## 配置

### 方法 1: 通过 Web UI 配置

1. 运行应用
2. 在侧边栏配置 LLM 参数
3. 点击"保存配置"

### 方法 2: 手动编辑配置文件

编辑 `config.yaml`:

```yaml
llm:
  provider: openai  # openai, anthropic, deepseek, qwen, ollama
  model: gpt-4o
  api_key: "your-api-key"
  base_url: ""  # 可选: 自定义 API 端点
  temperature: 0.3

proofreading:
  mode: comments  # comments (批注) 或 track_changes (修订)
  chunk_size: 500  # 每次处理的字符数
  chunk_overlap: 50  # 分块重叠
  batch_size: 5  # 并发请求数
```

## 使用

### 启动应用

```bash
streamlit run app.py
```

应用将在 `http://localhost:8501` 启动。

### 工作流程

1. **配置 LLM**: 在侧边栏设置 LLM 提供商、模型、API Key 等
2. **上传文档**: 选择 .docx 文件上传
3. **查看文档信息**: 确认文档的段落数、字符数、Token 数等
4. **开始审校**: 点击"开始审校"按钮
5. **查看结果**: 查看审校统计和示例结果
6. **下载文档**: 下载带批注或修订的 Word 文档

### 测试模式

启用测试模式可以仅处理前几个段落，用于测试 prompt 是否合适:

1. 在侧边栏展开"测试模式"
2. 勾选"启用测试模式"
3. 设置测试段落数 (如 2-3)
4. 开始审校

## 项目结构

```
doc_review/
├── app.py                 # Streamlit 主应用
├── llm_providers.py       # LLM 提供商接口
├── docx_parser.py         # Docx 解析器
├── proofreader.py         # AI 审校引擎
├── revision_writer.py     # Word 修订写入器
├── prompt_templates.py    # Prompt 模板
├── utils.py             # 工具函数
├── config.yaml           # 配置文件
├── requirements.txt      # 依赖列表
└── README.md            # 本文件
```

## 支持的 LLM 提供商

### OpenAI
- Provider: `openai`
- 默认模型: `gpt-4o`
- 文档: https://platform.openai.com/docs
- API 格式: OpenAI 标准

### Anthropic (Claude)
- Provider: `anthropic`
- 默认模型: `claude-3-opus-20240229`
- 文档: https://docs.anthropic.com
- API 格式: 自有格式（非 OpenAI 兼容）

### DeepSeek
- Provider: `deepseek`
- 默认模型: `deepseek-chat`
- 文档: https://platform.deepseek.com/api-docs/
- API 格式: OpenAI 兼容

### 通义千问 (Qwen)
- Provider: `qwen`
- 默认模型: `qwen-turbo`
- 文档: https://help.aliyun.com/zh/dashscope/
- API 格式: OpenAI 兼容（compatible-mode）

### 智谱 AI (GLM)
- Provider: `glm`
- 默认模型: `glm-4`
- 文档: https://open.bigmodel.cn/dev/api
- API 格式: OpenAI 兼容

### Ollama (本地模型)
- Provider: `ollama`
- 默认模型: `llama2`
- 文档: https://ollama.com/docs/
- 不需要 API Key
- API 格式: 自有格式

## 配置说明

### LLM 参数

- **provider**: LLM 提供商名称（支持 openai, anthropic, deepseek, qwen, glm, ollama）
- **model**: 模型名称
- **api_key**: API 密钥 (Ollama 不需要)
- **base_url**: 自定义 API 端点 (可选)
  - 对于 OpenAI 兼容的 API（如 DeepSeek, Qwen, GLM），可以覆盖默认端点
  - 通常不需要填写
  - 详见下方"各提供商 Base URL 配置"
- **temperature**: 生成温度 (0.0-2.0)，越低越确定性

### 各提供商 Base URL 配置

| 提供商 | provider 值 | 默认 Base URL | 可否自定义 | 自定义场景 |
|---------|--------------|---------------|-----------|-----------|
| OpenAI | `openai` | `https://api.openai.com/v1` | ✅ 是 | 使用代理或其他端点 |
| Anthropic | `anthropic` | `https://api.anthropic.com` | ✅ 是 | 使用代理或其他端点 |
| DeepSeek | `deepseek` | `https://api.deepseek.com` | ✅ 是 | 使用自定义端点 |
| 通义千问 | `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | ✅ 是 | 使用自定义端点 |
| 智谱 AI | `glm` | `https://open.bigmodel.cn/api/paas/v4` | ✅ 是 | 使用自定义端点 |
| Ollama | `ollama` | `http://localhost:11434` | ✅ 是 | 使用远程 Ollama 服务 |

**重要提示**：
- OpenAI 兼容格式（OpenAI、DeepSeek、Qwen、GLM）使用相同的 API 路径和格式
- 如果提供商的 API 有 `/v1` 或 `/v4` 后缀，在 `base_url` 中已包含
- 对于使用 `/compatible-mode/v1` 兼容模式的 API，不需要担心路径问题

### 使用自定义 OpenAI 兼容格式的模型

如果您有其他 OpenAI 兼容格式的 API（未预设支持），可以通过 `base_url` 配置使用：

**要求**：
- API 路径为 `/chat/completions`
- Header 使用 `Authorization: Bearer <token>`
- 请求体格式符合 OpenAI 标准
- 响应格式包含 `choices[0].message.content`

**配置示例**：

```yaml
llm:
  provider: openai
  model: your-custom-model-name
  api_key: "your-api-key"
  base_url: "https://your-custom-api-endpoint"  # 或 "https://your-custom-api-endpoint/v1"
  temperature: 0.3
```

**注意事项**：
- 如果 API 端点已包含版本号（如 `/v1`），直接填写完整 URL
- 如果 API 端点不包含版本，建议手动添加（如 `/v1`）
- 各模型提供商的 API 格式差异较大，建议优先使用预设的提供商

### 审校参数

- **mode**: `comments` (批注) 或 `track_changes` (修订)
- **chunk_size**: 每次处理的字符数 (100-2000)
- **chunk_overlap**: 分块之间的重叠字符数 (0-200)
- **batch_size**: 并发请求数 (1-10)
- **detail_level**: Prompt 详细程度 (`minimal`, `standard`, `detailed`)

## 常见问题

### Q: Track Changes 模式不工作?
A: 需要安装 `docx-editor` 或 `docx-revisions` 库:

**推荐使用 docx-editor:**
```bash
pip install docx-editor
```

**或使用 docx-revisions:**
```bash
pip install docx-revisions==0.1.3
```

### Q: 保存配置后注释消失了?
A: 这是已知问题，已通过以下方式修复：
1. 安装 `ruamel.yaml` 包：`pip install ruamel.yaml`
2. 系统会自动检测并使用 `ruamel.yaml` 保留注释
3. 如果未安装，会回退到标准 yaml（会丢失注释）

### Q: 如何降低成本?
A:
1. 使用更小的模型 (如 gpt-3.5-turbo 而非 gpt-4)
2. 减小 `chunk_size`
3. 减小 `batch_size`
4. 使用测试模式先测试 prompt

### Q: 中文处理效果如何?
A: 本系统针对中文文档优化，支持中文错别字、语法、标点等检查。

### Q: 支持哪些 Word 格式?
A: 仅支持 `.docx` 格式 (Office 2007+)

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码风格

项目遵循 PEP 8 代码风格。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request!
