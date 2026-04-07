"""
AI Document Proofreading System - Streamlit Web UI
"""

import streamlit as st
import io
import os
from typing import Dict, Any
import tempfile
import time

from docx_parser import DocxParser
from llm_providers import get_provider
from proofreader import ProofreadingEngine
from revision_writer import RevisionWriter
from prompt_templates import get_system_prompt, get_user_prompt, parse_llm_response
from utils import load_config, save_config, get_default_config, safe_filename, get_prompts_config, reset_prompts_config


# Page configuration
st.set_page_config(
    page_title="AI 文档智能审校系统",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load configuration
@st.cache_resource(ttl=60)
def get_config() -> Dict[str, Any]:
    """Get configuration (cached)"""
    base_config = load_config()
    default_config = get_default_config()
    
    merged_config = {**default_config, **base_config}
    
    custom_prompts = get_prompts_config("prompts.yaml")
    if custom_prompts.get("system") or custom_prompts.get("detail_level"):
        merged_config["prompt"] = custom_prompts
    
    return merged_config

# Initialize session state
if 'config' not in st.session_state:
    st.session_state.config = get_config()
else:
    loaded_config = load_config()
    default_config = get_default_config()
    
    merged_config = {**default_config, **loaded_config}
    
    custom_prompts = get_prompts_config("prompts.yaml")
    if custom_prompts.get("system") or custom_prompts.get("detail_level"):
        merged_config["prompt"] = custom_prompts
    
    st.session_state.config = {**merged_config, **st.session_state.config}

if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

if 'proofreading_results' not in st.session_state:
    st.session_state.proofreading_results = None

if 'stats' not in st.session_state:
    st.session_state.stats = None

if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False


def render_sidebar():
    """Render sidebar configuration"""
    st.sidebar.title("⚙️ 系统设置")

    # Disable entire configuration if processing
    is_busy = st.session_state.is_processing

    with st.sidebar.expander("📝 模型预设管理", expanded=False):
        presets = st.session_state.config.get("llm_presets", [])
        preset_names = [p["name"] for p in presets]
        
        selected_preset_name = st.selectbox("选择预设", ["-- 请选择 --"] + preset_names, disabled=is_busy)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("应用预设", use_container_width=True, disabled=is_busy or selected_preset_name == "-- 请选择 --"):
                preset = next(p for p in presets if p["name"] == selected_preset_name)
                st.session_state.config["llm"].update(preset["config"])
                # Also save immediately so it persists across sessions
                save_config(st.session_state.config)
                st.rerun()
        with col2:
            if st.button("删除预设", use_container_width=True, disabled=is_busy or selected_preset_name == "-- 请选择 --"):
                st.session_state.config["llm_presets"] = [p for p in presets if p["name"] != selected_preset_name]
                save_config(st.session_state.config)
                st.rerun()
        
        st.divider()
        new_preset_name = st.text_input("新预设名称", placeholder="例如: 我的 DeepSeek", disabled=is_busy)
        if st.button("保存当前配置为预设", use_container_width=True, disabled=is_busy):
            if new_preset_name:
                # Get current values from config (they are updated by widgets)
                if any(p["name"] == new_preset_name for p in presets):
                    st.error("预设名称已存在")
                else:
                    new_preset = {
                        "name": new_preset_name,
                        "config": st.session_state.config["llm"].copy()
                    }
                    if "llm_presets" not in st.session_state.config:
                        st.session_state.config["llm_presets"] = []
                    st.session_state.config["llm_presets"].append(new_preset)
                    save_config(st.session_state.config)
                    st.success(f"预设 '{new_preset_name}' 已保存")
                    st.rerun()
            else:
                st.error("请输入预设名称")

    with st.sidebar.expander("LLM 配置", expanded=True):
        provider = st.selectbox(
            "LLM 提供商",
            ["openai", "anthropic", "deepseek", "qwen", "ollama", "glm", "openai-format"],
            index=["openai", "anthropic", "deepseek", "qwen", "ollama", "glm", "openai-format"].index(
                st.session_state.config.get("llm", {}).get("provider", "openai")
            ),
            disabled=is_busy
        )

        if provider == "openai":
            model = st.text_input("模型名称", value=st.session_state.config.get("llm", {}).get("model", "gpt-4o"), key="openai_model", disabled=is_busy)
        elif provider == "anthropic":
            model = st.text_input("模型名称", value=st.session_state.config.get("llm", {}).get("model", "claude-3-haiku-20240307"), key="anthropic_model", disabled=is_busy)
        elif provider == "deepseek":
            model = st.text_input("模型名称", value=st.session_state.config.get("llm", {}).get("model", "deepseek-chat"), key="deepseek_model", disabled=is_busy)
        elif provider == "qwen":
            model = st.text_input("模型名称", value=st.session_state.config.get("llm", {}).get("model", "qwen-turbo"), key="qwen_model", disabled=is_busy)
        elif provider == "glm":
            model = st.text_input("模型名称", value=st.session_state.config.get("llm", {}).get("model", "glm-4"), key="glm_model", disabled=is_busy)
        elif provider == "openai-format":
            model = st.text_input("模型名称", value=st.session_state.config.get("llm", {}).get("model", ""), key="openai-format_model", disabled=is_busy)
        else:
            model = st.text_input("模型名称", value=st.session_state.config.get("llm", {}).get("model", "llama2"), key="ollama_model", disabled=is_busy)

        api_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.config.get("llm", {}).get("api_key", ""),
            help="对于 Ollama，此字段可留空",
            disabled=is_busy
        )

        base_url = st.text_input(
            "API Base URL (可选)",
            value=st.session_state.config.get("llm", {}).get("base_url", ""),
            help="自定义 API 端点，通常不需要填写",
            disabled=is_busy
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.config.get("llm", {}).get("temperature", 0.3),
            step=0.1,
            help="较低的值使输出更确定性，较高的值更有创造性",
            disabled=is_busy
        )

        timeout = st.slider(
            "超时时间 (秒)",
            min_value=30.0,
            max_value=600.0,
            value=st.session_state.config.get("llm", {}).get("timeout", 300.0),
            step=30.0,
            help="LLM 请求超时时间（秒），全文模式建议设置更大值",
            disabled=is_busy
        )

        st.session_state.config["llm"]["provider"] = provider
        st.session_state.config["llm"]["model"] = model
        st.session_state.config["llm"]["api_key"] = api_key
        st.session_state.config["llm"]["base_url"] = base_url
        st.session_state.config["llm"]["temperature"] = temperature
        st.session_state.config["llm"]["timeout"] = timeout

        st.divider()
        if st.button("⚡ 测试连接", use_container_width=True, disabled=is_busy):
            with st.spinner("正在测试连接..."):
                try:
                    p = get_provider(provider, st.session_state.config["llm"])
                    # Simple connectivity test
                    response = p.chat([{"role": "user", "content": "hi"}], temperature=0.1)
                    content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content:
                        st.success(f"✅ 连接成功！模型响应: {content[:50]}...")
                    else:
                        st.error("❌ 连接失败: 模型未返回有效内容")
                except Exception as e:
                    st.error(f"❌ 连接失败: {str(e)}")

    with st.sidebar.expander("审校设置", expanded=False):
        chunk_mode = st.selectbox(
            "分块模式",
            ["paragraph", "full_document"],
            index=0 if st.session_state.config.get("proofreading", {}).get("chunk_mode") == "paragraph" else 1,
            format_func=lambda x: {"paragraph": "逐段落", "full_document": "全文模式"}[x],
            help="逐段落: 每个段落单独处理\n全文模式: 一次性处理全文",
            disabled=is_busy
        )

        mode = st.radio(
            "审校模式",
            ["comments", "track_changes"],
            index=0 if st.session_state.config.get("proofreading", {}).get("mode") == "comments" else 1,
            format_func=lambda x: "批注模式" if x == "comments" else "修订模式",
            help="批注模式: 在原文中添加批注\n修订模式: 直接修改并显示差异",
            disabled=is_busy
        )

        if chunk_mode == "full_document":
            batch_size = 1
        elif chunk_mode == "paragraph":
            batch_size = st.number_input(
                "并发请求数",
                min_value=1,
                max_value=10,
                value=st.session_state.config.get("proofreading", {}).get("batch_size", 5),
                step=1,
                help="同时发送的请求数量",
                disabled=is_busy
            )

        detail_level = st.selectbox(
            "详细程度",
            ["minimal", "standard", "detailed"],
            index=1,
            format_func=lambda x: {"minimal": "快速", "standard": "标准", "detailed": "详细"}[x],
            help="快速: 更快但质量可能降低\n详细: 更慢但质量更高",
            disabled=is_busy
        )
        
        presets = st.session_state.config.get("llm_presets", [])
        preset_names = ["无 (不使用)"] + [p["name"] for p in presets]
        current_fallback = st.session_state.config.get("proofreading", {}).get("fallback_preset", "无 (不使用)")
        try:
            fb_index = preset_names.index(current_fallback)
        except ValueError:
            fb_index = 0
            
        fallback_preset = st.selectbox(
            "JSON解析失败备选模型",
            preset_names,
            index=fb_index,
            help="当主模型解析格式崩溃时，自动切换到此预设模型重试（建议选用逻辑更强的模型如 GPT-4o 或 Claude-3.5）",
            disabled=is_busy
        )

        st.session_state.config["proofreading"]["chunk_mode"] = chunk_mode
        st.session_state.config["proofreading"]["mode"] = mode
        st.session_state.config["proofreading"]["batch_size"] = batch_size
        st.session_state.config["prompt"]["detail_level"] = detail_level
        st.session_state.config["proofreading"]["fallback_preset"] = fallback_preset

    with st.sidebar.expander("👤 个性化设定", expanded=False):
        ai_editor_name = st.text_input(
            "AI 编辑名称",
            value=st.session_state.config.get("proofreading", {}).get("ai_editor_name", "AI Editor"),
            help="批注或修订中显示的作者名称",
            disabled=is_busy
        )
        
        add_header = st.checkbox(
            "为文档更新页眉",
            value=st.session_state.config.get("proofreading", {}).get("add_header", False),
            help="格式为: [编辑名] - [模型简称]",
            disabled=is_busy
        )
        
        st.session_state.config["proofreading"]["ai_editor_name"] = ai_editor_name
        st.session_state.config["proofreading"]["add_header"] = add_header

    with st.sidebar.expander("🔤 字体设置", expanded=False):
        cn_fonts = ["宋体", "微软雅黑", "黑体", "楷体", "仿宋"]
        en_fonts = ["Times New Roman", "Arial", "Calibri", "Courier New", "Verdana"]
        
        cn_font = st.selectbox(
            "中文字体",
            cn_fonts,
            index=cn_fonts.index(st.session_state.config["proofreading"].get("cn_font", "宋体")) if st.session_state.config["proofreading"].get("cn_font") in cn_fonts else 0,
            disabled=is_busy
        )
        
        en_font = st.selectbox(
            "英文字体",
            en_fonts,
            index=en_fonts.index(st.session_state.config["proofreading"].get("en_font", "Times New Roman")) if st.session_state.config["proofreading"].get("en_font") in en_fonts else 0,
            disabled=is_busy
        )
        apply_font_global = st.checkbox(
            "校对全文格式 (应用上述字体)",
            value=st.session_state.config["proofreading"].get("apply_font_global", True),
            help="选中后，处理后的文档将统一应用所选的中英文字体",
            disabled=is_busy
        )
        
        reference_formatting = st.checkbox(
            "📚 参考文献 GB/T 7714 格式化",
            value=st.session_state.config["proofreading"].get("reference_formatting", False),
            help="启用后会对文档末尾检测到的参考文献单独使用格式化提示词",
            disabled=is_busy
        )
        
        st.session_state.config["proofreading"]["cn_font"] = cn_font
        st.session_state.config["proofreading"]["en_font"] = en_font
        st.session_state.config["proofreading"]["apply_font_global"] = apply_font_global
        st.session_state.config["proofreading"]["reference_formatting"] = reference_formatting

    with st.sidebar.expander("测试模式", expanded=False):
        test_mode = st.checkbox(
            "启用测试模式",
            value=st.session_state.config.get("test_mode", {}).get("enabled", False),
            help="仅处理前几个段落用于测试 prompt"
        )

        test_chunks = st.number_input(
            "测试段落数",
            min_value=1,
            max_value=1000,
            value=st.session_state.config.get("test_mode", {}).get("chunks", 2),
            disabled=not test_mode
        )

        st.session_state.config["test_mode"]["enabled"] = test_mode
        st.session_state.config["test_mode"]["chunks"] = test_chunks

    if st.sidebar.button("💾 保存配置", disabled=is_busy):
        try:
            save_config(st.session_state.config)
            st.sidebar.success("配置已保存！")
            st.sidebar.info("提示：如果配置文件格式被破坏，请检查是否安装了 ruamel.yaml")
        except Exception as e:
            st.sidebar.error(f"保存配置失败: {str(e)}")

    st.sidebar.divider()
    if st.sidebar.button("🔄 重置界面", help="如果界面状态异常或想终止任务，请点击此按钮。注意：正在运行的任务将被中断。"):
        st.session_state.is_processing = False
        st.session_state.batch_results = []
        st.rerun()


