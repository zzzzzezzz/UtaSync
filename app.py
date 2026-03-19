import os
import sys
import json
import time
import threading
import hashlib
import queue 
import gc
import copy
import subprocess  
import shutil      
import webbrowser  
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from core.generator import LiveSubtitleGenerator
    from core.translator import SubtitleTranslator
    from core.ass_maker import ASSMaker, ASS_PRESETS 
except ImportError as e:
    print(f"⚠️ 核心引擎导入失败: {e}\n请确保 app.py 与 core 文件夹在同一级目录下。")
    ASS_PRESETS = {} 

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
        "hardware_mode": "极限防爆 (4G~6G显存/默认)",
        "ass_preset": "默认双语 (纯白+浅灰)", 
        "ch_font_override": "跟随预设",
        "jp_font_override": "跟随预设",
        "ch_size_override": "跟随预设",  
        "jp_size_override": "跟随预设",  
        "fade_mode": "智能动态呼吸 (默认/推荐)", 
        "hires_export": False, 
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
            "hardware_mode": self.opt_hardware.get(),
            "ass_preset": getattr(self, "opt_ass_preset", ctk.StringVar(value="默认双语 (纯白+浅灰)")).get(), 
            "ch_font_override": getattr(self, "opt_ch_font", ctk.StringVar(value="跟随预设")).get(),
            "jp_font_override": getattr(self, "opt_jp_font", ctk.StringVar(value="跟随预设")).get(),
            "ch_size_override": getattr(self, "opt_ch_size", ctk.StringVar(value="跟随预设")).get(), 
            "jp_size_override": getattr(self, "opt_jp_size", ctk.StringVar(value="跟随预设")).get(), 
            "fade_mode": getattr(self, "opt_fade_mode", ctk.StringVar(value="智能动态呼吸 (默认/推荐)")).get(),
            "hires_export": getattr(self, "check_hires", ctk.IntVar(value=0)).get() == 1,
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
        help_window.geometry("680x850")
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

【⚡ 算力调度 (Hardware)】
• 极限防爆 (4G~6G显存)：强制 60 秒极细微切片并物理锁死显存峰值。速度最慢但绝不闪退，低配救星！
• 均衡提速 (8G显存)：180 秒标准切片，适当放宽显存限制，速度与稳定性的完美平衡，适合主流游戏本。
• 满血狂飙 (12G+显存)：解除所有封印！整段音频直接塞进显卡进行极限并发，速度极快。

【🎨 特效字幕 (ASS Export) 与硬字幕压制】
• 系统内置了多款低饱和度、高质感的双语排版风格，自带剪映级的【丝滑淡入淡出动画】。
• 💡【神级排版】：支持独立修改中文/日文的字体和字号！可直接输入数字微调比例。
• 💡【出场动画】：支持智能呼吸与全局硬切，保护视力防闪瞎！
• 💡【微调绝技】：需要修改错别字时，用记事本打开 `_双语字幕.srt` 修改并保存，然后点击软件中的【一键重绘花字】，0.1秒即可套上新皮肤！
• 🎬【终极压制】：压制出来的视频自带高级字体与呼吸描边特效，且支持开启 B 站 Hi-Res 专属优化！

