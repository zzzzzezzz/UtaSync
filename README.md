🎵 UtaSync

<p align="center">
<b>一款专为日音 Live、音乐节和电台深度定制的工业级自动化双语字幕工作站</b>
</p>

<p align="center">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Python-3.10%252B-blue.svg" alt="Python Version">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Audio-Demucs_v4-green.svg" alt="Demucs">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/ASR-Faster--Whisper-orange.svg" alt="Faster-Whisper">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/LLM-DeepSeek%2520%257C%2520Gemini-purple.svg" alt="LLM">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/UI-CustomTkinter-black.svg" alt="CustomTkinter">
</p>

📖 项目简介

UtaSync 致力于解决传统 AI 字幕工具在复杂音乐与 Live 现场场景下的三大史诗级痛点：

乐器轰炸：架子鼓和失真吉他盖过人声，导致 AI 听写彻底变成乱码。

长间奏霸屏：长达数十秒的纯音乐间奏导致上一句字幕停留在屏幕上无法消散。

乱翻与空耳：传统机翻不看上下文和官方歌词，频发“空耳”错别字，且排版拥挤不堪。

本项目将 Demucs (人声分离)、Faster-Whisper (极速打轴) 与 LLM 大模型 (智能翻译与排版) 深度融合，并辅以极度强壮的防崩溃工程底座，提供从视频拖入到双语字幕产出的“一键式”体验。

✨ 核心硬核特性 (Features)

🎸 手术刀级提音与无缝切片 (Demucs Engine)

极限剥离：无惧千人合唱与重金属斗琴，完美剥离纯净人声。

动态防爆内存：首创针对 2 小时+ 蓝光 Live 的 「无缝切片处理机制」。音频自动切割分段进入显存，分离后再无痕拼接，彻底告别超长视频导致的 OOM (内存溢出) 崩溃。

⏱️ 智能打轴与防霸屏 (Whisper VAD Tuning)

双模式声学模型：内置【Live 现场】（高容忍防切碎）与【电台访谈】（低容忍高频切分）双重 VAD 参数集。

8秒物理熔断：强制拦截 Whisper 幻觉，字幕停留最多 8 秒，完美解决超长吉他 Solo 导致的字幕霸屏或错位问题。

🧠 大模型“开卷”翻译与同传 (LLM Translator)

官方歌词强制注入：支持直接粘贴官方网易云/QQ音乐歌词作为参考，大模型手握标准答案进行“同传级”校对，误听率降至 0%。

无缝 MC 切换：遇到无歌词的说话/互动环节，自动无感知切换至同声传译盲翻模式。

强迫症级排版：物理锁死时间轴与格式，强制产出【1行日文 + 1行中文】，严禁大模型违规合并或换行。

🛡️ 工业级容错与防线 (Fault Tolerance)

断网/限流续传：内置 JSON 进度缓存机制。遭遇 API 429 限流会自动阶梯休眠；哪怕断电重启，也能从中断的批次满血复活。

妥协放行机制 (Graceful Degradation)：面对大模型连续报错的“毒药数据”，系统会在第 5 次重试时强行通关并隔离错误，誓死保卫主程序不崩溃。

🖥️ V2.0 桌面端 GUI (全新上线)

彻底告别枯燥的命令行！UtaSync V2.0 引入了基于 CustomTkinter 构建的现代化暗黑极简风桌面端：

拖拽直达：支持一键拖拽音视频文件。

免文件歌词库：界面内置巨大黑板，直接 Ctrl+V 粘贴参考歌词。

多线程防假死：后台狂飙分离引擎，前台 UI 依然丝滑如初。

沉浸式控制台：实时流动展示分离、打轴、翻译进度的极客日志框。

⚙️ 快速上手 (Quick Start)

1. 环境准备

请确保您的电脑已安装 Python 3.10+，并且已在系统中配置好 FFmpeg。

# 克隆仓库
git clone [https://github.com/你的用户名/UtaSync.git](https://github.com/你的用户名/UtaSync.git)
cd UtaSync

# 安装核心依赖
pip install -r requirements.txt
pip install customtkinter


(注：如果需要极限 GPU 加速，请确保已正确安装 CUDA 与 cuDNN)

2. 配置 API Key

UtaSync 支持配置多家大模型。如果你使用 SiliconFlow (硅基流动) 或是 Google Gemini，请在桌面端 UI 的配置框中，填入你的个人 API Key 即可。

3. 一键起飞 🚀

启动 V2.0 桌面端界面（推荐）：

python app.py


启动 V1.0 纯净命令行版：

python main.py


🗺️ 架构与路线图 (Roadmap)

[x] V1.0 核心引擎：FFmpeg + Demucs + Faster-Whisper + LLM 自动化管线。

[x] V1.5 强壮底座：内存防爆切片、断点续传、API 妥协放行机制。

[x] V2.0 桌面端：CustomTkinter 暗黑风格图形化界面、实时日志反馈。

[ ] V2.5 花字渲染：直接输出带有发光/描边排版的 .ass 特效字幕文件。

[ ] V3.0 独立分发：使用 PyInstaller 打包为免 Python 环境的 Windows .exe 单文件。

⚠️ 免责声明 (Disclaimer)

本项目仅供编程学习与技术交流使用，核心依赖开源模型。请勿将生成的字幕用于任何侵犯版权的商业用途。用户因使用本工具调用第三方 API 产生的任何费用或法律责任，由用户自行承担。
