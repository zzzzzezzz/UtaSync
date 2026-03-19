import os
import re

# ==========================================
# 🎨 工业级双语花字预设库 (莫兰迪低饱和/高级感定制)
# 优化：整体字号调小 (中文55，日文35)，比例更显高级与精致
# ==========================================
ASS_PRESETS = {
    "默认双语 (纯白+浅灰)": {
        "ch_font": "Microsoft YaHei", "ch_size": 55, "ch_color": "#FFFFFF",
        "jp_font": "Meiryo", "jp_size": 35, "jp_color": "#CCCCCC",
        "outline_color": "#18181B", "outline_size": 3, "shadow_size": 1
    },
    "yama专属 (克莱因蓝/低饱和)": {
        "ch_font": "Microsoft YaHei", "ch_size": 55, "ch_color": "#F0F8FF",
        "jp_font": "Meiryo", "jp_size": 35, "jp_color": "#BAE6FD",         
        "outline_color": "#0C4A6E", "outline_size": 3, "shadow_size": 2    
    },
    "majiko专属 (柠檬碎冰/低饱和)": {
        "ch_font": "Microsoft YaHei", "ch_size": 55, "ch_color": "#FEF9C3", 
        "jp_font": "Meiryo", "jp_size": 35, "jp_color": "#FAFAFA",         
        "outline_color": "#3F3F46", "outline_size": 3, "shadow_size": 1    
    },
    "樋口爱专属 (落日绯红/低饱和)": {
        "ch_font": "Microsoft YaHei", "ch_size": 55, "ch_color": "#FFF1F2", 
        "jp_font": "Meiryo", "jp_size": 35, "jp_color": "#FECDD3",         
        "outline_color": "#881337", "outline_size": 3, "shadow_size": 2    
    },
    "莫兰迪绿 (清新治愈风)": {
        "ch_font": "Microsoft YaHei", "ch_size": 55, "ch_color": "#F0FDF4", 
        "jp_font": "Meiryo", "jp_size": 35, "jp_color": "#D1FAE5",         
        "outline_color": "#064E3B", "outline_size": 3, "shadow_size": 1    
    },
    "紫罗兰 (微醺梦幻风)": {
        "ch_font": "Microsoft YaHei", "ch_size": 55, "ch_color": "#F5F3FF", 
        "jp_font": "Meiryo", "jp_size": 35, "jp_color": "#DDD6FE",         
        "outline_color": "#4C1D95", "outline_size": 3, "shadow_size": 2    
    },
    "黑金质感 (LiveHouse高级感)": {
        "ch_font": "Microsoft YaHei", "ch_size": 55, "ch_color": "#FDE68A", 
        "jp_font": "Meiryo", "jp_size": 35, "jp_color": "#D4D4D8",         
        "outline_color": "#18181B", "outline_size": 3, "shadow_size": 2    
    },
    "B站烤肉标准 (高亮高对比)": {
        "ch_font": "Microsoft YaHei", "ch_size": 60, "ch_color": "#FFFFFF", 
        "jp_font": "Meiryo", "jp_size": 38, "jp_color": "#FFFFFF",         
        "outline_color": "#000000", "outline_size": 4, "shadow_size": 3    
    },
    "极简电影 (无边细字)": {
        "ch_font": "Microsoft YaHei", "ch_size": 48, "ch_color": "#EEEEEE",
        "jp_font": "Meiryo", "jp_size": 30, "jp_color": "#AAAAAA",
        "outline_color": "#000000", "outline_size": 1, "shadow_size": 0    
    }
}

