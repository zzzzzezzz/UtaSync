import os
import re
import time
import json
import threading
import concurrent.futures
from openai import OpenAI

class SubtitleTranslator:
    """
    大模型字幕翻译与纠错引擎 (强力纠错版 + 物理锁死时间轴 + 妥协放行防崩机制)
    """
    
    def __init__(self, api_key, base_url, primary_model, reasoning_model=None, srt_path="", reference_txt_path=None, output_mode="bilingual"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.primary_model = primary_model
        self.reasoning_model = reasoning_model if reasoning_model else primary_model 
        
        self.srt_path = srt_path
        self.reference_txt_path = reference_txt_path
        self.output_mode = output_mode
        self.max_workers = 3 
        
        base_name = os.path.splitext(srt_path)[0]
        suffix = "纯中文字幕" if output_mode == "chinese_only" else "双语字幕"
        self.output_srt_path = f"{base_name}_{suffix}.srt"
        
        self.cache_file = os.path.join(os.path.dirname(self.output_srt_path), f"{os.path.basename(base_name)}_翻译缓存.json")
        self.cache_lock = threading.Lock()
        self.translation_cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"   -> 💾 发现本地翻译进度缓存，已加载 {len(data)} 个批次。")
                    return data
            except Exception as e:
                print(f"   -> ⚠️ 缓存读取异常: {e}")
                return {}
        return {}

    def _save_to_cache(self, batch_idx, text):
        with self.cache_lock:
            self.translation_cache[str(batch_idx)] = text
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"   -> ⚠️ 缓存保存失败: {e}")

    def read_reference_lyrics(self):
        if self.reference_txt_path and os.path.exists(self.reference_txt_path):
            try:
                with open(self.reference_txt_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    lyric_name = os.path.basename(self.reference_txt_path)
                    print(f"   -> 📚 成功加载参考歌词: [{lyric_name}] (系统将分配极速主模型)")
                    return content
            except Exception:
                pass
        print("   -> 🔎 未检测到参考歌词！(系统将自动分配重型推理模型进行盲翻)")
        return ""

    def parse_srt(self):
        with open(self.srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        blocks = re.split(r'\n\s*\n', content)
        return [b.strip() for b in blocks if b.strip()]

    def _restore_timestamps(self, translated_content, original_blocks):
        """🌟 核心防护：物理锁死时间轴，防止大模型篡改或幻觉导致重叠"""
        time_map = {}
        for block in original_blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if len(lines) >= 2 and '-->' in lines[1]:
                idx = re.sub(r'[^\d]', '', lines[0])
                if idx:
                    time_map[idx] = lines[1]

        translated_blocks = re.split(r'\n\s*\n', translated_content.strip())
        restored_blocks = []
        
        for block in translated_blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines:
                continue
                
            idx_str = re.sub(r'[^\d]', '', lines[0])
            
            time_idx = -1
            for i, line in enumerate(lines):
                if '-->' in line:
                    time_idx = i
                    break
            
            if time_idx != -1 and idx_str in time_map:
                lines[time_idx] = time_map[idx_str]
                
            restored_blocks.append('\n'.join(lines))
            
        return '\n\n'.join(restored_blocks)

    def _reindex_srt(self, srt_content):
        blocks = re.split(r'\n\s*\n', srt_content.strip())
        valid_blocks = []
        
        for block in blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines:
                continue
                
            has_time = any('-->' in line for line in lines)
            
            if has_time:
                valid_blocks.append(lines)
            else:
                if valid_blocks:
                    valid_blocks[-1].extend(lines)
                    
        reindexed_blocks = []
        idx = 1
        
        for lines in valid_blocks:
            time_idx = -1
            for i, line in enumerate(lines):
                if '-->' in line:
                    time_idx = i
                    break
            
            if time_idx == -1:
                continue
                
            time_line = lines[time_idx]
            text_lines = lines[time_idx+1:]
            
            if not text_lines:
                continue
                
            if self.output_mode == "bilingual":
                # 斩杀纯假名噪音
                if len(text_lines) == 1 and re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text_lines[0]):
                    continue
            elif self.output_mode == "chinese_only":
                # 🌟 斩杀违规混入的日文双语
                if len(text_lines) > 1:
                    filtered_lines = [l for l in text_lines if not re.search(r'[\u3040-\u309F\u30A0-\u30FF]', l)]
                    if filtered_lines:
                        text_lines = filtered_lines
            
            new_block = f"{idx}\n{time_line}\n" + "\n".join(text_lines)
            reindexed_blocks.append(new_block)
            idx += 1
            
        return '\n\n'.join(reindexed_blocks)

    def translate_single_batch(self, batch_text, prev_context, batch_idx, total_batches, reference_lyrics, target_model, is_sub_batch=False):
        if not is_sub_batch and str(batch_idx) in self.translation_cache:
            return batch_idx, self.translation_cache[str(batch_idx)]
            
        if not is_sub_batch:
            print(f"   -> ⏳ [启动] 请求模型 {target_model} 翻译批次 {batch_idx + 1}/{total_batches} ...")
        else:
            print(f"      -> 🔪 [微型子批次] 正在处理被降级切分的片段 ...")
            
        prompt = self._build_prompt(batch_text, prev_context, reference_lyrics)
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=target_model,
                    messages=[
                        {"role": "system", "content": "你是一个严谨的日音Live字幕排版与翻译大师。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1, 
                    max_tokens=8192, 
                )
                
                if response.choices[0].finish_reason == "length":
                    raise Exception("API 返回长度触发限制，判定为残缺，准备重试")
                
                result_text = response.choices[0].message.content.strip()
                result_text = re.sub(r'<think>.*?</think>', '', result_text, flags=re.DOTALL).strip()
                result_text = result_text.replace("```srt", "").replace("```", "").strip()
                
                lines = result_text.split('\n')
                
                # 🌟 终极妥协机制：前4次严格要求，第5次(最后一次)直接豁免放行，保全大局！
                if len(lines) > 0 and attempt < max_retries - 1:
                    last_line = lines[-1].strip()
                    if re.match(r'^\d+$', last_line) or '-->' in last_line or result_text.endswith("-->") or (last_line.isdigit() and len(last_line) <= 3):
                        raise Exception("API 输出了没写完的半截子字幕，判定为网络异常，准备重试")
                
                if not is_sub_batch:
                    self._save_to_cache(batch_idx, result_text)
                
                if attempt == max_retries - 1:
                    print(f"   -> ⚠️ [妥协放行] 批次 {batch_idx + 1}/{total_batches} 多次格式异常，为防崩溃已强行放行该段落！")
                elif not is_sub_batch:
                    print(f"   -> ✅ [完成] 批次 {batch_idx + 1}/{total_batches} 翻译完毕！")
                    
                return batch_idx, result_text
                
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "403" in error_msg:
                    print(f"\n❌ [致命错误] 批次 {batch_idx + 1} API 认证失败: 请检查您的 API Key 是否正确。")
                    raise e
                
                # 🌟 动态切分降级机制：如果失败了 2 次，动刀切分！
                if attempt == 2 and not is_sub_batch:
                    blocks = batch_text.split('\n\n')
                    if len(blocks) > 1:
                        print(f"      -> 🪚 [动态降级] 批次 {batch_idx + 1} 过于复杂连续报错，正在将其切分为两半重新处理...")
                        half = len(blocks) // 2
                        part1 = '\n\n'.join(blocks[:half])
                        part2 = '\n\n'.join(blocks[half:])
                        
                        _, res1 = self.translate_single_batch(part1, prev_context, batch_idx, total_batches, reference_lyrics, target_model, is_sub_batch=True)
                        _, res2 = self.translate_single_batch(part2, prev_context, batch_idx, total_batches, reference_lyrics, target_model, is_sub_batch=True)
                        
                        combined_result = res1 + "\n\n" + res2
                        self._save_to_cache(batch_idx, combined_result)
                        print(f"   -> ✅ [完成] 批次 {batch_idx + 1}/{total_batches} (通过切分降级) 翻译完毕！")
                        return batch_idx, combined_result
                
                if "429" in error_msg or "RateLimitError" in error_msg:
                    sleep_time = 15 * (attempt + 1)
                    print(f"      ⚠️ [并发受限] 批次 {batch_idx + 1} 触发 429 频率限制，休眠 {sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                else:
                    print(f"      ⚠️ 批次 {batch_idx + 1} 发生错误 ({error_msg})，正在尝试重试 ({attempt+1}/{max_retries})...")
                    time.sleep(5)
        else:
            raise Exception(f"❌ 批次 {batch_idx + 1} 重试次数过多，任务异常终止。")

    def translate_blocks(self, blocks, reference_lyrics=""):
        batch_size = 30
        batches = []
        contexts = [] 
        
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i+batch_size]
            batches.append("\n\n".join(batch))
            
            if i == 0:
                contexts.append("")
            else:
                prev_lines = blocks[max(0, i-2):i]
                contexts.append("\n\n".join(prev_lines))
            
        total_batches = len(batches)
        results = []
        active_model = self.primary_model if reference_lyrics else self.reasoning_model

        print(f"   -> 🚀 启动多线程并发翻译 (并发数: {self.max_workers})，共计 {total_batches} 个批次...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {
                executor.submit(self.translate_single_batch, text, ctx, idx, total_batches, reference_lyrics, active_model): idx 
                for idx, (text, ctx) in enumerate(zip(batches, contexts))
            }
            
            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    batch_idx, translated_text = future.result()
                    results.append((batch_idx, translated_text))
                except Exception as exc:
                    print(f"   -> ❌ [任务中断] 由于 API 报错，翻译进程已停止。错误详情: {exc}")
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise exc

        results.sort(key=lambda x: x[0])
        ordered_translated_blocks = [text for idx, text in results]
        return "\n\n".join(ordered_translated_blocks)

    def _build_prompt(self, srt_batch_text, prev_context, reference_lyrics):
        if self.output_mode == "bilingual":
            format_rules = """
6. 🚫 【严禁合并时间轴】：输入的原轴有几个时间段，你就必须输出几个！绝对不允许为了凑完整句子，而把两三个时间轴强行合并成一个大轴！
7. 📝 【强制单行排版】：同一个时间轴内，【只允许1行日文和1行中文】！无论句子多长，都绝对不准在日文或中文内部使用换行符拆分！日文必须是完整的一行，紧接着中文是完整的一行。
8. 🗑️ 【过滤杂音】：如果发音是纯粹的无意义杂音、和声（且不在歌词库中），请必须直接删除该时间轴，不要输出任何替代文字。
9. 🔄 【强制替换日文原文】：输入的原轴中如果有听错的假名/片假名（拼音），【绝对不准】原样照抄！你必须根据发音，用官方歌词库中绝对正确的日文原句（汉字/平假名）将其彻底替换掉！
输出格式示例：
1
00:00:00,000 --> 00:00:05,000
笑って生きることが楽になるの
笑着活下去会变得轻松吗
"""
        else:
            format_rules = """
6. 🚫 【严禁合并时间轴】：输入的原轴有几个时间段，你就必须输出几个！绝对不允许擅自合并时间轴！
7. 📝 【强制单行排版】：同一个时间轴内，【只允许1行中文】！无论句子多长，都绝对不准使用换行符！
8. 🗑️ 【过滤杂音】：无意义的杂音、和声请直接删除该时间轴。绝不允许输出日文原文。
9. 🚨 【零日文容忍】：输出文本中【绝对不允许】包含任何日文平假名或片假名！必须全部翻译为中文。如果遇到人名，请音译或保留英文字母，绝对不准输出日文！
输出格式示例：
1
00:00:00,000 --> 00:00:05,000
笑着活下去会变得轻松吗
"""

        system_instruction = f"""
【核心任务】
请根据粗听 SRT 中的发音，去参考歌词库中寻找绝对正确的原句进行替换，并进行翻译排版。

【⚠️ 绝对不可触犯的死命令 - 否则任务失败】
1. ⏱️ 【时间轴格式】：必须严格保留时间跨度格式（00:00:00,000 --> 00:00:00,000）。
2. 🚫 【禁止做任何总结或注释】：严禁输出如“[注：此处为和声不予呈现]”之类的文字。直接合并或删除即可。
3. 🎤 【MC 谈话处理】：如果在歌词库找不到对应的词，说明是歌手在说话！请发挥你的听译能力，将内容翻译成中文，严禁跳过不翻。
4. 🗑️ 【纯净输出】：不要输出任何多余的前言、后记或思考过程，直接返回纯净的 SRT 结果。
5. 🛡️ 【严禁偷懒与截断】：你必须完整翻译输入的每一行字幕！绝对不允许中途停止、省略后半部分或罢工，务必把提供的所有文本处理完！
{format_rules}
"""
        if reference_lyrics:
            system_instruction += f"=== 📖 官方参考歌词库 ===\n{reference_lyrics}\n======================\n\n"
        
        if prev_context:
            system_instruction += f"=== 📖 上下文前情提要 (参考用，请勿输出翻译) ===\n{prev_context}\n======================\n\n"
            
        system_instruction += f"【请处理以下这批当前批次的 SRT 字幕】：\n{srt_batch_text}"
        
        return system_instruction

    def run(self):
        print(f"\n🤖 [大模型处理阶段] 启动高精度翻译与智能排版引擎...")
        reference_lyrics = self.read_reference_lyrics()
        blocks = self.parse_srt()
        
        try:
            start_time = time.time()
            final_srt_content = self.translate_blocks(blocks, reference_lyrics)
            
            # 🌟 物理锁死时间轴
            final_srt_content = self._restore_timestamps(final_srt_content, blocks)
            
            final_srt_content = self._reindex_srt(final_srt_content)
            
            with open(self.output_srt_path, 'w', encoding='utf-8') as f:
                f.write(final_srt_content)
                
            elapsed_time = int(time.time() - start_time)
            print(f"🎉 翻译大功告成！大模型阶段纯运转耗时: {elapsed_time} 秒")
            print(f"📁 最终字幕已就绪: {self.output_srt_path}")
            
            return self.output_srt_path
        except Exception:
            print("\n❌ 翻译阶段失败。由于 API Key 无效或网络原因，未能生成最终字幕。")
            print("💡 建议：请检查 API Key 后再次运行程序，断点续传机制会自动跳过已完成的部分。")
            return None