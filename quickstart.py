#!/usr/bin/env python3
"""
Quick start script for AI Document Proofreading System
"""

import os
import sys


def check_dependencies():
    """Check if required dependencies are installed"""
    print("检查依赖...")

    required_packages = [
        "streamlit",
        "docx",
        "pyyaml",
        "httpx"
    ]

    optional_packages = [
        "docx_revisions",
        "docx_editor",
        "tiktoken",
        "ruamel.yaml"
    ]

    missing_required = []
    missing_optional = []

    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (未安装)")
            missing_required.append(package)

    for package in optional_packages:
        try:
            __import__(package)
            if package == "docx_editor":
                print(f"  ✓ docx-editor (可选，推荐)")
            elif package == "docx_revisions":
                print(f"  ✓ docx-revisions (可选)")
            elif package == "ruamel.yaml":
                print(f"  ✓ ruamel.yaml (可选，推荐，用于保留配置注释)")
            else:
                print(f"  ✓ {package} (可选)")
        except ImportError:
            if package == "docx_editor":
                print(f"  ✗ docx-editor (可选，未安装)")
            elif package == "docx_revisions":
                print(f"  ✗ docx-revisions (可选，未安装)")
            elif package == "ruamel.yaml":
                print(f"  ✗ ruamel.yaml (可选，未安装)")
            else:
                print(f"  ✗ {package} (可选，未安装)")
            missing_optional.append(package)

    return missing_required, missing_optional


def create_config():
    """Create config file if it doesn't exist"""
    if not os.path.exists("config.yaml"):
        print("\n创建配置文件 config.yaml...")
        from utils import get_default_config, save_config
        save_config(get_default_config())
        print("  ✓ 配置文件已创建")
        print("  ⚠️  请编辑 config.yaml 设置您的 API Key")
    else:
        print("\n配置文件 config.yaml 已存在")


def print_usage():
    """Print usage instructions"""
    print("\n" + "=" * 60)
    print("使用方法:")
    print("=" * 60)
    print("\n1. 编辑 config.yaml 设置您的 LLM API Key")
    print("\n2. 启动应用:")
    print("   streamlit run app.py")
    print("\n3. 在浏览器中打开 http://localhost:8501")
    print("\n4. 上传 .docx 文件并开始审校")
    print("\n" + "=" * 60)
    print("\n支持的模式:")
    print("  - 批注模式 (comments): 在文档中添加批注")
    print("  - 修订模式 (track_changes): 显示 Track Changes (需要 docx-revisions)")
    print("\n支持的 LLM 提供商:")
    print("  - OpenAI (GPT-4, GPT-3.5)")
    print("  - Anthropic (Claude)")
    print("  - DeepSeek")
    print("  - 通义千问 (Qwen)")
    print("  - 智谱 AI (GLM)")
    print("  - Ollama (本地模型)")
    print("=" * 60)


def main():
    """Main function"""
    print("\n" + "=" * 60)
    print("AI 文档智能审校系统 - 快速启动")
    print("=" * 60 + "\n")

    missing_required, missing_optional = check_dependencies()

    if missing_required:
        print(f"\n错误: 缺少必需的依赖包: {', '.join(missing_required)}")
        print("\n请运行:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    if missing_optional:
        print(f"\n提示: 可选包未安装: {', '.join(missing_optional)}")
        print("功能限制:")
        if "docx_editor" in missing_optional and "docx_revisions" in missing_optional:
            print("  - Track Changes 模式将不可用")
            print("  - 推荐安装 docx-editor (更新的库): pip install docx-editor")
            print("  - 或安装 docx-revisions: pip install docx-revisions==0.1.3")
        elif "tiktoken" in missing_optional:
            print("  - Token 计数将使用近似值")
        elif "ruamel.yaml" in missing_optional:
            print("  - 保存配置时会丢失注释 (建议安装: pip install ruamel.yaml)")
        print("\n安装可选包:")
        print("  pip install ruamel.yaml docx-editor tiktoken")

    create_config()
    print_usage()


if __name__ == "__main__":
    main()