class ASSMaker:
    """
    UtaSync 专属 ASS 特效字幕生成器 (完美双语物理隔离 + 高阶段落式防闪烁呼吸)
    """
    def __init__(self, srt_path):
        self.srt_path = srt_path
        base_name = os.path.splitext(srt_path)[0]
        self.ass_path = f"{base_name}_顶级特效.ass"

    def convert_time(self, srt_time):
        """将 SRT 时间 00:00:01,000 转为 ASS 时间 0:00:01.00"""
        ass_time = srt_time.replace(',', '.')
        if ass_time.startswith('0'):
            ass_time = ass_time[1:]  
        return ass_time[:10]  

    def parse_srt_time_to_ms(self, srt_time_str):
        """将 SRT 时间字符串 00:00:01,000 转为毫秒用于计算时长"""
        try:
            h, m, s_ms = srt_time_str.split(':')
            s, ms = s_ms.split(',')
            return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
        except:
            return 0

    def hex_to_ass_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = hex_color[0:2], hex_color[2:4], hex_color[4:6]
            return f"&H{b}{g}{r}&"
        return "&HFFFFFF&"

    def build_ass_header(self, resolution_x=1920, resolution_y=1080):
        header = f"""[Script Info]
Title: UtaSync Auto Generated ASS
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {resolution_x}
PlayResY: {resolution_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
        base_style = "Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,30,1\n"
        return header + base_style + "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

    def generate_ass(self, style_config="默认双语 (纯白+浅灰)"):
        print(f"\n🎨 [ASS 引擎] 正在构建精美双语特效字幕...")
        
        if isinstance(style_config, str) and style_config in ASS_PRESETS:
            config = ASS_PRESETS[style_config]
            print(f"   -> 💅 已应用专属花字预设: [{style_config}]")
        elif isinstance(style_config, dict):
            config = style_config
            print("   -> 💅 已应用客制化花字配置")
        else:
            config = ASS_PRESETS["默认双语 (纯白+浅灰)"]
            print("   -> ⚠️ 未知预设，已回退至默认样式")

        with open(self.srt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        blocks = re.split(r'\n\s*\n', content)
        
        c_ch = self.hex_to_ass_color(config.get('ch_color', '#FFFFFF'))
        c_jp = self.hex_to_ass_color(config.get('jp_color', '#CCCCCC'))
        c_out = self.hex_to_ass_color(config.get('outline_color', '#000000'))
        
        s_ch = config.get('ch_size', 55)
        f_ch = config.get('ch_font', 'Microsoft YaHei')
        s_jp = config.get('jp_size', 35)
        f_jp = config.get('jp_font', 'Meiryo')
        bord = config.get('outline_size', 3)
        shad = config.get('shadow_size', 1)
        
        fade_mode = config.get('fade_mode', "智能动态呼吸 (默认/推荐)")

        # 🌟 阶段一：解析所有合法字幕块，获取全局视野 (Lookahead)
        valid_blocks = []
        for block in blocks:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if len(lines) < 3: continue
            
            time_line = lines[1]
            if '-->' not in time_line: continue
            
            start_str, end_str = time_line.split('-->')
            start_ms = self.parse_srt_time_to_ms(start_str.strip())
            end_ms = self.parse_srt_time_to_ms(end_str.strip())
            
            valid_blocks.append({
                'start_ass': self.convert_time(start_str.strip()),
                'end_ass': self.convert_time(end_str.strip()),
                'start_ms': start_ms,
                'end_ms': end_ms,
                'text_lines': lines[2:]
            })

        ass_events = []

        # 🌟 阶段二：计算独立淡入淡出 (段落式防闪烁呼吸算法)
        for i, b in enumerate(valid_blocks):
            duration = b['end_ms'] - b['start_ms']
            
            # 计算与上一句和下一句的时间间隙
            gap_with_prev = (b['start_ms'] - valid_blocks[i-1]['end_ms']) if i > 0 else 9999
            gap_with_next = (valid_blocks[i+1]['start_ms'] - b['end_ms']) if i < len(valid_blocks) - 1 else 9999

            fade_effect = ""
            if "强制全局淡入淡出" in fade_mode:
                fade_effect = r"{\fad(200,200)}"
            elif "硬切无延时" in fade_mode:
                fade_effect = ""
            else:
                # 智能动态呼吸算法核心：分离 fade_in 和 fade_out
                fade_in = 200
                fade_out = 200
                
                if duration < 1200:
                    # 单句时长太短，强制硬切，确保拥有足够的阅读时间
                    fade_in = 0
                    fade_out = 0
                else:
                    # 段落式呼吸连贯性处理
                    if gap_with_prev < 200:
                        # 紧接上一句：取消淡入（防止出现从黑变亮的闪烁）
                        fade_in = 0
                    if gap_with_next < 200:
                        # 紧接下一句：取消淡出（保持亮度直接切入下一句）
                        fade_out = 0
                
                # 仅在需要淡入淡出时添加标签
                if fade_in > 0 or fade_out > 0:
                    fade_effect = f"{{\\fad({fade_in},{fade_out})}}"

            # 排版组装
            text_lines = b['text_lines']
            if len(text_lines) >= 2:
                jp_text, ch_text = text_lines[0], text_lines[1]
                styled_ch = f"{fade_effect}{{\\fn{f_ch}\\fs{s_ch}\\c{c_ch}\\3c{c_out}\\bord{bord}\\shad{shad}\\b1}}{ch_text}"
                styled_jp = f"{{\\fn{f_ch}\\fs10}}\\N{{\\fn{f_jp}\\fs{s_jp}\\c{c_jp}\\3c{c_out}\\bord{bord}\\shad{shad}\\b0}}{jp_text}"
                final_text = styled_ch + styled_jp
            else:
                single_text = " ".join(text_lines)
                final_text = f"{fade_effect}{{\\fn{f_ch}\\fs{s_ch}\\c{c_ch}\\3c{c_out}\\bord{bord}\\shad{shad}\\b1}}{single_text}"

            event = f"Dialogue: 0,{b['start_ass']},{b['end_ass']},Default,,0,0,0,,{final_text}"
            ass_events.append(event)

        final_ass_content = self.build_ass_header() + "\n".join(ass_events)
        
        with open(self.ass_path, 'w', encoding='utf-8') as f:
            f.write(final_ass_content)
            
        return self.ass_path

if __name__ == "__main__":
    pass