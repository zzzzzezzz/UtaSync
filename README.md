🎵 UtaSync V2.0

Professional Auto Subtitle Pipeline for Live Music & Podcasts. 一款专为日音 Live 现场、播客访谈打造的工业级全自动双语字幕生成工作站。

✨ 核心特性 (Core Features)

🎸 极致抗干扰 (Demucs V4)：针对 Live 演唱会的复杂混响与摇滚伴奏，内置无缝切片防爆内存机制，精准提取纯净人声，支持长达 2 小时以上的视频处理。

📝 开卷考试级翻译 (LLM Reference Translation)：大模型结合官方歌词库，精准修复 Whisper 发音空耳，物理锁死时间轴，实现 0 漏翻。

🛡️ 工业级稳定防线：

Deep Cancellation (瞬间秒杀)：支持随时拉闸，瞬间切断底层 C++ 运算，拒绝僵尸线程。

Memory Safe (防显存溢出)：重写底层垃圾回收，完美解决 Windows 环境下多线程 GUI 的 Segmentation Fault 闪退死穴。

🧠 状态全记忆 (Auto-Save)：自动保存 API Key、大段参考歌词与翻译配置，关闭软件原样恢复。

⚡ 双指纹断点续传：基于哈希校验，中途停止后自动复用已生成的人声或原文字幕，节省海量算力。

🚀 快速开始 (Quick Start)

1. 环境准备

本项目依赖 FFmpeg，请确保系统已安装并配置环境变量。

# 克隆仓库
git clone [https://github.com/YourName/UtaSync.git](https://github.com/YourName/UtaSync.git)
cd UtaSync

# 安装核心依赖
pip install -r requirements.txt
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu118](https://download.pytorch.org/whl/cu118)


2. 启动工作站

python app.py


3. 操作流

导入本地视频或音频文件（支持 mp4/mkv/wav/mp3 等格式）。

在右侧“参考歌词库”贴入网易云/QQ音乐的日文原词（如果是访谈则留空盲翻）。

选择合适的声学模型、分离策略和引擎精度。

填入 API Key（支持 SiliconFlow / Gemini / 本地代理）。

点击「启动处理引擎」，全自动产出 .srt 极致双语字幕！

🏗️ 核心组件 (Components)

app.py: CustomTkinter 沉浸式暗黑主题 GUI，多线程消息队列防假死。

core/generator.py: faster-whisper + 动态 VAD (Voice Activity Detection)，精准切分长短句。

core/translator.py: OpenAI 兼容并发接口，强力斩杀 AI 幻觉，确保纯净单行排版。

📜 License

MIT License