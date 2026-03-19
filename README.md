# UtaSync - Professional Subtitle Studio 🎬

**UtaSync** 是一款专为音乐创作者、Live 现场搬运工及视频后期工作者打造的**端到端（End-to-End）自动双语字幕与硬核压制引擎**。

它不仅仅是一个字幕生成工具，而是一条集成了 **人声分离 ➔ AI 听写 ➔ 大模型语境翻译 ➔ 工业级花字排版 ➔ 智能硬件加速压制 ➔ B站 Hi-Res 无损输出** 的完整现代视频工业流水线。

## ✨ 核心特性 (Core Features)

### 🎙️ 1. 影音级声学处理 (Acoustic Processing)

- **伴奏智能剥离 (Demucs 引擎)**：针对 Live 现场、摇滚乐等极度嘈杂的场景，系统会首先剥离伴奏与和声，提取极致纯净的主唱人声，彻底消灭传统打轴软件“遇歌词就乱码”的痛点。
- **多精度打轴 (Whisper 矩阵)**：从 `large-v2` (战神级精度) 到 `turbo` (极速模式)，支持根据显存大小智能切片，物理锁死显存峰值（防爆显存机制），最低 4G 显存即可流畅运行。

### 🧠 2. 大模型语境翻译 (LLM Translation)

- **智能路由**：原生集成对 SiliconFlow (DeepSeek-V3/R1)、Kimi、Google Gemini 等前沿大模型的支持。
- **参考歌词库 (Reference Mode)**：支持输入官方日文/英文歌词作为参考锚点，LLM 将进行对齐纠错与文学化翻译，并自动格式化为标准双语字幕。
- **断点安全续传**：所有阶段自动生成 Hash 指纹校验，修改翻译参数无需重新打轴分离，极大节省时间。

### 🎨 3. 工业级花字引擎 (ASS Aesthetics)

- **低饱和高级美学**：内置 `克莱因蓝`、`柠檬碎冰`、`落日绯红` 等多款莫兰迪低饱和度调色预设，彻底告别廉价的高饱和刺眼字幕。
- **智能动态呼吸算法 (Anti-Fatigue Fade)**：独创段落式防闪烁判定。长句展现丝滑的电影级淡入淡出 (`\fad`)；短句与紧密衔接处自动降级为“硬切”，保护观众视力。
- **零膨胀字体映射**：独立控制中日双语的字体与字号，直接调用系统本地原生字体（如 思源黑体、Yu Mincho 等），软件无需打包几十兆的字库。

### ⚡ 4. 全平台智能硬件加速压制 (Smart Hardware Encode)

- **级联降级调度**：系统会自动侦测并依次尝试 `NVIDIA (NVENC)` ➔ `Apple (VideoToolbox)` ➔ `Intel (QSV)` ➔ `AMD (AMF)`，实现数倍于 CPU 的极速压制。全线失败时自动无缝切回 CPU 安全多线程软压。
- **无感后台压制 (OS Priority)**：系统级调度优化，FFmpeg 进程采用“低于正常优先级（Below Normal）”运行。即便在渲染时打 3A 游戏，系统也会自动为游戏让出算力，绝不卡机。

### 🎧 5. Bilibili Hi-Res 专属优化通道

- **强穿透封装**：一键开启后，系统将强制采用 `.mkv` 容器，并将音频轨强制无损重采样为 **24-bit/32-bit 48000Hz FLAC**。
- **金标点亮**：生成的成片可 100% 触发 Bilibili 播放器的「Hi-Res 无损音质」金标，保留原片最顶级的视听动态范围。

## 🚀 快速开始 (Quick Start)

### 环境依赖

1. **Python 3.10+**
2. **FFmpeg**: 必须安装并已将其添加至系统环境变量 (`Path`) 中。在终端输入 `ffmpeg -version` 不报错即为成功。

### 运行指令

1. 克隆本项目并进入目录。
2. 安装所需 Python 依赖：
   ```
   pip install customtkinter openai whisper demucs 
   # 请根据实际使用的底层库补全 requirements.txt

   ```
3. 启动主程序：
   ```
   python app.py

   ```

## 📁 目录结构 (Structure)

```
UtaSync/
├── app.py                  # 核心 UI 界面与任务调度总线
├── user_settings.json      # 用户偏好设置本地缓存 (自动生成)
├── core/
│   ├── generator.py        # 负责 Demucs 音频分离与 Whisper 听写打轴
│   ├── translator.py       # 负责与 LLM 通信进行语境翻译
│   └── ass_maker.py        # 特效字幕生成器 (包含所有美学配色预设)
└── output/                 # 压制成品与过程文件输出目录

```

## 🛠️ 后续开发路线图 (Roadmap)

- \[ ] 多视频批量任务队列 (Batch Processing Queue)
- \[ ] 现代化极简弹窗 UI 重构 (Minimalist Modal UI)
- \[ ] 接入 Gemini 视觉大模型实现“根据画面自动配色”功能

*Built with passion for creators. 让每一个发光发热的现场，都被完美铭记。*