def render_file_upload():
    """Render file upload section"""
    st.header("📤 上传文档")

    uploaded_files = st.file_uploader(
        "请选择 .docx 文件 (支持多选，最多 20 个)",
        type=['docx'],
        accept_multiple_files=True,
        help="支持 Microsoft Word 文档格式"
    )

    if uploaded_files:
        if len(uploaded_files) > 20:
            st.warning("⚠️ 一次最多处理 20 个文档，超出部分将被忽略。")
            uploaded_files = uploaded_files[:20]
            
        st.session_state.uploaded_files = uploaded_files
        
        st.info(f"📁 已上传 {len(uploaded_files)} 个文档")

        # Pre-parse and default-select
        if "file_stats" not in st.session_state:
            st.session_state.file_stats = {}
        if "preview_page" not in st.session_state:
            st.session_state.preview_page = 1
        if "selected_paragraphs" not in st.session_state:
            st.session_state.selected_paragraphs = {}
        if "current_preview_file" not in st.session_state:
            st.session_state.current_preview_file = uploaded_files[0].name

        # Ensure current_preview_file is still in uploaded_files
        file_names = [f.name for f in uploaded_files]
        if st.session_state.current_preview_file not in file_names:
            st.session_state.current_preview_file = file_names[0]

        for file in uploaded_files:
            fname = file.name
            if fname not in st.session_state.file_stats:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                    file.seek(0)
                    tmp.write(file.read())
                    tmp_path = tmp.name
                
                try:
                    parser = DocxParser(tmp_path)
                    stats = parser.get_document_stats()
                    
                    safe_paras = []
                    for p in parser.paragraphs_data:
                        safe_paras.append((p, False))
                    
                    st.session_state.file_stats[fname] = {
                        "stats": stats,
                        "safe_paras": safe_paras
                    }
                    
                    # Default checking ALL paras
                    if fname not in st.session_state.selected_paragraphs:
                        st.session_state.selected_paragraphs[fname] = set([p["index"] for p, _ in safe_paras])
                        
                except Exception as e:
                    st.error(f"预解析文件 {fname} 失败: {str(e)}")
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

        # Preview and selection for uploaded files
        st.subheader("📝 文档预览与精准修剪")
        st.caption("左侧点击文件以预览，右侧勾选需要审校的段落。系统默认全选所有段落。")

        left_col, right_col = st.columns([1, 2.5])
        
        with left_col:
            st.markdown("#### 📂 文档列表")
            st.markdown("<div style='max-height: 500px; overflow-y: auto;'>", unsafe_allow_html=True)
            for file in uploaded_files:
                fname = file.name
                if fname not in st.session_state.file_stats:
                    continue
                stats_cache = st.session_state.file_stats[fname]
                total_paras = len(stats_cache["safe_paras"])
                selected_count = len(st.session_state.selected_paragraphs.get(fname, set()))
                
                btn_label = f"{fname}\n({selected_count}/{total_paras} 段落)"
                is_active = (st.session_state.current_preview_file == fname)
                
                if st.button(btn_label, use_container_width=True, type="primary" if is_active else "secondary"):
                    st.session_state.current_preview_file = fname
                    st.session_state.preview_page = 1
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        with right_col:
            selected_preview_file = st.session_state.current_preview_file
            if selected_preview_file in st.session_state.file_stats:
                active_cache = st.session_state.file_stats[selected_preview_file]
                stats = active_cache["stats"]
                safe_paras = active_cache["safe_paras"]

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("段落数", stats["paragraphs"])
                with col2:
                    st.metric("字符数", stats["characters"])
                with col3:
                    st.metric("词数", stats["words"])
                with col4:
                    st.metric("估计 Token 数", stats["estimated_tokens"])

                if stats.get("image_paragraphs", 0) > 0:
                    st.info(f"🖼️ 检测到 {stats['image_paragraphs']} 个包含图片的段落，将在审校时自动跳过")

                total_paras = len(safe_paras)
                paras_per_page = 5
                total_pages = max(1, (total_paras + paras_per_page - 1) // paras_per_page) if total_paras > 0 else 1
                
                if total_paras > 0:
                    with st.expander(f"浏览与选择段落 - {selected_preview_file}", expanded=True):
                        # Pagination Controls
                        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
                        with col1:
                            if st.button("⏮ 首页", disabled=st.session_state.preview_page == 1):
                                st.session_state.preview_page = 1
                                st.rerun()
                        with col2:
                            if st.button("◀ 上页", disabled=st.session_state.preview_page == 1):
                                st.session_state.preview_page -= 1
                                st.rerun()
                        with col3:
                            st.markdown(f"<div style='text-align: center; padding-top: 5px;'>第 <b>{st.session_state.preview_page}</b> / {total_pages} 页 (共 {total_paras} 段)</div>", unsafe_allow_html=True)
                        with col4:
                            if st.button("下页 ▶", disabled=st.session_state.preview_page == total_pages):
                                st.session_state.preview_page += 1
                                st.rerun()
                        with col5:
                            if st.button("尾页 ⏭", disabled=st.session_state.preview_page == total_pages):
                                st.session_state.preview_page = total_pages
                                st.rerun()
                        
                        # Bulk selection actions for current page and entire document
                        start_idx = (st.session_state.preview_page - 1) * paras_per_page
                        end_idx = min(start_idx + paras_per_page, total_paras)
                        current_page_paras = safe_paras[start_idx:end_idx]
                        
                        b1, b2, b3, b4 = st.columns([1, 1, 1, 1.5])
                        with b1:
                            if st.button("本页全选", use_container_width=True, key=f"select_page_{selected_preview_file}"):
                                for p, disabled in current_page_paras:
                                    if not disabled: 
                                        st.session_state.selected_paragraphs[selected_preview_file].add(p["index"])
                                        st.session_state[f"cb_{selected_preview_file}_{p['index']}"] = True
                                st.rerun()
                        with b2:
                            if st.button("全选全部段落", use_container_width=True, type="secondary", key=f"select_all_{selected_preview_file}"):
                                for p, disabled in safe_paras:
                                    if not disabled: 
                                        st.session_state.selected_paragraphs[selected_preview_file].add(p["index"])
                                        st.session_state[f"cb_{selected_preview_file}_{p['index']}"] = True
                                st.rerun()
                        with b3:
                            if st.button("清空所有选取", use_container_width=True, key=f"clear_all_{selected_preview_file}"):
                                st.session_state.selected_paragraphs[selected_preview_file].clear()
                                for p, _ in safe_paras:
                                    st.session_state[f"cb_{selected_preview_file}_{p['index']}"] = False
                                st.rerun()
                        with b4:
                            selected_count = len(st.session_state.selected_paragraphs.get(selected_preview_file, set()))
                            if selected_count > 0:
                                st.info(f"✨ 已选择 {selected_count} 个段落")
        
                        st.divider()
                        
                        # Render Paragraphs
                        for i, (para, is_disabled) in enumerate(current_page_paras, start_idx + 1):
                            # Checkbox
                            para_idx = para["index"]
                            is_selected = para_idx in st.session_state.selected_paragraphs.get(selected_preview_file, set())
                            cols = st.columns([0.1, 0.9])
                            
                            with cols[0]:
                                cb_key = f"cb_{selected_preview_file}_{para_idx}"
                                if cb_key not in st.session_state:
                                    st.session_state[cb_key] = is_selected
        
                                def on_change(idx=para_idx, k=cb_key, file=selected_preview_file):
                                    if st.session_state[k]:
                                        st.session_state.selected_paragraphs[file].add(idx)
                                    else:
                                        st.session_state.selected_paragraphs[file].discard(idx)
                                        
                                st.checkbox("", disabled=is_disabled, 
                                            key=cb_key, on_change=on_change, kwargs={"idx": para_idx, "k": cb_key, "file": selected_preview_file})
                            
                            with cols[1]:
                                reason = ""
                                badges = []
                                if para.get("has_image"): badges.append("图片")
                                if para.get("contains_drawing"): badges.append("绘图")
                                if para.get("is_layout"): badges.append("排版")
                                if para.get("is_reference"): badges.append("参考文献")
                                
                                if badges:
                                    reason += f" *(标签: **{','.join(badges)}**)*"
                                    
                                fallback_msgs = []
                                if para.get("has_image") or para.get("contains_drawing"):
                                    fallback_msgs.append("视觉")
                                if "[[FORMULA_" in para.get("text", ""):
                                    fallback_msgs.append("公式")
                                    
                                if fallback_msgs:
                                    reason += f" *(安全回退：含{'+'.join(fallback_msgs)}结构，以批注形式悬挂建议)*"
                                
                                st.markdown(f"**段落 {i}** {reason}")
                                st.text(para["text"][:300] + ("..." if len(para["text"]) > 300 else ""))
                            st.divider()


def render_proofreading():
    """Render proofreading section"""
    st.header("🤖 AI 审校")

    if not st.session_state.get('uploaded_files'):
        st.warning("请先上传文档")
        return

    llm_config = st.session_state.config.get("llm", {})
    if not llm_config.get("api_key") and llm_config.get("provider") != "ollama":
        st.warning("请先在设置中配置 API Key")
        return

    start_button = st.button("🚀 开始批量审校", type="primary", disabled=st.session_state.is_processing)

    if start_button:
        st.session_state.is_processing = True
        st.session_state.batch_results = []
        results_container = []
        start_time = time.time()
        
        main_progress = st.progress(0)
        status_text = st.empty()
        time_text = st.empty()
        sub_progress_label = st.empty()
        sub_progress = st.progress(0)
        
        for file_idx, uploaded_file in enumerate(st.session_state.uploaded_files):
            tmp_path = None
            try:
                status_text.text(f"正在处理第 {file_idx+1}/{len(st.session_state.uploaded_files)} 个文件: {uploaded_file.name}...")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                    uploaded_file.seek(0)
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                parser = DocxParser(tmp_path)
                
                test_mode = st.session_state.config.get("test_mode", {}).get("enabled", False)
                test_chunks = st.session_state.config.get("test_mode", {}).get("chunks", 2)
                chunk_mode = st.session_state.config.get("proofreading", {}).get("chunk_mode", "paragraph")

                if test_mode:
                    chunks = parser.get_chunk_for_testing(test_chunks)
                elif chunk_mode == "paragraph":
                    chunks = parser.chunk_by_paragraph()
                elif chunk_mode == "full_document":
                    chunks = parser.chunk_full_document()
                elif chunk_mode == "chunk_text":
                    chunks = parser.chunk_text(
                        chunk_size=st.session_state.config.get("proofreading", {}).get("chunk_size", 500),
                        overlap=st.session_state.config.get("proofreading", {}).get("chunk_overlap", 50)
                    )
                else:
                    st.error(f"未知的分块模式: {chunk_mode}")
                    continue

                # --- Selective Revision Filtering ---
                # If user selected specific paragraphs for THIS file, filter the generated chunks
                selected_dict = st.session_state.get("selected_paragraphs", {})
                selected = selected_dict.get(uploaded_file.name, set())

                # Full document mode does not support paragraph-level filtering.
                if chunk_mode == "full_document" and uploaded_file.name in selected_dict:
                    total_paragraphs = len(parser.paragraphs_data)
                    if len(selected) != total_paragraphs:
                        st.warning(f"⚠️ 文件 [{uploaded_file.name}] 当前为全文模式，不支持段落筛选，已按整篇文档处理。")
                
                # If the user specifically visited the preview tab and selected 0 paragraphs, selected will be an empty set.
                # However, if they never selected the file in the dropdown, the key wouldn't exist and it would default to set().
                # To distinguish: if the key exists AND the set is empty -> user explicitly cleared selections.
                # If the key does not exist -> user didn't care, default to full processing.
                if chunk_mode != "full_document" and uploaded_file.name in selected_dict and len(selected) == 0:
                    st.warning(f"⚠️ 文件 [{uploaded_file.name}] 未选中任何有效段落，本次对该文件不进行大模型修订，将保持原样返回。")
                    chunks = []
                elif chunk_mode != "full_document" and selected:
                    filtered_chunks = []
                    for chunk in chunks:
                        # Check if any index in paragraph_indices overlaps with selected set
                        if any(idx in selected for idx in chunk.get("paragraph_indices", [])):
                            filtered_chunks.append(chunk)
                    
                    if len(filtered_chunks) < len(chunks):
                        st.info(f"🎯 文件 [{uploaded_file.name}] 已开启精准修订：共 {len(chunks)} 个分块，仅处理选中的 {len(filtered_chunks)} 个分块，其余将保持原样。")
                    chunks = filtered_chunks

                if not chunks:
                    # No chunks to process (either explicitly cleared or all filtered out)
                    # We must NOT `continue` here, because we still need to package this unaltered file into the results!
                    output_bytes = io.BytesIO()
                    # Open original again to ensure it's pristine, then save immediately
                    parser.doc.save(output_bytes)
                    output_bytes.seek(0)
                    
                    results_container.append({
                        "name": uploaded_file.name,
                        "processed_name": f"revised_{safe_filename(uploaded_file.name)}",
                        "data": output_bytes.getvalue(),
                        "stats": {"total_chunks": 0, "successful_edits": 0, "failed_edits": 0, "total_tokens": 0},
                        "results": []
                    })
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    sub_progress.empty()
                    main_progress.progress((file_idx + 1) / len(st.session_state.uploaded_files))
                    continue # Safe to continue strictly after packaging

                provider = get_provider(llm_config["provider"], llm_config)
                engine = ProofreadingEngine(
                    provider,
                    detail_level=st.session_state.config["prompt"]["detail_level"],
                    custom_prompts=st.session_state.config.get("custom_prompts"),
                    enable_reference_formatting=st.session_state.config["proofreading"].get("reference_formatting", False)
                )

                def progress_callback(progress, current, total):
                    sub_progress.progress(progress)
                    sub_progress_label.text(f"  └─ 当前文件进度: {current}/{total} 段落 ({int(progress*100)}%)")
                    elapsed = time.time() - start_time
                    time_text.markdown(f"⏱️ **累计用时**: {int(elapsed // 60)}分 {int(elapsed % 60)}秒")

                results, stats = engine.proofread_document(
                    chunks,
                    batch_size=st.session_state.config["proofreading"]["batch_size"],
                    temperature=llm_config["temperature"],
                    progress_callback=progress_callback
                )
                
                # Apply results and get processed Document
                writer = RevisionWriter(tmp_path)
                ai_name = st.session_state.config["proofreading"]["ai_editor_name"]
                
                mode = st.session_state.config["proofreading"]["mode"]
                if mode == "comments":
                    processed_doc = writer.write_comments(results, author=ai_name)
                else:
                    processed_doc = writer.write_track_changes(results, author=ai_name)
                    
                # Add header if requested AFTER getting the final processed_doc
                if st.session_state.config["proofreading"].get("add_header"):
                    writer.add_header(llm_config["model"], ai_name, target_doc=processed_doc)
                
                # Apply fonts if requested
                if st.session_state.config["proofreading"].get("apply_font_global"):
                    writer.apply_fonts(
                        cn_font=st.session_state.config["proofreading"].get("cn_font", "宋体"),
                        en_font=st.session_state.config["proofreading"].get("en_font", "Times New Roman"),
                        target_doc=processed_doc
                    )
                
                # Save to bytes
                output_bytes = io.BytesIO()
                processed_doc.save(output_bytes)
                output_bytes.seek(0)
                
                results_container.append({
                    "name": uploaded_file.name,
                    "processed_name": f"revised_{safe_filename(uploaded_file.name)}",
                    "data": output_bytes.getvalue(),
                    "stats": stats,
                    "results": results
                })
                
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                sub_progress.empty()
                
            except Exception as e:
                st.error(f"处理文件 {uploaded_file.name} 时出错: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
            main_progress.progress((file_idx + 1) / len(st.session_state.uploaded_files))

        st.session_state.is_processing = False
        status_text.text("✅ 所有文件处理完成！")
        sub_progress_label.empty()
        sub_progress.empty()
        st.session_state.batch_results = results_container
        st.rerun()

def render_download():
    """Render download section"""
    st.header("📥 下载结果")

    if not st.session_state.get('batch_results'):
        st.warning("请先完成审校")
        return

    results = st.session_state.batch_results
    
    if len(results) > 1:
        st.subheader("📦 批量下载")
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for r in results:
                zip_file.writestr(r["processed_name"], r["data"])
        
        st.info("💡 已为您生成压缩包，包含所有已处理的文档。")
        st.download_button(
            label="📥 一键压缩并下载所有结果 (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"batch_revised_{int(time.time())}.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )
        st.divider()
        st.subheader("📄 单个文件下载")

    for idx, r in enumerate(results):
        with st.expander(f"📄 {r['name']} - 查看详情"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.download_button(
                    label=f"📥 下载修订版: {r['processed_name']}",
                    data=r['data'],
                    file_name=r['processed_name'],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"dl_{idx}"
                )
            with col2:
                st.write(f"修订数: {r['stats']['successful_edits']}")
            
            # Show top 3 comments
            for i, res in enumerate(r["results"][:3], 1):
                if res["success"] and res["revised_text"] != res["original_text"]:
                    st.caption(f"建议 #{i}: {res['comment']}")



def main():
    st.title("📝 AI 文档智能审校系统")
    st.markdown("基于大语言模型的智能文档校对工具")

    render_sidebar()
    st.divider()
    render_file_upload()
    st.divider()
    render_proofreading()
    st.divider()
    render_download()

    st.divider()
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>AI 文档智能审校系统 | 支持 OpenAI, Anthropic, DeepSeek, Qwen, Ollama</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
