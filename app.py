import os
import sys
import json
import time
import threading
import hashlib
import queue 
import gc
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from core.generator import LiveSubtitleGenerator
    from core.translator import SubtitleTranslator
except ImportError as e:
    print(f"⚠️ 核心引擎导入失败: {e}\n请确保 app.py 与 core 文件夹在同一级目录下。")

# ==========================================
# 🎨 终极高级感调色板
# ==========================================
BG_WORKSPACE = "#000000"  
BG_SIDEBAR = "#0A0A0A"    
BG_CARD = "#151515"       
BG_GROUP = "#1A1A1A"      

ACCENT_PRIMARY = "#FFFFFF" 
ACCENT_GREEN = "#1DB954"   
ACCENT_RED = "#991B1B"     
ACCENT_RED_HOVER = "#7F1D1D"

TEXT_TITLE = "#FFFFFF"     
TEXT_MUTED = "#888888"     
TEXT_HINT = "#666666"      

ctk.set_appearance_mode("dark")

SETTINGS_FILE = "user_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "api_key": "", "api_preset": "SiliconFlow (DeepSeek-V3)", 
        "api_url": "https://api.siliconflow.cn/v1",
        "api_model": "deepseek-ai/DeepSeek-V3",
        "model_size": "large-v2 (战神级/推荐)", "audio_type": "Live 现场演唱 (常规/摇滚)", 
        "output_mode": "中日双语字幕", "use_demucs": "开启分离 (Live音乐必选)",
        "proxy_url": "",
        "cached_lyrics": "" 
    }

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except:
        pass

class StdoutRedirector:
    """🌟 工业级防闪退：队列式日志重定向"""
    def __init__(self, queue_obj):
        self.queue = queue_obj
        
    def write(self, string):
        self.queue.put(string)
        
    def flush(self): pass

class UtaSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("UtaSync - Professional Subtitle Studio")
        self.geometry("1300x940") 
        self.minsize(1100, 800)
        self.configure(fg_color=BG_WORKSPACE)
        
        self.video_path = ""
        self.is_running = False
        self.cancel_event = threading.Event() 
        self.settings = load_settings()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_workspace()

        self.log_queue = queue.Queue()
        self.stdout_redirector = StdoutRedirector(self.log_queue)
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stdout_redirector
        
        self.after(100, self.process_console_queue)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        print("💡 UtaSync 核心引擎已挂载就绪。\n等待导入媒体文件...")

    def save_all_ui_states(self):
        self.settings = {
            "api_key": self.api_key_entry.get().strip(), 
            "api_preset": self.opt_api_preset.get(),
            "api_url": self.api_url_entry.get().strip(),
            "api_model": self.api_model_entry.get().strip(),
            "model_size": self.opt_model.get(), 
            "audio_type": self.opt_audio_type.get(), 
            "output_mode": self.opt_output_mode.get(), 
            "use_demucs": self.opt_demucs.get(),
            "proxy_url": self.proxy_entry.get().strip(),
            "cached_lyrics": self.lyrics_textbox.get("1.0", "end-1c") 
        }
        save_settings(self.settings)

    def on_closing(self):
        try:
            self.save_all_ui_states()
        except Exception:
            pass
            
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.destroy()
        os._exit(0)

    def process_console_queue(self):
        if not self.log_queue.empty():
            content = ""
            while not self.log_queue.empty():
                try:
                    content += self.log_queue.get_nowait()
                except queue.Empty:
                    break
            
            if content:
                self.console_textbox.configure(state="normal")
                self.console_textbox.insert("end", content)
                self.console_textbox.see("end") 
                self.console_textbox.configure(state="disabled")
                
        self.after(50, self.process_console_queue)

    def show_help_dialog(self):
        help_window = ctk.CTkToplevel(self)
        help_window.title("UtaSync 参数说明与帮助指南")
        help_window.geometry("680x780")
        help_window.minsize(600, 650)
        help_window.configure(fg_color=BG_WORKSPACE)
        help_window.attributes("-topmost", True) 
        
        title_lbl = ctk.CTkLabel(help_window, text="📖 UtaSync 参数配置说明", font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"), text_color=TEXT_TITLE)
        title_lbl.pack(pady=(25, 15))
        
        help_textbox = ctk.CTkTextbox(help_window, font=ctk.CTkFont(family="Microsoft YaHei", size=13), fg_color=BG_CARD, text_color="#CCCCCC", wrap="word", corner_radius=10)
        help_textbox.pack(fill="both", expand=True, padx=25, pady=(0, 25))
        
        help_text = """
【🎵 声学模型 (Acoustic)】
• Live 现场演唱 (常规/摇滚)：防漂移时间设为 8 秒，包容高强度的乐器和伴奏，最适合绝大多数的演唱会。
• Live 现场演唱 (极柔气声/清唱)：VAD 敏感度更高，适合只有钢琴伴奏、或者歌手极度轻柔呢喃的特种 Live。
• 访谈 / 电台播客：防霸屏时间设为 5 秒，快速断句，适合纯说话、无伴奏的场景。

【🎸 分离策略 (Demucs)】
• 开启分离 (必选)：只要背景有伴奏、BGM、乐器，就必须开启！否则底层 Whisper 会产生严重的时间轴幻觉。
• 强制跳过：仅适用于【完全没有背景音乐】的纯人声电台、播客。跳过分离可节省大量时间和电脑内存。

【🧠 引擎精度与模型性格 (Whisper)】
• large-v2 (日音战神/推荐)：极其沉稳、抗噪，对背景杂音有"钝感力"，极难产生幻觉。Live 现场的首选！
• large-v3-turbo (极速刺客)：速度是 v2 的数倍，体积小巧。但极其敏感，适合无伴奏的长播客或纯净人声。
• large-v3 (高精放大镜)：词汇量最大，对微小声音极度敏感。不推荐用于音乐现场，容易把残留乐器声听成幻觉。
• medium / small (轻量救星)：速度快、省显存。适合显卡显存低于 6GB 的用户，但在复杂场景下准确率会下降。

【🌍 大模型 API (翻译阶段)】
• 推荐主力：SiliconFlow (硅基流动)。采用 DeepSeek-V3 作为主力，国内直连无需梯子，速度快且不易被封禁断连。
• 自定义接口：支持任何兼容 OpenAI 格式的 API。只需要在下拉框选择 [完全自定义]，填入供应商提供的 Base URL (必须以 /v1 结尾) 和对应的模型代号即可。
• 代理支持：如果您使用的是国外大模型 (如 Google Gemini)，请务必在底部的 [本地代理] 框填入您梯子的端口号，例如 "http://127.0.0.1:10808" 或 "socks5://127.0.0.1:10808"。

【💡 其他高阶提示】
1. 盲翻模式：如果在右侧不贴入日文参考歌词本，大模型将完全凭借发音去自由翻译（适合访谈播客）。
2. 断点续传：程序意外中断（或您手动停止）后，只要不修改打轴参数，再次运行会自动跳过已完成的人声分离和听写阶段，直接进入翻译！
        """.strip()
        
        help_textbox.insert("1.0", help_text)
        help_textbox.configure(state="disabled") 

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=380, corner_radius=0, fg_color=BG_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.sidebar.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="UtaSync", font=ctk.CTkFont(family="Segoe UI Black", size=42, weight="bold"), text_color=TEXT_TITLE)
        self.logo_label.grid(row=0, column=0, padx=40, pady=(45, 0), sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(self.sidebar, text="Auto Subtitle Pipeline", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=TEXT_MUTED)
        self.subtitle_label.grid(row=1, column=0, padx=42, pady=(0, 15), sticky="w")

        self.help_btn = ctk.CTkButton(self.sidebar, text="📖 参数指南说明", font=ctk.CTkFont(family="Microsoft YaHei", size=11, weight="bold"), width=110, height=26, fg_color="#181818", hover_color="#2A2A2A", text_color=TEXT_MUTED, corner_radius=6, command=self.show_help_dialog)
        self.help_btn.grid(row=2, column=0, padx=40, pady=(0, 25), sticky="w")

        self.import_btn = ctk.CTkButton(self.sidebar, text="导入视音频源文件", font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"), height=45, corner_radius=22, fg_color="#222222", hover_color="#333333", text_color=ACCENT_PRIMARY, command=self.import_video)
        self.import_btn.grid(row=3, column=0, padx=40, pady=(0, 5), sticky="ew")
        
        self.file_label = ctk.CTkLabel(self.sidebar, text="未选择任何媒体", font=ctk.CTkFont(family="Microsoft YaHei", size=11), text_color="#555555", wraplength=300, justify="left")
        self.file_label.grid(row=4, column=0, padx=45, pady=(0, 15), sticky="w")

        self.settings_group = ctk.CTkScrollableFrame(
            self.sidebar, fg_color=BG_GROUP, corner_radius=16, 
            scrollbar_button_color="#2A2A2A", scrollbar_button_hover_color="#444444"
        )
        self.settings_group.grid(row=5, column=0, padx=25, pady=(0, 15), sticky="nsew")
        self.settings_group.grid_columnconfigure(0, weight=1)
        
        row_idx = 0

        self._add_group_label(self.settings_group, "声学模型 (Acoustic)", row_idx); row_idx += 1
        self.opt_audio_type = ctk.CTkOptionMenu(self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=13), values=["Live 现场演唱 (常规/摇滚)", "Live 现场演唱 (极柔气声/清唱)", "访谈 / 电台播客"], fg_color="#222222", text_color=TEXT_TITLE, button_color="#222222", button_hover_color="#2A2A2A")
        self.opt_audio_type.set(self.settings.get("audio_type", "Live 现场演唱 (常规/摇滚)"))
        self.opt_audio_type.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
        self._add_group_divider(self.settings_group, row_idx); row_idx += 1

        self._add_group_label(self.settings_group, "分离策略 (Demucs)", row_idx); row_idx += 1
        self.opt_demucs = ctk.CTkOptionMenu(self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=13), values=["开启分离 (Live音乐必选)", "强制跳过 (极速/仅限无伴奏访谈)"], fg_color="#222222", text_color=TEXT_TITLE, button_color="#222222", button_hover_color="#2A2A2A")
        self.opt_demucs.set(self.settings.get("use_demucs", "开启分离 (Live音乐必选)"))
        self.opt_demucs.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
        self._add_group_divider(self.settings_group, row_idx); row_idx += 1

        self._add_group_label(self.settings_group, "引擎精度 (Whisper)", row_idx); row_idx += 1
        self.opt_model = ctk.CTkOptionMenu(self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=13), values=["large-v2 (战神级/推荐)", "large-v3-turbo (极速高精)", "large-v3", "medium (省显存)", "small", "base"], fg_color="#222222", text_color=TEXT_TITLE, button_color="#222222", button_hover_color="#2A2A2A")
        self.opt_model.set(self.settings.get("model_size", "large-v2 (战神级/推荐)"))
        self.opt_model.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
        self._add_group_divider(self.settings_group, row_idx); row_idx += 1

        self._add_group_label(self.settings_group, "大模型 API (智能路由 & 自定义)", row_idx); row_idx += 1
        self.opt_api_preset = ctk.CTkOptionMenu(self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=13), values=["SiliconFlow (DeepSeek-V3)", "Kimi (月之暗面)", "Google Gemini", "完全自定义"], command=self.on_api_preset_change, fg_color="#222222", text_color=TEXT_TITLE, button_color="#222222", button_hover_color="#2A2A2A")
        self.opt_api_preset.set(self.settings.get("api_preset", "SiliconFlow (DeepSeek-V3)"))
        self.opt_api_preset.grid(row=row_idx, column=0, padx=15, pady=(0, 15), sticky="ew"); row_idx += 1
        
        hint_font = ctk.CTkFont(family="Microsoft YaHei", size=11)
        
        self.lbl_url = ctk.CTkLabel(self.settings_group, text="Base URL (接口地址):", font=hint_font, text_color=TEXT_HINT)
        self.lbl_url.grid(row=row_idx, column=0, padx=20, pady=(0, 2), sticky="w"); row_idx += 1
        self.api_url_entry = ctk.CTkEntry(self.settings_group, font=ctk.CTkFont(family="Consolas", size=12), height=32, fg_color="#121212", text_color=TEXT_TITLE, border_width=0, corner_radius=8)
        self.api_url_entry.insert(0, self.settings.get("api_url", "https://api.siliconflow.cn/v1"))
        self.api_url_entry.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1

        self.lbl_model = ctk.CTkLabel(self.settings_group, text="Model ID (模型代号):", font=hint_font, text_color=TEXT_HINT)
        self.lbl_model.grid(row=row_idx, column=0, padx=20, pady=(0, 2), sticky="w"); row_idx += 1
        self.api_model_entry = ctk.CTkEntry(self.settings_group, font=ctk.CTkFont(family="Consolas", size=12), height=32, fg_color="#121212", text_color=TEXT_TITLE, border_width=0, corner_radius=8)
        self.api_model_entry.insert(0, self.settings.get("api_model", "deepseek-ai/DeepSeek-V3"))
        self.api_model_entry.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
        
        self.lbl_key = ctk.CTkLabel(self.settings_group, text="API Key (您的密钥):", font=hint_font, text_color=TEXT_HINT)
        self.lbl_key.grid(row=row_idx, column=0, padx=20, pady=(0, 2), sticky="w"); row_idx += 1
        self.api_key_entry = ctk.CTkEntry(self.settings_group, font=ctk.CTkFont(family="Consolas", size=12), show="*", height=32, fg_color="#121212", text_color=TEXT_TITLE, border_width=0, corner_radius=8)
        self.api_key_entry.insert(0, self.settings.get("api_key", ""))
        self.api_key_entry.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1

        self.proxy_entry = ctk.CTkEntry(self.settings_group, font=ctk.CTkFont(family="Consolas", size=12), placeholder_text="本地代理 (例如 http://127.0.0.1:10808) 留空直连", height=32, fg_color="#121212", text_color=TEXT_TITLE, border_width=0, corner_radius=8)
        self.proxy_entry.insert(0, self.settings.get("proxy_url", ""))
        self.proxy_entry.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
        self._add_group_divider(self.settings_group, row_idx); row_idx += 1

        self._add_group_label(self.settings_group, "排版模式 (Output)", row_idx); row_idx += 1
        self.opt_output_mode = ctk.CTkOptionMenu(self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=13), values=["中日双语字幕", "纯中文字幕"], fg_color="#222222", text_color=TEXT_TITLE, button_color="#222222", button_hover_color="#2A2A2A")
        self.opt_output_mode.set(self.settings.get("output_mode", "中日双语字幕"))
        self.opt_output_mode.grid(row=row_idx, column=0, padx=15, pady=(0, 15), sticky="ew"); row_idx += 1

        self.run_btn = ctk.CTkButton(self.sidebar, text="启动处理引擎", font=ctk.CTkFont(family="Microsoft YaHei", size=16, weight="bold"), height=55, corner_radius=27, text_color="#000000", fg_color=ACCENT_GREEN, hover_color="#1ED760", command=self.toggle_process)
        self.run_btn.grid(row=6, column=0, padx=40, pady=(5, 10), sticky="ew")

        self.progressbar = ctk.CTkProgressBar(self.sidebar, mode="determinate", height=4, fg_color="#252525", progress_color=ACCENT_GREEN, corner_radius=2)
        self.progressbar.grid(row=7, column=0, padx=60, pady=(0, 25), sticky="ew")
        self.progressbar.set(0) 

    def on_api_preset_change(self, choice):
        self.api_url_entry.delete(0, "end")
        self.api_model_entry.delete(0, "end")
        
        if "SiliconFlow" in choice:
            self.api_url_entry.insert(0, "https://api.siliconflow.cn/v1")
            self.api_model_entry.insert(0, "deepseek-ai/DeepSeek-V3")
        elif "Kimi" in choice:
            self.api_url_entry.insert(0, "https://api.moonshot.cn/v1")
            self.api_model_entry.insert(0, "moonshot-v1-32k")
        elif "Gemini" in choice:
            self.api_url_entry.insert(0, "https://generativelanguage.googleapis.com/v1beta/openai/")
            self.api_model_entry.insert(0, "gemini-2.5-flash")
        else:
            self.api_url_entry.insert(0, "")
            self.api_model_entry.insert(0, "")

    def _add_group_label(self, parent, text, row):
        label = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_MUTED)
        label.grid(row=row, column=0, padx=25, pady=(10, 5), sticky="w")

    def _add_group_divider(self, parent, row):
        divider = ctk.CTkFrame(parent, height=1, fg_color="#252525")
        divider.grid(row=row, column=0, padx=15, pady=(0, 5), sticky="ew")

    def _build_main_workspace(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=BG_WORKSPACE, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)

        self.header_label = ctk.CTkLabel(self.main_frame, text="Workspace", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=TEXT_TITLE)
        self.header_label.grid(row=0, column=0, padx=50, pady=(45, 20), sticky="w")

        self.lyrics_panel = ctk.CTkFrame(self.main_frame, fg_color=BG_CARD, corner_radius=16)
        self.lyrics_panel.grid(row=1, column=0, padx=50, pady=(0, 20), sticky="nsew")
        self.lyrics_panel.grid_columnconfigure(0, weight=1)
        self.lyrics_panel.grid_rowconfigure(1, weight=1)

        self.lyrics_label = ctk.CTkLabel(self.lyrics_panel, text="参考歌词库 Reference", font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"), text_color=TEXT_TITLE)
        self.lyrics_label.grid(row=0, column=0, padx=25, pady=(20, 10), sticky="w")
        
        self.lyrics_textbox = ctk.CTkTextbox(self.lyrics_panel, height=200, fg_color="#1A1A1A", text_color="#CCCCCC", border_width=0, font=ctk.CTkFont(family="Microsoft YaHei", size=14), corner_radius=10)
        self.lyrics_textbox.grid(row=1, column=0, padx=25, pady=(0, 25), sticky="nsew")
        
        default_placeholder = "【留空即为盲翻】\n请将网易云/QQ音乐的日文歌词粘贴于此...\n\nねぇ、もしも全て投げ捨てられたら\n笑って生きることが楽になるの？"
        saved_lyrics = self.settings.get("cached_lyrics", "")
        self.lyrics_textbox.insert("1.0", saved_lyrics if saved_lyrics else default_placeholder)

        self.console_panel = ctk.CTkFrame(self.main_frame, fg_color=BG_CARD, corner_radius=16)
        self.console_panel.grid(row=2, column=0, padx=50, pady=(0, 50), sticky="nsew")
        self.console_panel.grid_columnconfigure(0, weight=1)
        self.console_panel.grid_rowconfigure(1, weight=1)

        self.console_label = ctk.CTkLabel(self.console_panel, text="终端监控 Console", font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"), text_color=TEXT_TITLE)
        self.console_label.grid(row=0, column=0, padx=25, pady=(20, 10), sticky="w")
        
        self.console_textbox = ctk.CTkTextbox(self.console_panel, fg_color="#0A0A0A", border_width=0, text_color="#A0A0A0", font=ctk.CTkFont(family="Consolas", size=13), corner_radius=10)
        self.console_textbox.grid(row=1, column=0, padx=25, pady=(0, 25), sticky="nsew")
        self.console_textbox.configure(state="disabled")

    def import_video(self):
        file_path = filedialog.askopenfilename(title="选择视音频文件", filetypes=[("Media files", "*.mp4 *.mkv *.avi *.ts *.mp3 *.wav *.flac"), ("All files", "*.*")])
        if file_path:
            self.video_path = file_path
            self.file_label.configure(text=os.path.basename(file_path), text_color=ACCENT_PRIMARY)
            print(f"🎬 成功挂载输入源: {self.video_path}")

    def update_ui_status(self, progress_val, btn_text):
        self.progressbar.set(progress_val)
        self.run_btn.configure(text=btn_text)

    def toggle_process(self):
        if self.is_running:
            response = messagebox.askyesno(
                "终止任务", 
                "⚠️ 确定要终止当前任务吗？\n\n系统已升级【深层安全中断】机制，将立即切断底层的 AI 运算和显存占用，不再需要漫长等待！"
            )
            if response:
                self.cancel_event.set()
                self.run_btn.configure(text="🛑 正在强制切断底层进程...", state="disabled", fg_color="#222222", text_color="#888888")
            return

        if not self.video_path:
            messagebox.showwarning("警告", "请先在左侧导入媒体文件！")
            return
        
        self.save_all_ui_states()
        self.cancel_event.clear()

        raw_lyrics = self.lyrics_textbox.get("1.0", "end-1c").strip()
        lyrics_text = "" if "【留空即为盲翻】" in raw_lyrics else raw_lyrics
        trans_state_string = f"{lyrics_text}__{self.settings['output_mode']}__{self.settings['api_url']}__{self.settings['api_model']}"
        current_trans_hash = hashlib.md5(trans_state_string.encode('utf-8')).hexdigest()

        asr_state_string = f"{self.settings['audio_type']}__{self.settings['use_demucs']}__{self.settings['model_size']}"
        current_asr_hash = hashlib.md5(asr_state_string.encode('utf-8')).hexdigest()

        base_name = os.path.splitext(os.path.basename(self.video_path))[0]
        output_dir = os.path.abspath(os.path.join("output", base_name))
        expected_srt = os.path.join(output_dir, "subtitles", f"{base_name}_极致打轴.srt")
        trans_cache_file_path = os.path.join(output_dir, "subtitles", f"{base_name}_极致打轴_翻译缓存.json")
        trans_hash_file_path = os.path.join(output_dir, "subtitles", f"{base_name}_翻译指纹.hash")
        asr_hash_file_path = os.path.join(output_dir, "subtitles", f"{base_name}_打轴指纹.hash")
        
        skip_generator = False
        clear_cache = False
        
        if os.path.exists(expected_srt):
            saved_asr_hash = ""
            if os.path.exists(asr_hash_file_path):
                with open(asr_hash_file_path, "r", encoding="utf-8") as f:
                    saved_asr_hash = f.read().strip()
            
            if current_asr_hash != saved_asr_hash:
                messagebox.showinfo(
                    "🎙️ 引擎参数已变更", 
                    "侦测到您修改了【声学模型】或【分离策略/引擎精度】！\n\n系统将废弃旧的原文字幕，使用新参数重新提取打轴。\n\n💡 提示：若您仅修改了模型或精度，系统会自动复用之前分离好的人声文件，为您节省大量时间！"
                )
                print("\n🎙️ [智能管家] 侦测到打轴参数更改，准备重新生成原文字幕。")
                skip_generator = False
            else:
                response = messagebox.askyesno(
                    "安全断点续传 (阶段一)", 
                    f"发现已存在的原文字幕：\n{base_name}_极致打轴.srt\n\n您的打轴参数未发生改变，是否跳过漫长的人声分离与听写阶段，直接读取该文件进行大模型翻译？\n\n(选 '是' 极速直达翻译，选 '否' 将覆写并重新运行)"
                )
                if response: skip_generator = True

        if os.path.exists(trans_cache_file_path):
            saved_trans_hash = ""
            if os.path.exists(trans_hash_file_path):
                with open(trans_hash_file_path, "r", encoding="utf-8") as f:
                    saved_trans_hash = f.read().strip()
            
            if not skip_generator:
                print("   -> ⚠️ 侦测到原文字幕即将重新生成，旧翻译缓存已自动作废。")
                clear_cache = True
            elif current_trans_hash != saved_trans_hash:
                messagebox.showinfo(
                    "🧠 翻译配置已变更", 
                    "侦测到您修改了【参考歌词】或【接口/排版配置】！\n\n为防止采用旧缓存导致前后翻译格式错乱，系统已自动为您隔离了旧数据。\n\n本次将采用您的新配置进行全新翻译！"
                )
                print("\n🧠 [智能管家] 侦测到配置更改，旧翻译缓存已安全废弃，准备全新翻译。")
                clear_cache = True
            else:
                response = messagebox.askyesno(
                    "安全断点续传 (阶段二)", 
                    "检测到未完成的翻译缓存，且您的歌词与设置均未改变。\n\n是否继续上一次的翻译进度？\n\n(选 '是' 安全续传，选 '否' 清除重翻)"
                )
                if not response: clear_cache = True

        self.is_running = True
        self.run_btn.configure(text="⏹ 取 消 任 务", state="normal", fg_color=ACCENT_RED, hover_color=ACCENT_RED_HOVER, text_color="#FFFFFF")
        self.progressbar.set(0.0) 
        
        threading.Thread(target=self.run_core_pipeline, args=(skip_generator, clear_cache, current_trans_hash, current_asr_hash), daemon=True).start()

    def run_core_pipeline(self, skip_generator, clear_cache, current_trans_hash, current_asr_hash):
        try:
            self.after(0, self.update_ui_status, 0.05, "⏹ 取消任务 (引擎预热...)")
            
            audio_type_raw = self.opt_audio_type.get()
            if "访谈" in audio_type_raw:
                audio_type = "speech"
            elif "极柔气声" in audio_type_raw:
                audio_type = "live_soft"
            else:
                audio_type = "live"
                
            model_size = self.opt_model.get().split(" ")[0]
            
            base_url = self.api_url_entry.get().strip()
            p_model = self.api_model_entry.get().strip()
            
            api_key = self.api_key_entry.get().strip()
            proxy_url = self.proxy_entry.get().strip() 
            output_mode = "chinese_only" if "纯中文" in self.opt_output_mode.get() else "bilingual"
            
            force_skip_demucs = True if "强制跳过" in self.opt_demucs.get() else False
            skip_sep = True if audio_type == "speech" or force_skip_demucs else False
            
            raw_lyrics = self.lyrics_textbox.get("1.0", "end-1c").strip()
            lyrics_text = "" if "【留空即为盲翻】" in raw_lyrics else raw_lyrics

            print("\n" + "="*50)
            print(f"🚀 [任务总线启动] 目标文件: {os.path.basename(self.video_path)}")
            
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            output_dir = os.path.abspath(os.path.join("output", base_name))
            expected_srt = os.path.join(output_dir, "subtitles", f"{base_name}_极致打轴.srt")
            trans_hash_file_path = os.path.join(output_dir, "subtitles", f"{base_name}_翻译指纹.hash")
            asr_hash_file_path = os.path.join(output_dir, "subtitles", f"{base_name}_打轴指纹.hash")

            if self.cancel_event.is_set(): raise Exception("用户手动终止了任务")

            if skip_generator and os.path.exists(expected_srt):
                self.after(0, self.update_ui_status, 0.5, "⏹ 取消任务 (直达翻译...)")
                print(f"\n⏩ [断点续传] 用户选择跳过音频处理，直接使用本地字幕: {expected_srt}")
                srt_path = expected_srt
                with open(asr_hash_file_path, "w", encoding="utf-8") as f:
                    f.write(current_asr_hash)
            else:
                self.after(0, self.update_ui_status, 0.1, "⏹ 取消任务 (打轴中...)")
                generator = LiveSubtitleGenerator(video_path=self.video_path)
                srt_path = generator.run(model_size=model_size, audio_type=audio_type, skip_separation=skip_sep, cancel_event=self.cancel_event)
                if not srt_path: raise Exception("打轴阶段未能返回有效的 SRT 路径。")
                
                with open(asr_hash_file_path, "w", encoding="utf-8") as f:
                    f.write(current_asr_hash)

            if self.cancel_event.is_set(): raise Exception("用户手动终止了任务")

            if clear_cache:
                cache_file_path = os.path.join(output_dir, "subtitles", f"{base_name}_极致打轴_翻译缓存.json")
                if os.path.exists(cache_file_path):
                    os.remove(cache_file_path)
                if os.path.exists(trans_hash_file_path):
                    os.remove(trans_hash_file_path)
                print("   -> 🗑️ 旧缓存及指纹已清除，准备全新翻译。")

            if api_key:
                self.after(0, self.update_ui_status, 0.6, "⏹ 取消任务 (AI翻译中...)")
                
                print(f"\n🌍 [大模型矩阵启动] 开始执行听译与纠错排版...")
                print(f"   -> 🌐 目标接口: {base_url}")
                print(f"   -> 🧠 加载模型: {p_model}")
                
                r_model = p_model 
                if "gemini-2.5-flash" in p_model:
                    r_model = "gemini-2.5-pro"
                elif "DeepSeek-V3" in p_model:
                    r_model = "deepseek-ai/DeepSeek-R1"

                temp_lyrics_path = os.path.join(output_dir, "temp_lyrics_gui.txt")
                with open(temp_lyrics_path, "w", encoding="utf-8") as f: 
                    f.write(lyrics_text)

                translator = SubtitleTranslator(
                    api_key=api_key, 
                    base_url=base_url, 
                    primary_model=p_model, 
                    reasoning_model=r_model,
                    srt_path=srt_path, 
                    reference_txt_path=temp_lyrics_path, 
                    output_mode=output_mode,
                    proxy_url=proxy_url 
                )
                final_srt = translator.run(cancel_event=self.cancel_event)
                
                if os.path.exists(temp_lyrics_path): 
                    os.remove(temp_lyrics_path) 
                
                if final_srt: 
                    print(f"\n🎉 最终字幕位置: {final_srt}")
                    with open(trans_hash_file_path, "w", encoding="utf-8") as f:
                        f.write(current_trans_hash)
            else:
                self.after(0, self.update_ui_status, 0.6, "⚠️ 未检测到 Key, 翻译跳过...")
                print("\n⚠️ 未检测到 API Key，跳过大模型翻译。")

            if self.cancel_event.is_set(): raise Exception("用户手动终止了任务")

            self.after(0, self.update_ui_status, 1.0, "🎉 处 理 完 成 ！")
            self.after(0, lambda: self.run_btn.configure(fg_color=ACCENT_GREEN, hover_color="#1ED760"))
            time.sleep(1.5) 

        except Exception as e:
            if "用户中断" in str(e):
                print(f"\n🛑 任务已由用户手动终止。")
                self.after(0, self.update_ui_status, 0.0, "🛑 任 务 已 中 止")
            else:
                print(f"\n❌ 任务异常终止: {str(e)}")
                self.after(0, self.update_ui_status, 0.0, "❌ 任 务 异 常 终 止")
            time.sleep(2)
        finally:
            self.is_running = False
            
            # 🌟 终极防闪退补丁 2：在线程彻底死亡前，强行清空所有遗留内存
            gc.collect()
            
            self.after(0, lambda: self.run_btn.configure(text="启动处理引擎", state="normal", fg_color=ACCENT_GREEN, hover_color="#1ED760", text_color="#000000"))
            self.after(0, lambda: self.progressbar.set(0.0))

if __name__ == "__main__":
    app = UtaSyncApp()
    app.mainloop()