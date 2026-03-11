import os
import sys
import time
import subprocess
import hashlib
import shutil
import glob
import gc
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
        self.cancel_event = None # 🌟 接收外部的秒杀信号

    def _run_cmd(self, cmd, hide_output=True):
        """🌟 进程级安全秒杀器：取代原本会卡死的 subprocess.run"""
        out_target = subprocess.DEVNULL if hide_output else None
        process = subprocess.Popen(cmd, stdout=out_target, stderr=out_target)
        while process.poll() is None:
            if self.cancel_event and self.cancel_event.is_set():
                process.terminate()
                process.wait()
                raise Exception("用户中断：已安全切断外部进程 (FFmpeg/Demucs)")
            time.sleep(0.5)
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
        self._run_cmd(command, hide_output=True)
        return self.audio_path

    def isolate_vocals(self, skip=False):
        if skip:
            print(f"⏩ [步骤 2/4] 极速模式：已跳过 Demucs 人声分离，直接使用源音频！")
            self.vocal_path = self.audio_path
            return self.vocal_path

        duration = 0
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.audio_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
            duration = float(res.stdout.strip())
        except Exception:
            pass

        print(f"🎸 [步骤 2/4] 正在使用 Demucs 高精模型分离人声...")
        
        if duration > 1200:
            print(f"   -> ⚠️ 检测到超长音频 (约 {int(duration//60)} 分钟)！")
            print(f"   -> 🛡️ 启动【无缝切片防爆内存】引擎，将分段处理以保护您的电脑...")
            
            chunks_dir = os.path.join(self.audio_dir, "chunks")
            os.makedirs(chunks_dir, exist_ok=True)
            
            chunk_pattern = os.path.join(chunks_dir, "chunk_%03d.wav")
            self._run_cmd(["ffmpeg", "-i", self.audio_path, "-f", "segment", "-segment_time", "1200", "-c", "copy", chunk_pattern, "-y"], hide_output=True)
            
            chunks = sorted(glob.glob(os.path.join(chunks_dir, "chunk_*.wav")))
            vocal_chunks = []
            
            for i, chunk_file in enumerate(chunks):
                print(f"      -> 正在提取分段 {i+1}/{len(chunks)} 的人声 (安全运行中)...")
                self._run_cmd(["demucs", "-n", "htdemucs_ft", "--two-stems=vocals", "-o", chunks_dir, chunk_file], hide_output=True)
                
                chunk_name = os.path.splitext(os.path.basename(chunk_file))[0]
                chunk_vocal = os.path.join(chunks_dir, "htdemucs_ft", chunk_name, "vocals.wav")
                if os.path.exists(chunk_vocal):
                    vocal_chunks.append(chunk_vocal)

            print(f"   -> 🧩 所有分段处理完毕，正在无缝拼接最终人声...")
            concat_txt = os.path.join(chunks_dir, "concat.txt")
            with open(concat_txt, "w", encoding="utf-8") as f:
                for vc in vocal_chunks:
                    safe_path = vc.replace('\\', '/')
                    f.write(f"file '{safe_path}'\n")
                    
            self._run_cmd(["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", self.final_vocal_path, "-y"], hide_output=True)
            self.vocal_path = self.final_vocal_path
            
            shutil.rmtree(chunks_dir, ignore_errors=True)
            print("   -> ✅ 拼接完成！内存防爆机制运行成功。")
            return self.vocal_path
            
        else:
            command = [
                "demucs", "-n", "htdemucs_ft", "--two-stems=vocals", 
                "-o", self.output_dir, self.audio_path
            ]
            self._run_cmd(command, hide_output=False)
            
            vocal_path = os.path.join(self.output_dir, "htdemucs_ft", f"{self.safe_name}_源音频", "vocals.wav")
            if os.path.exists(vocal_path):
                self.vocal_path = vocal_path
                return self.vocal_path
            else:
                raise FileNotFoundError("找不到分离后的人声文件。请检查源音频是否存在。")

    def transcribe_to_srt(self, model_size="large-v2", audio_type="live", skipped_demucs=False):
        print(f"📝 [步骤 3/4] 正在加载 Faster-Whisper ({model_size}) 模型...")
        model_dir = os.path.abspath("models_faster") 
        os.makedirs(model_dir, exist_ok=True)
        
        try:
            self.model = WhisperModel(model_size, device="cuda", compute_type="float16", download_root=model_dir)
            print("   -> 🚀 成功启用 GPU 显卡加速！")
        except Exception:
            print("   -> ⚠️ GPU 加载失败，降级使用 CPU")
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8", download_root=model_dir)
            
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
                
            # 🚫 彻底删除了 del self.model, gc.collect(), empty_cache 等强杀代码
            # 让底层的垃圾回收顺其自然，永不触发 C++ 线程段错误闪退！
            
        except Exception as e:
            print(f"   -> ⚠️ 缓存清理时出现小问题 (可忽略): {e}")

    def _format_timestamp(self, seconds: float):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def run(self, model_size="large-v2", audio_type="live", skip_separation=False, cancel_event=None):
        self.cancel_event = cancel_event
        start_time = time.time() 
        try:
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
                self.isolate_vocals(skip=skip_separation) 
                
                with open(self.strategy_flag_path, "w", encoding="utf-8") as f:
                    f.write(current_strategy)
                
            srt_path = self.transcribe_to_srt(model_size=model_size, audio_type=audio_type, skipped_demucs=skip_separation)
            
            self.cleanup_temp_files()
            
            elapsed_time = time.time() - start_time
            mins = int(elapsed_time // 60)
            secs = int(elapsed_time % 60)
            print(f"\n⏱️ [性能报告] 音频提取与打轴总耗时: {mins} 分 {secs} 秒")
            return srt_path
        except Exception as e:
            print(f"\n❌ 程序运行出错: {e}")
            return None