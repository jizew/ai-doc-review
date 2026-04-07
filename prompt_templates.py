"""
Prompt Templates for Document Proofreading
"""
import re
import json
import os

_PROMPTS_CACHE = None

def _load_prompts():
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is not None:
        return _PROMPTS_CACHE
    try:
        prompts_path = os.path.join(os.path.dirname(__file__), "prompts.json")
        with open(prompts_path, "r", encoding="utf-8") as f:
            _PROMPTS_CACHE = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load prompts.json: {e}")
        _PROMPTS_CACHE = {
            "system": "你是一位专业的中文编辑...",
            "user_prompts": {
                "standard": "请对以下文本进行校对：\n{text}",
                "detailed": "请仔细校对以下文本：\n{text}",
                "minimal": "校对：{text}"
            },
            "leak_detection": {
                "patterns": [],
                "notice_keywords": []
            }
        }
    return _PROMPTS_CACHE

def reload_prompts():
    """Force reload of the prompts.json file."""
    global _PROMPTS_CACHE
    _PROMPTS_CACHE = None
    _load_prompts()

def get_system_prompt() -> str:
    """Get system prompt for proofreading"""
    prompts = _load_prompts()
    return prompts.get("system", "")

def get_user_prompt(text: str, detail_level: str = "standard") -> str:
    """
    Get user prompt with specified detail level

    Args:
        text: The text to proofread
        detail_level: "minimal", "standard", or "detailed"
    """
    prompts = _load_prompts()
    user_prompts = prompts.get("user_prompts", {})
    template = user_prompts.get(detail_level, user_prompts.get("standard", ""))
    return template.format(text=text)

def get_reference_system_prompt() -> str:
    """Get system prompt for reference formatting"""
    prompts = _load_prompts()
    return prompts.get("reference_system", "你是一位专业的学术编辑，精通 GB/T 7714-2015《信息与文献 参考文献著录规则》。")

def get_reference_prompt(text: str) -> str:
    """Get user prompt for reference formatting"""
    prompts = _load_prompts()
    template = prompts.get("reference_prompt", "请将以下参考文献条目格式化为标准的 GB/T 7714-2015 格式：\n{text}")
    return template.format(text=text)

def _strip_notice_block(text: str, original_text: str = "") -> str:
    """Strip 注意: bullet block without regex backtracking."""
    prompts = _load_prompts()
    notice_keywords = prompts.get("leak_detection", {}).get("notice_keywords", [])
    
    # Pre-clean original text for robust comparison
    original_clean = re.sub(r'\s+', '', original_text) if original_text else ""
    
    lines = text.split('\n')
    result = []
    in_notice_block = False
    for line in lines:
        stripped = line.strip()
        # Detect start of notice block
        if stripped.startswith('注意') and (stripped.endswith('：') or stripped.endswith(':') or stripped == '注意：' or '注意：' in stripped):
            in_notice_block = True
            
            # If the "注意" line itself is in the original document, we should probably keep it, 
            # but we continue to check the bullets.
            if original_clean and re.sub(r'\s+', '', stripped) in original_clean:
                result.append(line)
            continue
            
        # If inside notice block, skip bullet lines with known keywords
        if in_notice_block:
            if stripped.startswith('-') or stripped.startswith('\u2013') or stripped.startswith('\u2014'):
                if any(kw in stripped for kw in notice_keywords):
                    # Check if this bullet is actually in the original text
                    if original_clean and re.sub(r'\s+', '', stripped) in original_clean:
                        result.append(line) # Keep it
                    else:
                        continue  # Strip this hallucinatory bullet
                else:
                    in_notice_block = False  # not a prompt bullet, exit block
            elif stripped == '':
                if not original_clean: # Only strip empty lines if we aren't preserving the original block
                    continue
            else:
                in_notice_block = False  # non-bullet, non-blank: exit block
        result.append(line)
    return '\n'.join(result)