【🌍 大模型 API (翻译阶段)】
• 推荐主力：SiliconFlow (硅基流动)。采用 DeepSeek-V3 作为主力，国内直连无网络障碍。
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

        self._add_group_label(self.settings_group, "算力调度 (Hardware)", row_idx); row_idx += 1
        self.opt_hardware = ctk.CTkOptionMenu(self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=13), values=["极限防爆 (4G~6G显存/默认)", "均衡提速 (8G显存)", "满血狂飙 (12G+显存)"], fg_color="#222222", text_color=TEXT_TITLE, button_color="#222222", button_hover_color="#2A2A2A")
        self.opt_hardware.set(self.settings.get("hardware_mode", "极限防爆 (4G~6G显存/默认)"))
        self.opt_hardware.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
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

        self._add_group_label(self.settings_group, "特效字幕 (ASS Export)", row_idx); row_idx += 1
        ass_options = ["不生成 (仅SRT)"] + list(ASS_PRESETS.keys())
        self.opt_ass_preset = ctk.CTkOptionMenu(self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=13), values=ass_options, fg_color="#18181B", text_color=TEXT_TITLE, button_color="#27272A", button_hover_color="#3F3F46")
        self.opt_ass_preset.set(self.settings.get("ass_preset", "默认双语 (纯白+浅灰)"))
        self.opt_ass_preset.grid(row=row_idx, column=0, padx=15, pady=(0, 5), sticky="ew"); row_idx += 1
        
        try:
            from tkinter import font as tkfont
            all_fonts = list(tkfont.families())
            valid_fonts = sorted([f for f in all_fonts if not f.startswith('@')])
        except:
            valid_fonts = ["Microsoft YaHei", "Meiryo", "Yu Gothic", "Yu Mincho", "SimHei"]
            
        priority_fonts = ["跟随预设", "Microsoft YaHei", "Yu Gothic", "Meiryo", "Yu Mincho", "SimHei", "楷体", "Source Han Sans CN", "Source Han Sans JP"]
        font_options = priority_fonts + [f for f in valid_fonts if f not in priority_fonts]

        font_lbl_frame = ctk.CTkFrame(self.settings_group, fg_color="transparent")
        font_lbl_frame.grid(row=row_idx, column=0, padx=15, pady=(0, 2), sticky="ew"); row_idx += 1
        font_lbl_frame.grid_columnconfigure(0, weight=1)
        font_lbl_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(font_lbl_frame, text="主字体 (中文)", font=ctk.CTkFont(size=11), text_color=TEXT_HINT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(font_lbl_frame, text="副字体 (日文) 推荐 Yu Gothic", font=ctk.CTkFont(size=11), text_color=TEXT_HINT).grid(row=0, column=1, sticky="w", padx=(5,0))

        font_sel_frame = ctk.CTkFrame(self.settings_group, fg_color="transparent")
        font_sel_frame.grid(row=row_idx, column=0, padx=15, pady=(0, 5), sticky="ew"); row_idx += 1
        font_sel_frame.grid_columnconfigure(0, weight=1)
        font_sel_frame.grid_columnconfigure(1, weight=1)

        self.opt_ch_font = ctk.CTkComboBox(font_sel_frame, font=ctk.CTkFont(family="Microsoft YaHei", size=12), values=font_options, fg_color="#18181B", button_color="#27272A", dropdown_font=ctk.CTkFont(family="Microsoft YaHei", size=12))
        self.opt_ch_font.set(self.settings.get("ch_font_override", "跟随预设"))
        self.opt_ch_font.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.opt_jp_font = ctk.CTkComboBox(font_sel_frame, font=ctk.CTkFont(family="Microsoft YaHei", size=12), values=font_options, fg_color="#18181B", button_color="#27272A", dropdown_font=ctk.CTkFont(family="Microsoft YaHei", size=12))
        self.opt_jp_font.set(self.settings.get("jp_font_override", "跟随预设"))
        self.opt_jp_font.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        size_lbl_frame = ctk.CTkFrame(self.settings_group, fg_color="transparent")
        size_lbl_frame.grid(row=row_idx, column=0, padx=15, pady=(0, 2), sticky="ew"); row_idx += 1
        size_lbl_frame.grid_columnconfigure(0, weight=1)
        size_lbl_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(size_lbl_frame, text="主字号 (中文大小)", font=ctk.CTkFont(size=11), text_color=TEXT_HINT).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(size_lbl_frame, text="副字号 (日文大小)", font=ctk.CTkFont(size=11), text_color=TEXT_HINT).grid(row=0, column=1, sticky="w", padx=(5,0))

        size_options = ["跟随预设", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80", "90"]
        size_sel_frame = ctk.CTkFrame(self.settings_group, fg_color="transparent")
        size_sel_frame.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
        size_sel_frame.grid_columnconfigure(0, weight=1)
        size_sel_frame.grid_columnconfigure(1, weight=1)

        self.opt_ch_size = ctk.CTkComboBox(size_sel_frame, font=ctk.CTkFont(family="Consolas", size=12), values=size_options, fg_color="#18181B", button_color="#27272A", dropdown_font=ctk.CTkFont(family="Consolas", size=12))
        self.opt_ch_size.set(self.settings.get("ch_size_override", "跟随预设"))
        self.opt_ch_size.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.opt_jp_size = ctk.CTkComboBox(size_sel_frame, font=ctk.CTkFont(family="Consolas", size=12), values=size_options, fg_color="#18181B", button_color="#27272A", dropdown_font=ctk.CTkFont(family="Consolas", size=12))
        self.opt_jp_size.set(self.settings.get("jp_size_override", "跟随预设"))
        self.opt_jp_size.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        fade_lbl_frame = ctk.CTkFrame(self.settings_group, fg_color="transparent")
        fade_lbl_frame.grid(row=row_idx, column=0, padx=15, pady=(0, 2), sticky="ew"); row_idx += 1
        ctk.CTkLabel(fade_lbl_frame, text="字幕出场动画 (防疲劳控制)", font=ctk.CTkFont(size=11), text_color=TEXT_HINT).pack(side="left")

        self.opt_fade_mode = ctk.CTkOptionMenu(
            self.settings_group, font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            values=["智能动态呼吸 (默认/推荐)", "全局硬切无延时 (极速弹出)", "强制全局淡入淡出 (旧版)"],
            fg_color="#18181B", button_color="#27272A", dropdown_font=ctk.CTkFont(family="Microsoft YaHei", size=12)
        )
        self.opt_fade_mode.set(self.settings.get("fade_mode", "智能动态呼吸 (默认/推荐)"))
        self.opt_fade_mode.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1

        ass_btn_frame = ctk.CTkFrame(self.settings_group, fg_color="transparent")
        ass_btn_frame.grid(row=row_idx, column=0, padx=15, pady=(0, 5), sticky="ew"); row_idx += 1
        
        self.btn_preview_ass = ctk.CTkButton(ass_btn_frame, text="👁️ 浏览器极速预览", font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"), height=30, fg_color="#3F3F46", hover_color="#52525B", command=self.preview_ass_style)
        self.btn_preview_ass.pack(fill="x", pady=(0, 6))
        
        self.btn_redraw_ass = ctk.CTkButton(ass_btn_frame, text="🔄 一键重绘成片", font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"), height=30, fg_color="#2A2A2A", hover_color="#3F3F46", text_color="#AAAAAA", command=self.quick_redraw_ass)
        self.btn_redraw_ass.pack(fill="x")
        
        self.check_hires = ctk.CTkSwitch(
            self.settings_group, text="开启 B站 Hi-Res 无损直出 (.mkv)",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"),
            text_color=ACCENT_GREEN, progress_color=ACCENT_GREEN
        )
        if self.settings.get("hires_export", False):
            self.check_hires.select()
        self.check_hires.grid(row=row_idx, column=0, padx=15, pady=(15, 10), sticky="w"); row_idx += 1

        self.btn_burn_video = ctk.CTkButton(self.settings_group, text="🎬 将花字压制入原视频 (硬字幕)", font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"), height=32, fg_color="#1E3A8A", hover_color="#0284C7", text_color="#FFFFFF", command=self.quick_burn_video)
        self.btn_burn_video.grid(row=row_idx, column=0, padx=15, pady=(0, 10), sticky="ew"); row_idx += 1
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

    def preview_ass_style(self):
        ass_choice = getattr(self, "opt_ass_preset", ctk.StringVar(value="不生成 (仅SRT)")).get()
        if ass_choice == "不生成 (仅SRT)":
            messagebox.showinfo("提示", "请在下拉菜单中选择一个花字预设！")
            return
            
        base_config = ASS_PRESETS.get(ass_choice, ASS_PRESETS.get("默认双语 (纯白+浅灰)"))
        config = copy.deepcopy(base_config)
        
        if self.opt_ch_font.get() != "跟随预设":
            config["ch_font"] = self.opt_ch_font.get()
        if self.opt_jp_font.get() != "跟随预设":
            config["jp_font"] = self.opt_jp_font.get()
            
        if self.opt_ch_size.get() != "跟随预设":
            try: config["ch_size"] = int(self.opt_ch_size.get())
            except: pass
        if self.opt_jp_size.get() != "跟随预设":
            try: config["jp_size"] = int(self.opt_jp_size.get())
            except: pass

        config["fade_mode"] = getattr(self, "opt_fade_mode", ctk.StringVar(value="智能动态呼吸 (默认/推荐)")).get()
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>{ass_choice} - 样式预览</title>
            <style>
                body {{
                    background-color: #121212;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    color: white;
                    font-family: sans-serif;
                }}
                .stage {{
                    width: 800px;
                    height: 450px;
                    background: linear-gradient(135deg, #1f1c2c 0%, #928dab 100%);
                    border-radius: 12px;
                    display: flex;
                    flex-direction: column;
                    justify-content: flex-end;
                    padding-bottom: 40px;
                    align-items: center;
                    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
                    position: relative;
                    overflow: hidden;
                }}
                .stage::after {{
                    content: "";
                    position: absolute;
                    top: 0; left: 0; right: 0; bottom: 0;
                    background: radial-gradient(circle at 50% 0%, rgba(255,255,255,0.05), transparent 60%);
                }}
                .subtitle-container {{
                    text-align: center;
                    animation: fadeEffect 4s ease-in-out infinite;
                }}
                @keyframes fadeEffect {{
                    0% {{ opacity: 0; }}
                    15% {{ opacity: 1; }}
                    85% {{ opacity: 1; }}
                    100% {{ opacity: 0; }}
                }}
                .ch-text {{
                    font-family: "{config.get('ch_font', 'Microsoft YaHei')}", sans-serif;
                    font-size: {config.get('ch_size', 55)}px;
                    color: {config.get('ch_color', '#FFFFFF')};
                    -webkit-text-stroke: {config.get('outline_size', 3)}px {config.get('outline_color', '#000000')};
                    text-shadow: {config.get('shadow_size', 2)}px {config.get('shadow_size', 2)}px 0px {config.get('outline_color', '#000000')};
                    font-weight: bold;
                    margin-bottom: 10px;
                    z-index: 10;
                }}
                .jp-text {{
                    font-family: "{config.get('jp_font', 'Meiryo')}", sans-serif;
                    font-size: {config.get('jp_size', 35)}px;
                    color: {config.get('jp_color', '#CCCCCC')};
                    -webkit-text-stroke: {config.get('outline_size', 3)}px {config.get('outline_color', '#000000')};
                    text-shadow: {config.get('shadow_size', 2)}px {config.get('shadow_size', 2)}px 0px {config.get('outline_color', '#000000')};
                    font-weight: normal;
                    z-index: 10;
                }}
                .info {{
                    margin-top: 30px;
                    color: #888;
                }}
            </style>
        </head>
        <body>
            <div class="stage">
                <div class="subtitle-container">
                    <div class="ch-text">在这光芒万丈的舞台上</div>
                    <div class="jp-text">この光り輝くステージの上で</div>
                </div>
            </div>
            <div class="info">💡 中文字号: {config.get('ch_size')}px | 日文字号: {config.get('jp_size')}px</div>
        </body>
        </html>
        """
        try:
            preview_path = os.path.abspath("temp_style_preview.html")
            with open(preview_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            webbrowser.open(f"file://{preview_path}")
        except Exception as e:
            messagebox.showerror("错误", f"预览生成失败: {e}")

    def quick_redraw_ass(self):
        if not self.video_path:
            messagebox.showwarning("提示", "请先在左侧导入您刚才处理过的媒体文件！")
            return

        base_name = os.path.splitext(os.path.basename(self.video_path))[0]
        output_dir = os.path.abspath(os.path.join("output", base_name, "subtitles"))

        target_srt = None
        for suffix in ["_极致打轴_双语字幕.srt", "_极致打轴_纯中文字幕.srt", "_极致打轴.srt"]:
            potential_path = os.path.join(output_dir, f"{base_name}{suffix}")
            if os.path.exists(potential_path):
                target_srt = potential_path
                break

        if not target_srt:
            messagebox.showwarning("提示", "未找到任何已生成的 SRT 字幕！\n请确认您已经完整运行过一次字幕生成流程。")
            return

        ass_choice = getattr(self, "opt_ass_preset", ctk.StringVar(value="不生成 (仅SRT)")).get()
        if ass_choice == "不生成 (仅SRT)":
            messagebox.showinfo("提示", "请先在上方下拉菜单中选择一个花字预设风格！")
            return

        try:
            base_config = ASS_PRESETS.get(ass_choice, ASS_PRESETS.get("默认双语 (纯白+浅灰)"))
            config = copy.deepcopy(base_config)
            
            if self.opt_ch_font.get() != "跟随预设":
                config["ch_font"] = self.opt_ch_font.get()
            if self.opt_jp_font.get() != "跟随预设":
                config["jp_font"] = self.opt_jp_font.get()
                
            if self.opt_ch_size.get() != "跟随预设":
                try: config["ch_size"] = int(self.opt_ch_size.get())
                except: pass
            if self.opt_jp_size.get() != "跟随预设":
                try: config["jp_size"] = int(self.opt_jp_size.get())
                except: pass

            config["fade_mode"] = getattr(self, "opt_fade_mode", ctk.StringVar(value="智能动态呼吸 (默认/推荐)")).get()

            print(f"\n⚡ [极速重绘] 正在读取修改后的文本: {os.path.basename(target_srt)}")
            maker = ASSMaker(target_srt)
            ass_path = maker.generate_ass(config)
            messagebox.showinfo("重绘成功", f"🎉 花字皮肤已秒换！\n\n新特效已覆盖保存:\n{os.path.basename(ass_path)}\n\n💡 提示: 请直接将其拖入播放器中查看效果，或点击下方的【压制视频】生成带字成片！")
        except Exception as e:
            messagebox.showerror("错误", f"重绘失败: {e}")

    def quick_burn_video(self):
        if self.is_running:
            messagebox.showwarning("提示", "当前有任务正在运行，请稍后再试！")
            return
            
        if not self.video_path:
            messagebox.showwarning("提示", "请先在左侧导入原视频文件！")
            return

        base_name = os.path.splitext(os.path.basename(self.video_path))[0]
        output_dir = os.path.abspath(os.path.join("output", base_name))
        
        potential_ass = None
        for suffix in ["_极致打轴_双语字幕_顶级特效.ass", "_极致打轴_纯中文字幕_顶级特效.ass", "_极致打轴_顶级特效.ass"]:
            test_path = os.path.join(output_dir, "subtitles", f"{base_name}{suffix}")
            if os.path.exists(test_path):
                potential_ass = test_path
                break

        if not potential_ass:
            messagebox.showwarning("提示", "未找到特效字幕 (.ass)！\n请先确认在上方菜单选择了预设，并已生成或重绘字幕。")
            return

        response = messagebox.askyesno("开始压制", f"即将调用 FFmpeg 将顶级花字硬核刻录到视频画面中！\n\n压制时长取决于您的电脑 CPU/GPU 性能。\n由于这是底层硬编码，期间请耐心等待，确定要开始压制吗？")
        if not response:
            return

        hires_enabled = getattr(self, "check_hires", ctk.IntVar(value=0)).get() == 1

        self.is_running = True
        self.run_btn.configure(text="🛑 正在强制切断压制进程...", state="normal", fg_color=ACCENT_RED, text_color="#FFFFFF")
        self.update_ui_status(0.5, "⏹ 取消任务 (视频压制中...)")
        self.cancel_event.clear()
        
        threading.Thread(target=self._run_burn_video, args=(potential_ass, hires_enabled), daemon=True).start()

    def _run_burn_video(self, target_ass, hires_enabled=False):
        try:
            print("\n" + "="*50)
            print(" 🎬 [压制引擎启动] 开始将特效花字永久刻录至视频画面...")
            print("="*50)
            
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            output_dir = os.path.abspath(os.path.join("output", base_name))
            
            if hires_enabled:
                final_video = os.path.join(output_dir, f"{base_name}_成品带字版_HiRes.mkv")
                audio_args = ["-c:a", "flac", "-sample_fmt", "s32", "-ar", "48000"]
                print("   -> 🎧 [Hi-Res 模式已开启] 强制封装为 MKV + 32-bit FLAC 无损音频！")
            else:
                final_video = os.path.join(output_dir, f"{base_name}_成品带字版.mp4")
                audio_args = ["-c:a", "copy"]
            
            temp_ass_name = "temp_burn_subtitles.ass"
            temp_ass_path = os.path.join(output_dir, temp_ass_name)
            shutil.copy(target_ass, temp_ass_path)
            
            # 🌟 全平台硬件加速策略 (智能级联回退)
            hardware_encoders = [
                {"name": "NVIDIA 显卡 (NVENC)", "vcodec": "h264_nvenc", "args": ["-preset", "p4", "-cq", "22"]},
                {"name": "Apple Mac (VideoToolbox)", "vcodec": "h264_videotoolbox", "args": ["-q:v", "50"]},
                {"name": "Intel 核显 (QSV)", "vcodec": "h264_qsv", "args": ["-preset", "fast", "-global_quality", "22"]},
                {"name": "AMD 显卡 (AMF)", "vcodec": "h264_amf", "args": ["-quality", "speed", "-rc", "vbr", "-qp_i", "22"]},
                {"name": "CPU 安全软压 (兼容兜底)", "vcodec": "libx264", "args": ["-preset", "superfast", "-crf", "22", "-threads", "4"]}
            ]
            
            start_time = time.time()
            success = False
            
            # 🌟 核心升级：系统级智能调度 (Background Priority)
            # 告诉系统这是一个后台任务，如果用户开游戏，自动让出 CPU/GPU 资源
            popen_kwargs = {
                "cwd": output_dir,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.PIPE,
                "text": True,
                "encoding": "utf-8",
                "errors": "ignore"
            }
            # 如果是 Windows 系统，设置底层进程优先级为“低于正常 (BELOW_NORMAL)”
            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.BELOW_NORMAL_PRIORITY_CLASS
            
            for enc in hardware_encoders:
                print(f"   -> 🚀 [智能调度] 尝试使用 {enc['name']} 引擎压制...")
                cmd = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", self.video_path,
                    "-vf", f"subtitles={temp_ass_name}",
                    "-c:v", enc["vcodec"]
                ] + enc["args"] + audio_args + [final_video]

                # 携带低优先级调度指令启动 FFmpeg
                process = subprocess.Popen(cmd, **popen_kwargs)
                
                last_heartbeat = time.time()
                
                while process.poll() is None:
                    if self.cancel_event.is_set():
                        process.kill()
                        process.wait()
                        raise Exception("用户手动终止了压制任务")
                    
                    time.sleep(0.5) 
                    
                    current_time = time.time()
                    if current_time - last_heartbeat >= 10:
                        elapsed = int(current_time - start_time)
                        print(f"   -> ⏳ [{enc['name']} 刻录心跳] 画面合成中... (已耗时 {elapsed} 秒)")
                        last_heartbeat = current_time
                        
                if process.returncode == 0:
                    success = True
                    print(f"   -> ✅ {enc['name']} 引擎压制成功！")
                    break
                else:
                    _, stderr_data = process.communicate()
                    if "Cancel" in stderr_data or self.cancel_event.is_set():
                        raise Exception("用户手动终止了压制任务")
                    print(f"   -> ⚠️ {enc['name']} 不受支持或初始化失败。准备降级...")
            
            if not success:
                raise Exception("所有硬件加速及 CPU 软压均失败，请检查 FFmpeg 环境。")

            elapsed_total = int(time.time() - start_time)
            print(f"\n🎉 压制大功告成！(总耗时: {elapsed_total} 秒)")
            print(f"📁 您的【最终成品视频】已安全保存在:\n{final_video}")
                
            if os.path.exists(temp_ass_path):
                os.remove(temp_ass_path)
                
            self.after(0, self.update_ui_status, 1.0, "🎉 压 制 完 成 ！")
            self.after(0, lambda: self.run_btn.configure(fg_color=ACCENT_GREEN, hover_color="#1ED760"))
            
        except Exception as e:
            if "用户手动终止" in str(e):
                print(f"\n🛑 压制已终止。")
                self.after(0, self.update_ui_status, 0.0, "🛑 压 制 已 中 止")
            else:
                print(f"\n❌ 压制异常终止: {e}")
                self.after(0, self.update_ui_status, 0.0, "❌ 压 制 异 常 终 止")
        finally:
            self.is_running = False
            self.after(0, lambda: self.run_btn.configure(text="启动处理引擎", state="normal", fg_color=ACCENT_GREEN, hover_color="#1ED760", text_color="#000000"))
            self.after(0, lambda: self.progressbar.set(0.0))

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
            
            hw_mode_raw = self.opt_hardware.get()
            if "均衡" in hw_mode_raw:
                hw_mode = "medium"
            elif "满血" in hw_mode_raw:
                hw_mode = "high"
            else:
                hw_mode = "low"
            
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
                srt_path = generator.run(model_size=model_size, audio_type=audio_type, skip_separation=skip_sep, hardware_mode=hw_mode, cancel_event=self.cancel_event)
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

            final_srt = None
            if api_key:
                self.after(0, self.update_ui_status, 0.6, "⏹ 取消任务 (AI翻译中...)")
                
                print(f"\n🌍 [大模型矩阵启动] 开始执行听译与纠错排版...")
                
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
                final_srt = srt_path 

            if self.cancel_event.is_set(): raise Exception("用户手动终止了任务")

            if final_srt:
                ass_choice = getattr(self, "opt_ass_preset", ctk.StringVar(value="不生成 (仅SRT)")).get()
                if ass_choice != "不生成 (仅SRT)":
                    self.after(0, self.update_ui_status, 0.9, "⏹ 取消任务 (生成花字...)")
                    try:
                        base_config = ASS_PRESETS.get(ass_choice, ASS_PRESETS.get("默认双语 (纯白+浅灰)"))
                        config = copy.deepcopy(base_config)
                        
                        ch_override = getattr(self, "opt_ch_font", ctk.StringVar(value="跟随预设")).get()
                        if ch_override != "跟随预设":
                            config["ch_font"] = ch_override
                            
                        jp_override = getattr(self, "opt_jp_font", ctk.StringVar(value="跟随预设")).get()
                        if jp_override != "跟随预设":
                            config["jp_font"] = jp_override
                            
                        ch_size_override = getattr(self, "opt_ch_size", ctk.StringVar(value="跟随预设")).get()
                        if ch_size_override != "跟随预设":
                            try: config["ch_size"] = int(ch_size_override)
                            except: pass
                            
                        jp_size_override = getattr(self, "opt_jp_size", ctk.StringVar(value="跟随预设")).get()
                        if jp_size_override != "跟随预设":
                            try: config["jp_size"] = int(jp_size_override)
                            except: pass
                            
                        config["fade_mode"] = getattr(self, "opt_fade_mode", ctk.StringVar(value="智能动态呼吸 (默认/推荐)")).get()

                        maker = ASSMaker(final_srt)
                        ass_path = maker.generate_ass(config)
                    except Exception as e:
                        print(f"\n❌ ASS 特效字幕生成失败: {e}")

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
            gc.collect()
            
            self.after(0, lambda: self.run_btn.configure(text="启动处理引擎", state="normal", fg_color=ACCENT_GREEN, hover_color="#1ED760", text_color="#000000"))
            self.after(0, lambda: self.progressbar.set(0.0))

if __name__ == "__main__":
    app = UtaSyncApp()
    app.mainloop()