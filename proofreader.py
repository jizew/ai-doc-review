"""
Proofreading Engine
Handles AI-powered document proofreading
"""

from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import random

from llm_providers import LLMProvider, get_provider
from prompt_templates import get_system_prompt, get_user_prompt, parse_llm_response, get_reference_prompt, get_reference_system_prompt
from utils import get_prompts_config, load_config


class ProofreadingEngine:
    """AI-powered proofreading engine"""

    def __init__(self, llm_provider: LLMProvider, detail_level: str = "standard", custom_prompts: Optional[Dict] = None, enable_reference_formatting: bool = False):
        """
        Initialize proofreading engine

        Args:
            llm_provider: LLM provider instance
            detail_level: "minimal", "standard", or "detailed"
            custom_prompts: Optional dictionary with system and user prompts
            enable_reference_formatting: Whether to apply GB/T 7714 formatting to reference paragraphs
        """
        self.provider = llm_provider
        self.detail_level = detail_level
        self.enable_reference_formatting = enable_reference_formatting
        self.custom_prompts = custom_prompts or get_prompts_config("prompts.yaml")
        # Use custom system prompt if provided, otherwise use default
        self.system_prompt = self.custom_prompts.get("system", "").strip() if self.custom_prompts.get("system") else get_system_prompt()
        
        # Load retry settings
        config = load_config()
        proof_config = config.get("proofreading", {})
        self.max_retries = proof_config.get("max_retries", 5)
        self.max_parse_retries = proof_config.get("max_parse_retries", 3)
        self.base_retry_delay = proof_config.get("base_retry_delay", 2.0)
        
        # Load fallback provider if configured
        self.fallback_preset_name = proof_config.get("fallback_preset", "无 (不使用)")
        self.fallback_provider = None
        if self.fallback_preset_name and self.fallback_preset_name != "无 (不使用)":
            presets = config.get("llm_presets", [])
            for p in presets:
                if p["name"] == self.fallback_preset_name:
                    from llm_providers import get_provider
                    self.fallback_provider = get_provider(p["config"].get("provider", "openai"), p["config"])
                    break

        self.stats = {
            "total_chunks": 0,
            "successful_edits": 0,
            "failed_edits": 0,
            "total_tokens": 0
        }

    def proofread_chunk(self, chunk: Dict, temperature: float = 0.3) -> Dict:
        """
        Proofread a single chunk of text

        Args:
            chunk: Dictionary containing text and paragraph indices
            temperature: LLM temperature

        Returns:
            Dictionary with original text, revised text, and edits
        """
        is_ref = chunk.get("is_reference", False) and self.enable_reference_formatting
        
        if is_ref:
            messages = [
                {"role": "system", "content": get_reference_system_prompt()},
                {"role": "user", "content": get_reference_prompt(chunk["text"])}
            ]
        else:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": get_user_prompt(chunk["text"], self.detail_level)}
            ]

        max_retries = getattr(self, "max_retries", 5)
        max_parse_retries = getattr(self, "max_parse_retries", 3)
        base_retry_delay = getattr(self, "base_retry_delay", 2.0)
        
        last_error = None
        parse_retry_count = 0
        current_provider = self.provider

        for attempt in range(max_retries):
            try:
                input_tokens = current_provider.count_tokens("\n".join([m["content"] for m in messages]))
                self.stats["total_tokens"] += input_tokens
    
                response = current_provider.chat(messages, temperature=temperature, json_mode=True)
    
                content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
                parsed = parse_llm_response(content, original_text=chunk["text"])

                # --- [新增] JSON 解析失败防御重试与备选模型切换 ---
                if isinstance(parsed.get("comment"), str) and parsed.get("comment", "").startswith("解析失败"):
                    if parse_retry_count < max_parse_retries and attempt < max_retries - 1:
                        parse_retry_count += 1
                        idx = chunk.get("paragraph_indices", ["未知"])[0] if chunk.get("paragraph_indices") else "未知"
                        
                        # Switch to fallback provider if available
                        provider_switch_msg = ""
                        if self.fallback_provider and current_provider != self.fallback_provider:
                            current_provider = self.fallback_provider
                            provider_switch_msg = f" ➡️ [切换至备选模型: {self.fallback_preset_name}]"
                            
                        print(f"⚠️ [段落 {idx}] JSON解析失败, 发起格式重试 {parse_retry_count}/{max_parse_retries} (计入全局尝试 {attempt+1}/{max_retries}){provider_switch_msg}")
                        time.sleep(1.0 + random.uniform(0, 0.5))
                        continue
                    else:
                        # --- [临界防御] 如果重试完全耗尽，强制将 revised 设置为原文，防止清空段落 ---
                        parsed["revised"] = chunk["text"]
                        parsed["original"] = chunk["text"]
                
                # Empty/invalid output is treated as parse failure and follows the same retry path.
                if not parsed.get("revised"):
                    if parse_retry_count < max_parse_retries and attempt < max_retries - 1:
                        parse_retry_count += 1
                        idx = chunk.get("paragraph_indices", ["未知"])[0] if chunk.get("paragraph_indices") else "未知"
                        provider_switch_msg = ""
                        if self.fallback_provider and current_provider != self.fallback_provider:
                            current_provider = self.fallback_provider
                            provider_switch_msg = f" ➡️ [切换至备选模型: {self.fallback_preset_name}]"
                        print(f"⚠️ [段落 {idx}] 模型返回空修订, 发起格式重试 {parse_retry_count}/{max_parse_retries} (计入全局尝试 {attempt+1}/{max_retries}){provider_switch_msg}")
                        time.sleep(1.0 + random.uniform(0, 0.5))
                        continue
                    parsed["revised"] = chunk["text"]
                    parsed["original"] = chunk["text"]
                    if not parsed.get("comment"):
                        parsed["comment"] = "模型未返回有效修订，已自动回退原文。"

                if content:
                    output_tokens = current_provider.count_tokens(content)
                    self.stats["total_tokens"] += output_tokens
    
                revised_text = parsed.get("revised", chunk["text"])
                original_text = chunk["text"]
    
                # --- Layer 3: Post-validation guards ---
                if revised_text and revised_text != original_text:
                    # 3a. Whitespace-only change detection (layout destruction)
                    if original_text.replace(' ', '').replace('\t', '') == revised_text.replace(' ', '').replace('\t', ''):
                        print(f"Post-validation REJECT: whitespace-only change detected (layout protection)")
                        revised_text = original_text
    
                    # Reference formatting can change length significantly
                    elif not is_ref:
                        # 3b. Dramatic length reduction (content deletion)
                        if len(revised_text) < len(original_text) * 0.5:
                            print(f"Post-validation REJECT: dramatic length reduction ({len(revised_text)} vs {len(original_text)})")
                            revised_text = original_text
    
                        # 3c. Dramatic length inflation (likely prompt leakage remnant)
                        elif len(revised_text) > len(original_text) * 1.5 and len(original_text) > 20:
                            print(f"Post-validation REJECT: dramatic length inflation ({len(revised_text)} vs {len(original_text)})")
                            revised_text = original_text
    
                if revised_text and revised_text != original_text:
                    self.stats["successful_edits"] += 1
                else:
                    self.stats["failed_edits"] += 1
    
                return {
                    "original_text": original_text,
                    "revised_text": revised_text,
                    "comment": parsed.get("comment", ""),
                    "paragraph_indices": chunk.get("paragraph_indices", []),
                    "success": True,
                    "raw_response": content
                }
    
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                
                # Check for rate limits or server unavailability
                if "503" in err_str or "429" in err_str or "timeout" in err_str or "connection" in err_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        sleep_time = (base_retry_delay * (2 ** attempt)) + random.uniform(0, 1)
                        idx = chunk.get("paragraph_indices", ["未知"])[0] if chunk.get("paragraph_indices") else "未知"
                        print(f"⚠️ [段落 {idx}] 触发 API 限流或网络异常 ({err_str[:50]}...), "
                              f"正在进行第 {attempt+1}/{max_retries} 次重试, 休眠 {sleep_time:.1f} 秒...")
                        time.sleep(sleep_time)
                        continue
                elif attempt < max_retries - 1:
                    # For other transient errors, perform a small delay and retry
                    sleep_time = base_retry_delay + random.uniform(0, 0.5)
                    time.sleep(sleep_time)
                    continue
                
                # If we exhausted attempts or decided not to retry
                break

        # If all retries failed
        self.stats["failed_edits"] += 1

        return {
            "original_text": chunk["text"],
            "revised_text": chunk["text"],
            "comment": f"处理失败 (已重试 {max_retries} 次): {str(last_error)}",
            "paragraph_indices": chunk.get("paragraph_indices", []),
            "success": False,
            "error": str(last_error)
        }

    def proofread_chunks(
        self,
        chunks: List[Dict],
        batch_size: int = 5,
        temperature: float = 0.3,
        show_progress: bool = False
    ) -> List[Dict]:
        """
        Proofread multiple chunks in parallel

        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of concurrent requests
            temperature: LLM temperature
            show_progress: Show progress information

        Returns:
            List of proofreading results
        """
        results = []

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            future_to_chunk = {
                executor.submit(self.proofread_chunk, chunk, temperature): chunk
                for chunk in chunks
            }

            for i, future in enumerate(as_completed(future_to_chunk), 1):
                result = future.result()
                results.append(result)

                if show_progress:
                    print(f"进度: {i}/{len(chunks)} ({i*100//len(chunks)}%)")

        results.sort(key=lambda x: x.get("paragraph_indices", [0])[0] if x.get("paragraph_indices") else 0)

        return results

    def proofread_document(
        self,
        chunks: List[Dict],
        batch_size: int = 5,
        temperature: float = 0.3,
        progress_callback=None
    ) -> Tuple[List[Dict], Dict]:
        """
        Proofread entire document

        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of concurrent requests
            temperature: LLM temperature
            progress_callback: Optional callback function for progress updates

        Returns:
            Tuple of (results, stats)
        """
        self.stats = {
            "total_chunks": len(chunks),
            "successful_edits": 0,
            "failed_edits": 0,
            "total_tokens": 0
        }

        from concurrent.futures import wait, FIRST_COMPLETED
        
        results = []
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            future_to_chunk = {
                executor.submit(self.proofread_chunk, chunk, temperature): chunk
                for chunk in chunks
            }

            done_count = 0
            all_futures = list(future_to_chunk.keys())
            
            while done_count < len(chunks):
                # Wait for at least one future to complete, or 1 second timeout for heartbeat
                done, not_done = wait(all_futures, timeout=1.0, return_when=FIRST_COMPLETED)
                
                # Process any newly completed futures
                for future in done:
                    if future in all_futures: # Ensure we only process each once
                        result = future.result()
                        results.append(result)
                        all_futures.remove(future)
                        done_count += 1
                
                # Always trigger callback for heartbeat (timer update)
                if progress_callback:
                    progress = done_count / len(chunks)
                    progress_callback(progress, done_count, len(chunks))

        results.sort(key=lambda x: x.get("paragraph_indices", [0])[0] if x.get("paragraph_indices") else 0)

        return results, self.stats

    def get_stats(self) -> Dict:
        """Get proofreading statistics"""
        return self.stats.copy()