def clean_prompt_leakage(text: str, original_text: str = "") -> str:
    """Remove leaked prompt template fragments from LLM output."""
    if not text:
        return text
        
    # Pre-clean original text for robust comparison
    original_clean = re.sub(r'\s+', '', original_text) if original_text else ""
    
    # First, handle the 注意: block with a safe line-by-line approach
    cleaned = _strip_notice_block(text, original_text)
    
    # Then apply regex patterns for the remaining fragments
    prompts = _load_prompts()
    patterns = prompts.get("leak_detection", {}).get("patterns", [])
    
    def replacer(match):
        matched_str = match.group(0)
        # If the matched string literally appears in the original text (ignoring whitespace), keep it
        if original_clean:
            matched_clean = re.sub(r'\s+', '', matched_str)
            if matched_clean and matched_clean in original_clean:
                return matched_str
        # Else remove it
        return ""
        
    for pattern in patterns:
        try:
            cleaned = re.sub(pattern, replacer, cleaned, flags=re.DOTALL | re.MULTILINE)
        except re.error:
            pass
            
    # Collapse multiple blank lines left over after removal
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def parse_llm_response(response: str, original_text: str = "") -> dict:
    """
    Parse LLM response to extract JSON with improved robustness

    Args:
        response: Raw response from LLM
        original_text: The original text chunk, used for source-aware prompt leakage prevention

    Returns:
        Parsed dictionary with original, revised, and comment
    """
    import json

    if not response:
        return {"original": "", "revised": "", "comment": "AI 未返回内容"}

    # 1. Clean markdown code blocks if present
    clean_content = response.strip()
    if clean_content.startswith("```"):
        clean_content = re.sub(r'^```(?:json)?\s*', '', clean_content)
        clean_content = re.sub(r'\s*```$', '', clean_content)
    
    clean_content = clean_content.strip()

    # 2. Try direct parsing
    result = None
    try:
        result = json.loads(clean_content)
    except json.JSONDecodeError:
        pass

    # 3. Try to find the first '{' and the last '}'
    if result is None:
        try:
            start_idx = clean_content.find('{')
            end_idx = clean_content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = clean_content[start_idx:end_idx+1]
                result = json.loads(json_str)
        except Exception:
            pass

    # 4. Final attempt: regex for specific fields
    # Use [^\"]* instead of .*? with DOTALL to avoid catastrophic backtracking
    if result is None:
        try:
            original = re.search(r'"original"\s*:\s*"([^"]*)"', clean_content)
            revised = re.search(r'"revised"\s*:\s*"([^"]*)"', clean_content)
            comment = re.search(r'"comment"\s*:\s*"([^"]*)"', clean_content)
            
            if original and revised:
                result = {
                    "original": original.group(1),
                    "revised": revised.group(1),
                    "comment": comment.group(1) if comment else ""
                }
        except Exception:
            pass

    # 5. Fallback: return structure indicating parsing failure
    if result is None:
        return {
            "original": "",
            "revised": "",
            "comment": f"解析失败。原始响应: {response[:100]}..."
        }

    # --- Strong Hallucination Overrule ---
    # Since we now have a robust retry max_parse_retries loop, we proactively REJECT 
    # blatant prompt leakages to force the LLM to retry properly, rather than risky stripping.
    if result.get("revised") and original_text:
        rev_text = result["revised"]
        
        leakage_signatures = [
            "校对重点：", "校对重点:", "保持原文的", "只做必要的修改", "如果文本没有问题", 
            "original和revised应相同", "返回JSON", "不要过度润色"
        ]
        
        for sig in leakage_signatures:
            if sig in rev_text and sig not in original_text:
                return {
                    "original": "",
                    "revised": "",
                    "comment": f"解析失败：检测到严重提示词幻觉泄露 ({sig})，触发重试截断。"
                }

    # --- Post-parse sanitization: attempt to clean minor leakages from revised text ---
    if result.get("revised"):
        result["revised"] = clean_prompt_leakage(result["revised"], original_text)
    
    return result
