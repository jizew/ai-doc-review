#!/bin/bash
# AI 文档智能审校系统 - 启动脚本 (macOS / Linux)

set -e

echo ""
echo "============================================================"
echo "  AI 文档智能审校系统 - 启动程序"
echo "============================================================"
echo ""

# 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "[错误] 未检测到 Python3，请先安装 Python 3.9 或更高版本。"
    echo "  macOS: brew install python"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 创建或复用虚拟环境
if [ ! -f "venv/bin/activate" ]; then
    echo "[1/3] 首次运行：正在创建虚拟环境..."
    python3 -m venv venv
    echo "      虚拟环境创建成功。"
else
    echo "[1/3] 虚拟环境已存在，跳过创建。"
fi

# 激活虚拟环境
echo "[2/3] 正在激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "[3/3] 正在检查并安装依赖（首次运行可能需要几分钟）..."
pip install -r requirements.txt -q

# 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo ""
    echo "[提示] 未找到 config.yaml，正在从模板创建..."
    cp config.yaml.example config.yaml
    echo "      已创建 config.yaml，请用文本编辑器打开并填写您的 API Key。"
    echo "      填写完成后，再次运行本脚本启动应用。"
    echo ""
    exit 0
fi

# 启动
echo ""
echo "============================================================"
echo "  正在启动应用，浏览器将自动打开..."
echo "  如未自动打开，请手动访问: http://localhost:8501"
echo "  按 Ctrl+C 停止应用。"
echo "============================================================"
echo ""
streamlit run app.py --server.headless false
