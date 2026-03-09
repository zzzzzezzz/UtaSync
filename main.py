import os
import time
import subprocess
from core.generator import LiveSubtitleGenerator
from core.translator import SubtitleTranslator

# ==========================================
# ⚙️ 大模型 API 配置区 (支持智能路由双模型)
# ==========================================
API_CONFIGS = {
    "1": {
        "name": "硅基流动 (SiliconFlow) - 智能路由 (V3主力 + R1盲翻)",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "YOUR_API_KEY", 
        "primary_model": "deepseek-ai/DeepSeek-V3",     
        "reasoning_model": "deepseek-ai/DeepSeek-R1"    
    },
    "2": {
        "name": "Google Gemini (智能路由版)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": "YOUR_API_KEY",
        "primary_model": "gemini-2.5-flash",            
        "reasoning_model": "gemini-2.5-pro"             
    }
}
# ==========================================

def get_video_duration(video_path):
    """瞬间读取视频原时长，用于最终性能评级"""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def main():
    print("="*50)
    print(" 🎶 欢迎使用 UtaSync V1.9.2 - 内存防爆版 🎶")
    print("="*50)
    
    video_path = input("👉 请输入视频的完整路径: ").strip()
    
    if video_path.startswith('"') and video_path.endswith('"'):
        video_path = video_path[1:-1]
        
    if not os.path.exists(video_path):
        print("❌ 错误: 找不到视频文件，请检查路径是否正确。")
        return

    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.abspath(os.path.join("output", base_name))
    expected_srt = os.path.join(output_dir, "subtitles", f"{base_name}_极致打轴.srt")
    time_log_path = os.path.join(output_dir, "打轴耗时记录.txt")
    
    srt_path = None
    whisper_time = 0.0
    translation_time = 0.0
    
    if os.path.exists(expected_srt):
        print(f"\n📦 检测到已打好的字幕文件: {expected_srt}")
        skip = input("👉 是否跳过漫长的打轴，直接读取该文件进行翻译？(y/n) [默认 y, 直接回车]: ").strip().lower()
        if skip != 'n':
            srt_path = expected_srt
            print("   -> ✅ 进度已恢复，直达大模型翻译阶段！")
            if os.path.exists(time_log_path):
                try:
                    with open(time_log_path, "r", encoding="utf-8") as f:
                        whisper_time = float(f.read().strip())
                except:
                    pass
    
    if not srt_path:
        print("\n🎬 请选择视频类型：")
        print("   1. Live 现场演唱 (高容忍, 快歌1秒防漂移)")
        print("   2. 访谈 / 谈话节目 (高频断句, 5秒防霸屏)")
        type_choice = input("👉 请输入序号 (默认 1): ").strip()
        audio_type = "speech" if type_choice == "2" else "live"

        # 🌟 核心防爆内存逻辑：按需跳过 Demucs
        skip_separation = False
        if audio_type == "speech":
            print("\n💡 检测到您选择了【访谈/电台模式】。")
            skip_choice = input("👉 是否跳过 Demucs 人声分离？\n   (强烈建议选 y！电台通常无吵闹伴奏，跳过可防内存崩溃且速度提升10倍) [y/n] 默认 y: ").strip().lower()
            if skip_choice != 'n':
                skip_separation = True
        else:
            print("\n💡 内存预警：2小时以上的 Live 分离需要极大的电脑运行内存 (16G+)。")
            skip_choice = input("👉 如果您的电脑内存较小，是否强行跳过人声分离？[y/n] 默认 n: ").strip().lower()
            if skip_choice == 'y':
                skip_separation = True

        print("\n🧠 请选择 Whisper 模型 (💡 提示: 最新不一定最适合)：")
        print("   1. medium   (日常速度，省显存)")
        print("   2. large-v2 (🏆 强烈推荐！日音 Live 最强战神，抗噪防幻觉)")
        print("   3. large-v3 (最新模型，极度敏感，适合无背景音的纯访谈)")
        model_choice = input("👉 请输入序号 (默认 2): ").strip()
        model_map = {"1": "medium", "2": "large-v2", "3": "large-v3"}
        selected_model = model_map.get(model_choice, "large-v2") 
        
        print(f"\n⚠️ 提示：如果您是首次使用 [{selected_model}] 模型，系统会自动下载几GB的模型文件。")

        start_gen_time = time.time()
        generator = LiveSubtitleGenerator(video_path=video_path)
        # 传入 skip_separation 参数
        srt_path = generator.run(model_size=selected_model, audio_type=audio_type, skip_separation=skip_separation)
        whisper_time = time.time() - start_gen_time
        
        os.makedirs(output_dir, exist_ok=True)
        try:
            with open(time_log_path, "w", encoding="utf-8") as f:
                f.write(str(whisper_time))
        except:
            pass

    if not srt_path or not os.path.exists(srt_path):
        print("❌ 未能获取有效的 SRT 文件，终止。")
        return

    print("\n" + "="*50)
    print(" 🌍 阶段二：大模型 AI 翻译与排版")
    print("="*50)
    
    do_translate = input("👉 是否继续调用 AI 对字幕进行翻译？(y/n) [默认 y, 直接回车]: ").strip().lower()
    
    if do_translate != 'n':
        print("\n📝 请选择输出格式：")
        print("   1. 中日双语字幕")
        print("   2. 纯中文字幕")
        lang_choice = input("👉 请输入序号 (默认 1): ").strip()
        output_mode = "chinese_only" if lang_choice == "2" else "bilingual"

        print("\n🧠 请选择翻译大模型 (支持智能路由)：")
        for key, config in API_CONFIGS.items():
            print(f"   {key}. {config['name']}")
        api_choice = input("👉 请输入序号 (默认 1): ").strip()
        config = API_CONFIGS.get(api_choice, API_CONFIGS["1"])

        if "YOUR_" in config["api_key"]:
            print(f"\n❌ 错误：尚未配置 {config['name']} 的 API Key！")
            return

        lyrics_dir = "input/lyrics"
        os.makedirs(lyrics_dir, exist_ok=True)
        
        specific_lyrics = os.path.join(lyrics_dir, f"{base_name}.txt")
        general_lyrics = os.path.join(lyrics_dir, "参考歌词_范本.txt")
        
        reference_lyrics_path = None
        if os.path.exists(specific_lyrics):
            reference_lyrics_path = specific_lyrics
        elif os.path.exists(general_lyrics):
            reference_lyrics_path = general_lyrics
        
        cache_file_path = os.path.join(os.path.dirname(srt_path), f"{os.path.splitext(os.path.basename(srt_path))[0]}_翻译缓存.json")
        if os.path.exists(cache_file_path):
            print(f"\n📦 检测到已存在的历史翻译缓存！")
            print("⚠️ 注意：如果你刚刚切换了排版模式 (如[双语]切换到[纯中文])，或修改了参考歌词，请务必清除旧缓存！")
            clear_cache = input("👉 是否清除历史缓存重新翻译？(y/n) [默认 n, 直接回车继续使用旧缓存]: ").strip().lower()
            if clear_cache == 'y':
                try:
                    os.remove(cache_file_path)
                    print("   -> 🗑️ 历史缓存已成功清除！大模型将重新开始翻译。")
                except Exception as e:
                    print(f"   -> ⚠️ 缓存清除失败: {e}")

        start_trans_time = time.time()
        translator = SubtitleTranslator(
            api_key=config["api_key"],
            base_url=config["base_url"],
            primary_model=config["primary_model"],
            reasoning_model=config.get("reasoning_model", config["primary_model"]),
            srt_path=srt_path,
            reference_txt_path=reference_lyrics_path,
            output_mode=output_mode
        )
        translator.run()
        translation_time = time.time() - start_trans_time
    else:
        print("\n✅ 好的，已跳过大模型翻译。原版日文字幕已保留在 subtitles 文件夹内！")

    # ==========================================
    # 📊 输出明细版性能体检与算力评级报告
    # ==========================================
    total_time = whisper_time + translation_time
    if total_time > 0:
        video_duration = get_video_duration(video_path)
        
        print("\n" + "="*50)
        print(" 📊 全链路性能体检报告 (Performance Profiler)")
        print("="*50)
        
        if video_duration > 0:
            print(f"   -> 🎞️ 原视频总时长: {int(video_duration // 60)} 分 {int(video_duration % 60)} 秒")
            
        print(f"   -> 🎤 打轴纯耗时  : {int(whisper_time // 60)} 分 {int(whisper_time % 60)} 秒")
        print(f"   -> 🌍 翻译纯耗时  : {int(translation_time // 60)} 分 {int(translation_time % 60)} 秒")
        print(f"   -> ⏱️ 真实总计耗时: {int(total_time // 60)} 分 {int(total_time % 60)} 秒")
        
        # 🌟 智能评级逻辑
        if video_duration > 0:
            speed_ratio = video_duration / total_time
            print(f"\n   -> ⚡ 综合处理倍速: {speed_ratio:.2f}x (即处理速度是播放速度的 {speed_ratio:.2f} 倍)")
            
            if speed_ratio >= 3.0:
                rating = "👑 SSS 级 (神级算力！这速度简直是印钞机！)"
            elif speed_ratio >= 1.5:
                rating = "🚀 S 级 (性能极佳！远超原片播放速度！)"
            elif speed_ratio >= 1.0:
                rating = "⚡ A 级 (效率达标！比人工处理快百倍！)"
            else:
                rating = "🐢 B 级 (平稳运行！建议挂机喝杯咖啡~)"
                
            print(f"   -> 🏆 最终性能评级: {rating}")
        print("="*50)

if __name__ == "__main__":
    main()