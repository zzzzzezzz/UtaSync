🎵 UtaSync - 专业级日音 Live/访谈自动化双语字幕工作站

<p align="center">
<b>专为极其嘈杂的重型 Live 现场、极柔清唱以及电台访谈深度定制的工业级 AI 字幕流水线</b>
</p>

<p align="center">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Python-3.10%252B-blue.svg" alt="Python Version">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/Audio-Demucs_v4-green.svg" alt="Demucs">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/ASR-Faster--Whisper-orange.svg" alt="Faster-Whisper">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/LLM-DeepSeek%2520%257C%2520Gemini-purple.svg" alt="LLM">
<img src="https://www.google.com/search?q=https://img.shields.io/badge/UI-CustomTkinter-black.svg" alt="CustomTkinter">
</p>

📖 项目简介

UtaSync V2.0 致力于解决传统 AI 字幕工具在处理“复杂音乐与现场场景”时面临的史诗级痛点：

乐器轰炸致盲：架子鼓和失真吉他盖过人声，导致 AI 听写彻底变成乱码或静音。

极柔气声误杀：轻柔的低语往往被降噪算法当成底噪直接抹除，导致大段缺漏。

超长视频崩溃：处理 2 小时+ 的音乐节视频时，极易因内存溢出(OOM)或大模型长上下文失焦而导致全盘崩溃。

机翻空耳与格式崩坏：传统机翻不结合官方歌词，频发“空耳”，且长句排版拥挤不堪，甚至擅自合并时间轴。

本项目将 Demucs (人声分离)、Faster-Whisper (极速打轴) 与 LLM 大模型 (智能同传与排版) 深度融合，包裹在一个多线程异步防假死的极简暗黑 GUI 中，提供从音视频导入到精美双语字幕产出的“一键式”体验。

🏗️ 核心架构与黑科技 (Core Features)

🖥️ 1. 沉浸式专业图形界面 (GUI)

极简暗黑风：基于 CustomTkinter 打造的专业级数字音频工作站 (DAW) 视觉体验。

消息队列防闪退：全面引入 queue.Queue 拦截底层海量并发日志，主界面永远丝滑拖拽，彻底告别“未响应”与闪退。

免文件歌词黑板：直接在界面粘贴多首歌（甚至数十首）的参考歌词，彻底告别繁琐的 .txt 文件管理。

双指纹智能管家：利用 MD5 侦测打轴参数与翻译配置的变动，极其聪明地处理断点续传。改了歌词？只重翻。改了模型精度？只重跑打轴，复用耗时的分离音频缓存！

🎸 2. 军工级提音与动态 VAD (Audio & ASR)

无缝切片防爆内存：针对 20分钟+ 到数小时的超长视频，底层自动分段分离人声，完美护航 2 小时 Live，拒绝物理内存溢出。

三模场景隔离舱 (核心杀招)：

👉 常规摇滚 Live：坚守 0.5 VAD 阈值，完美过滤杂音与超长间奏幻觉。

👉 极柔气声 Live：下调至 0.3 宽容 VAD 阈值，专治微弱气声 (如 Yama / Aimer) 被误杀交白卷。

👉 无伴奏电台访谈：允许强制跳过人声分离，极速打轴。

🧠 3. 大模型“开卷”翻译与强力纠错 (LLM Translator)

智能代理穿透 (Smart Routing)：代码层内置网络路由，并在 UI 提供自定义代理端口（如 10808）。调用 Gemini 免费版时自动挂载代理防断连；调用国内 SiliconFlow 时智能切回极速物理直连。

15 句微型批次护航：将翻译批次从 30 句骤降至 15 句，极大收束大模型在超大歌词本中的注意力，彻底解决大模型“漏翻”、“吞字”与“排版错位”问题。

60% 漏翻防线与时间轴锁死：底层代码物理锁死 Whisper 原始时间轴！侦测到大模型偷懒（输出轴少于输入轴 60%）时直接打回重审，严防字幕合并错位。

第 5 次妥协放行 (Graceful Degradation)：面对连续报错的“毒药级发音乱码”，重试 4 次后强制通关放行（保留原文），誓死保卫 2 小时主流程不被卡死！且自动兼容并剔除 DeepSeek-R1 的 <think> 思考过程。

⚙️ 快速上手 (Quick Start)

1. 环境准备

请确保您的电脑已安装 Python 3.10+，并且 必须在系统环境变量中配置好 FFmpeg。

# 1. 克隆本仓库
git clone [https://github.com/你的用户名/UtaSync.git](https://github.com/你的用户名/UtaSync.git)
cd UtaSync

# 2. 一键安装核心依赖库
pip install -r requirements.txt


(💡 性能提示：为获得极其丝滑的打轴体验，请确保配备 NVIDIA 显卡并已正确配置 CUDA 与 cuDNN。)

2. 启动工作站 🚀

双击运行或在终端输入：

python app.py


在左侧填入你的大模型 API Key，配置将自动加密保存于本地 user_settings.json（已加入 .gitignore 保护名单）。

📁 目录结构 (Directory Structure)

UtaSync/
├── app.py                  # V2.0 桌面端 GUI 控制中枢
├── core/
│   ├── generator.py        # 打轴引擎：负责防爆分离、三模 VAD、Faster-Whisper
│   └── translator.py       # 翻译引擎：负责代理路由、并发调度、物理锁轴与妥协放行
├── output/                 # 自动生成音频、字幕及双指纹缓存的收纳站
└── requirements.txt        # 核心环境依赖清单


🤝 常见场景推荐配置

YOASOBI / 重金属摇滚 Live 👉 Live 现场演唱 (常规/摇滚) + 开启分离

不插电 / 极柔气声清唱 👉 Live 现场演唱 (极柔气声) + 开启分离

电台广播 / 纯对话访谈 👉 访谈 / 电台播客 + 强制跳过

(对于长达 1 小时以上的超长视频，强烈推荐将翻译配置切换为国内的 SiliconFlow (智能路由)，搭配 DeepSeek-V3 以获得无断连的最佳体验。)

⚠️ 免责声明

本项目仅供编程学习与技术交流使用，核心依赖开源声学模型。请勿将本工具及生成的字幕用于任何侵犯版权的商业用途。用户因调用第三方大模型 API 产生的任何费用或网络法律责任，由用户自行承担。