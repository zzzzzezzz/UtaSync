import os
import sys
import time
import subprocess
import hashlib
import shutil
import glob
import gc
import torch
from faster_whisper import WhisperModel 

# 🌟 限制底层 AI 引擎的核心数，防止 CPU 满载卡死
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
# 🌟 神级补丁：防止 Faster-Whisper 与大模型请求库发生底层 DLL 线程冲突！
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE" 

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 🌟 神级补丁：自动扫描并注册 NVIDIA 显卡 DLL，解决 PyInstaller 打包后漏文件报错！
try:
    import nvidia
    nvidia_base = None
    if hasattr(nvidia, '__file__') and nvidia.__file__ is not None:
        nvidia_base = os.path.dirname(nvidia.__file__)
    elif hasattr(nvidia, '__path__'):
        nvidia_base = list(nvidia.__path__)[0]
    if nvidia_base:
        for root, dirs, files in os.walk(nvidia_base):
            if any(file.endswith('.dll') for file in files):
                os.environ["PATH"] += os.pathsep + root
except ImportError:
    pass

class LiveSubtitleGenerator:
    def __init__(self, video_path, output_dir="output"):
        self.video_path = os.path.abspath(video_path)
        self.base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        self.output_dir = os.path.abspath(os.path.join(output_dir, self.base_name))
        self.audio_dir = os.path.join(self.output_dir, "audio")
        self.subs_dir = os.path.join(self.output_dir, "subtitles")
        
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.subs_dir, exist_ok=True)
        
        self.safe_name = hashlib.md5(self.base_name.encode('utf-8')).hexdigest()[:8]
        self.final_vocal_path = os.path.join(self.audio_dir, f"{self.base_name}_纯净人声.wav")
        self.strategy_flag_path = os.path.join(self.audio_dir, "separation_strategy.txt")
        self.model = None
        self.cancel_event = None 

    def _run_cmd(self, cmd, hide_output=True, task_name=None):
        """🌟 进程级安全秒杀器 + 智能心跳监测 + 底层报错透传 (彻底解决黑框版)"""
        log_path = os.path.join(self.audio_dir, "last_cmd.log")
        out_file = None
        
        if hide_output:
            out_file = open(log_path, "w", encoding="utf-8", errors="ignore")
            
        popen_kwargs = {
            "stdout": out_file if hide_output else None,
            "stderr": subprocess.STDOUT if hide_output else None,
            "text": True, 
            "encoding": "utf-8", 
            "errors": "ignore"
        }
        
        # 🌟 核心修复：强制屏蔽 Windows 命令行黑框弹窗
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = 0x08000000
            
        try:
            process = subprocess.Popen(cmd, **popen_kwargs)
        except FileNotFoundError:
            if out_file: out_file.close()
            raise Exception(f"🚨 系统找不到核心工具 [{cmd[0]}.exe]！\n💡 解决方案：您的环境变量可能未生效，请彻底重启编辑器；或直接将 {cmd[0]}.exe 复制到 app.py 所在的文件夹中！")
            
        start_time = time.time()
        last_heartbeat = start_time
        
        while process.poll() is None:
            if self.cancel_event and self.cancel_event.is_set():
                process.kill()
                process.wait()
                if out_file: out_file.close()
                raise Exception("用户中断：已安全切断外部进程 (FFmpeg/Demucs)")
            
            if task_name:
                current_time = time.time()
                if current_time - last_heartbeat >= 30:
                    elapsed = int(current_time - start_time)
                    print(f"      -> ⏳ [系统心跳] {task_name} 正在后台全速狂飙，请耐心等待 (已耗时 {elapsed} 秒)...")
                    last_heartbeat = current_time

            time.sleep(0.5)
            
        if out_file:
            out_file.close()
            
        if process.returncode != 0:
            err_msg = "未能捕获到底层输出。请检查环境。"
            if hide_output and os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if content:
                        err_msg = content[-1500:] 
            
            raise Exception(f"进程异常退出 (退出码: {process.returncode})。\n[🔍 底层真实报错日志]：\n{err_msg}")
            
        return process.returncode

    def extract_audio(self):
        print(f"🎤 [步骤 1/4] 正在提取/转换音频格式...")
        self.audio_path = os.path.join(self.audio_dir, f"{self.safe_name}_源音频.wav")
        if os.path.exists(self.audio_path):
            return self.audio_path
            
        command = [
            "ffmpeg", "-i", self.video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            self.audio_path, "-y"
        ]
        self._run_cmd(command, hide_output=True, task_name="音频提取")
        return self.audio_path

    def isolate_vocals(self, skip=False, hardware_mode="low"):
        if skip:
            print(f"⏩ [步骤 2/4] 极速模式：已跳过 Demucs 人声分离，直接使用源音频！")
            self.vocal_path = self.audio_path
            return self.vocal_path

        print(f"🎸 [步骤 2/4] 正在使用 Demucs 高精模型分离人声...")
        
        # 🌟 算力调度核心逻辑：根据传进来的 hardware_mode 动态分配胃口
        segment_args = []
        if hardware_mode == "high":
            chunk_length = "1800" 
            print(f"   -> 🚀 启动【满血狂飙】引擎，解除所有显存封印 (每 {chunk_length} 秒一段)...")
        elif hardware_mode == "medium":
            chunk_length = "180"  
            print(f"   -> ⚖️ 启动【均衡提速】引擎，兼顾速度与稳定 (每 {chunk_length} 秒一段)...")
        else:
            chunk_length = "60"   
            segment_args = ["--segment", "2"] 
            print(f"   -> 🛡️ 启动【极限防爆】引擎，物理锁死显存峰值 (每 {chunk_length} 秒一段)...")
        
        chunks_dir = os.path.join(self.audio_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        chunk_pattern = os.path.join(chunks_dir, "chunk_%03d.wav")
        self._run_cmd(["ffmpeg", "-i", self.audio_path, "-f", "segment", "-segment_time", chunk_length, "-c", "copy", chunk_pattern, "-y"], hide_output=True)
        
        # 🌟 核心修复：弃用 glob，改用 os.listdir，彻底免疫文件名中的 [] 等特殊符号！
        chunks = []
        if os.path.exists(chunks_dir):
            for f in os.listdir(chunks_dir):
                if f.startswith("chunk_") and f.endswith(".wav"):
                    chunks.append(os.path.join(chunks_dir, f))
        chunks = sorted(chunks)

        vocal_chunks = []
        
        if not chunks:
            raise Exception("音频切片失败，无法生成分段文件。请检查音频源。")

        for i, chunk_file in enumerate(chunks):
            status_msg = f"正在提取分段 {i+1}/{len(chunks)} 的人声..."
            if hardware_mode == "low": status_msg += " (极致锁死显存中)"
            elif hardware_mode == "high": status_msg += " (算力火力全开中)"
            print(f"      -> {status_msg}")
            
            cmd = [
                "demucs", "-n", "htdemucs_ft", 
                "--two-stems=vocals"
            ] + segment_args + [
                "-o", chunks_dir, chunk_file
            ]
            
            try:
                self._run_cmd(cmd, hide_output=True, task_name=f"人声分离 (第 {i+1} 分段)")
            except Exception as e:
                raise Exception(f"Demucs 在处理第 {i+1} 个切片时彻底崩溃！\n{str(e)}")
                
            chunk_name = os.path.splitext(os.path.basename(chunk_file))[0]
            chunk_vocal = os.path.join(chunks_dir, "htdemucs_ft", chunk_name, "vocals.wav")
            if os.path.exists(chunk_vocal):
                vocal_chunks.append(chunk_vocal)
            else:
                 print(f"      -> ⚠️ 警告：找不到分段 {i+1} 的分离人声，可能该片段极其短暂或出错了。")

        if not vocal_chunks:
            raise Exception("所有分段处理完毕，但未能提取到任何人声文件！")

        print(f"   -> 🧩 所有分段处理完毕，正在无缝拼接最终人声...")
        concat_txt = os.path.join(chunks_dir, "concat.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for vc in vocal_chunks:
                safe_path = vc.replace('\\', '/')
                f.write(f"file '{safe_path}'\n")
                
        self._run_cmd(["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", self.final_vocal_path, "-y"], hide_output=True)
        self.vocal_path = self.final_vocal_path
        
        shutil.rmtree(chunks_dir, ignore_errors=True)
        print("   -> ✅ 拼接完成！音频分离调度机制运行成功。")
        return self.vocal_path

    def transcribe_to_srt(self, model_size="large-v2", audio_type="live", skipped_demucs=False):
        print(f"📝 [步骤 3/4] 正在加载/下载 Faster-Whisper ({model_size}) 模型...")
        
        if "large-v2" in model_size:
            print("   -> 💡 模型特性: [日音战神] 沉稳抗噪，对残留乐器有钝感力，极难产生幻觉，Live 现场首选！")
        elif "large-v3-turbo" in model_size:
            print("   -> 💡 模型特性: [极速刺客] 速度极快且体积小，但较敏感，适合无伴奏长播客或纯净人声。")
        elif "large-v3" in model_size:
            print("   -> 💡 模型特性: [高精放大镜] 对微小声音极度敏感，不推荐用于嘈杂的音乐现场，易产生幻觉。")
        elif "medium" in model_size or "small" in model_size or "base" in model_size:
            print("   -> 💡 模型特性: [轻量救星] 速度极快、极省显存。适合低配电脑，但复杂场景下准确率会下降。")

        print(f"   -> 💡 下载提示: 若首次使用此模型，系统正从云端下载权重 (约 1.5G~3G)。")
        print(f"   -> ⏳ 下载过程根据网速可能需要 3~15 分钟，后台正在拼命拉取，请勿关闭软件...")
        
        if self.cancel_event and self.cancel_event.is_set():
            raise Exception("用户中断：加载模型前已被取消")
            
        model_dir = os.path.abspath("models_faster") 
        os.makedirs(model_dir, exist_ok=True)
        
        try:
            self.model = WhisperModel(model_size, device="cuda", compute_type="float16", download_root=model_dir)
            print("   -> 🚀 模型准备就绪，成功启用 GPU 显卡加速！")
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "connection" in error_msg or "urllib3" in error_msg or "read operation timed out" in error_msg:
                raise Exception("模型下载超时！由于文件较大，您的网络中途断开。\n💡 别担心！系统已保存下载进度，请再次点击「启动」，它会自动【断点续传】！")
            
            print(f"   -> ⚠️ GPU 加载失败 ({e})，降级使用 CPU...")
            try:
                self.model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=model_dir)
                print("   -> 🚀 成功启用 CPU 模式运行！")
            except Exception as cpu_e:
                cpu_err = str(cpu_e).lower()
                if "timeout" in cpu_err or "connection" in cpu_err or "urllib3" in cpu_err:
                    raise Exception("模型下载超时！由于文件较大，您的网络中途断开。\n💡 别担心！系统已保存下载进度，请再次点击「启动」，它会自动【断点续传】！")
                raise Exception(f"CPU 加载模型彻底失败: {cpu_e}")
            
        if self.cancel_event and self.cancel_event.is_set():
            raise Exception("用户中断：模型加载完毕，打轴动作已终止")
            
        print(f"   -> 开始生成时间轴 (模式: {audio_type})...")
        
        use_vad = True
        
        if audio_type == "live":
            prompt = "これはライブ音楽の歌詞です。正確に書き起こしてください。"
            silence_ms = 1000
            pad_ms = 200
            max_duration = 8.0  
            vad_threshold = 0.5 
            
            if skipped_demucs:
                use_vad = False
                print("   -> ⚠️ 警告: 检测到跳过分离，已强行关闭 VAD 防白卷。")
                
        elif audio_type == "live_soft":
            prompt = "これはライブ音楽の歌詞です。正確に書き起こしてください。"
            silence_ms = 1000
            pad_ms = 200
            max_duration = 8.0  
            vad_threshold = 0.3 
            
            if skipped_demucs:
                use_vad = False
                print("   -> ⚠️ 警告: 检测到跳过分离，已强行关闭 VAD 防白卷。")
                
        else:
            prompt = "これは日本語のインタビューや日常会話です。正確に書き起こしてください。"
            silence_ms = 500
            pad_ms = 0
            max_duration = 5.0  
            vad_threshold = 0.5

        vad_params = dict(
            threshold=vad_threshold, 
            min_silence_duration_ms=silence_ms,
            speech_pad_ms=pad_ms
        ) if use_vad else None

        segments, info = self.model.transcribe(
            self.vocal_path, 
            language="ja", 
            condition_on_previous_text=False,
            beam_size=5,
            initial_prompt=prompt,
            vad_filter=use_vad, 
            vad_parameters=vad_params
        )
        
        srt_path = os.path.join(self.subs_dir, f"{self.base_name}_极致打轴.srt")
        valid_index = 1
        with open(srt_path, "w", encoding="utf-8") as srt_file:
            for segment in segments:
                if self.cancel_event and self.cancel_event.is_set():
                    print("   -> 🛑 收到终止指令，打轴引擎已安全断电！")
                    raise Exception("用户中断：大模型打轴已停止")
                
                text = segment.text.strip()
                
                if "書き起こして" in text or "ライブ音楽" in text:
                    continue
                    
                start_val = segment.start
                end_val = segment.end
                
                if (end_val - start_val) > max_duration:
                    end_val = start_val + max_duration
                
                start_time = self._format_timestamp(start_val)
                end_time = self._format_timestamp(end_val)
                
                print(f"   [{start_time} -> {end_time}] {text}")
                
                srt_file.write(f"{valid_index}\n")
                srt_file.write(f"{start_time} --> {end_time}\n")
                srt_file.write(f"{text}\n\n")
                valid_index += 1
                
        print(f"✅ 成功！原文字幕已收纳至: {srt_path}")
        return srt_path 

    def cleanup_temp_files(self):
        try:
            if hasattr(self, 'audio_path') and hasattr(self, 'vocal_path') and self.audio_path != self.vocal_path:
                if os.path.exists(self.audio_path):
                    os.remove(self.audio_path)
                    
            if hasattr(self, 'vocal_path') and os.path.exists(self.vocal_path):
                if os.path.abspath(self.vocal_path) != os.path.abspath(self.final_vocal_path):
                    shutil.move(self.vocal_path, self.final_vocal_path)
                    self.vocal_path = self.final_vocal_path
                    
            htdemucs_dir = os.path.join(self.output_dir, "htdemucs_ft")
            if os.path.exists(htdemucs_dir):
                shutil.rmtree(htdemucs_dir)
        except Exception as e:
            print(f"   -> ⚠️ 缓存清理时出现小问题 (可忽略): {e}")

    def _format_timestamp(self, seconds: float):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def run(self, model_size="large-v2", audio_type="live", skip_separation=False, hardware_mode="low", cancel_event=None):
        self.cancel_event = cancel_event
        start_time = time.time() 
        try:
            if self.cancel_event and self.cancel_event.is_set():
                raise Exception("用户中断：任务尚未开始即被取消")
                
            current_strategy = "skip" if skip_separation else "demucs"
            cache_valid = False
            
            if os.path.exists(self.final_vocal_path) and os.path.exists(self.strategy_flag_path):
                with open(self.strategy_flag_path, "r", encoding="utf-8") as f:
                    saved_strategy = f.read().strip()
                if saved_strategy == current_strategy:
                    cache_valid = True
            
            if cache_valid:
                print("   -> ⚡ 检测到有效音频缓存，跳过提取与分离，直达打轴！")
                self.vocal_path = self.final_vocal_path
            else:
                if os.path.exists(self.final_vocal_path):
                    print("   -> 🔄 检测到分离策略变更，已作废旧缓存，重新提取音频...")
                    os.remove(self.final_vocal_path) 
                    
                self.extract_audio()
                self.isolate_vocals(skip=skip_separation, hardware_mode=hardware_mode) 
                
                with open(self.strategy_flag_path, "w", encoding="utf-8") as f:
                    f.write(current_strategy)
                
            srt_path = self.transcribe_to_srt(model_size=model_size, audio_type=audio_type, skipped_demucs=skip_separation)
            
            self.cleanup_temp_files()
            
            elapsed_time = time.time() - start_time
            mins = int(elapsed_time // 60)
            secs = int(elapsed_time % 60)
            print(f"\n⏱️ [性能报告] 音频提取与打轴总耗时: {mins} 分 {secs} 秒")
            
            if hasattr(self, 'model') and self.model is not None:
                del self.model
                self.model = None
            gc.collect()
            
            return srt_path
        except Exception as e:
            if "用户中断" not in str(e):
                print(f"\n❌ 程序运行出错: {e}")
            return None