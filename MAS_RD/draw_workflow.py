# 必须将 matplotlib.use() 放在所有 matplotlib 相关导入的最前面
import matplotlib

import os
import requests
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as patches # 引入 patches 用于绘制背景框

# --- 1. 字体管理 (完全保留您提供的最终版本) ---

def setup_chinese_font():
    """
    一个完整的函数，用于下载、注册中文字体，并处理缓存问题。
    使用多种备用字体源和系统字体备选方案，提高稳定性。
    """
    # --- 字体配置 ---
    FONT_FILENAME = "Alibaba-PuHuiTi-Regular.ttf"
    
    # 字体下载源列表，按优先级排序
    font_urls = [
        "https://mdn.alipayobjects.com/huamei_qa8qxu/afts/file/A*_7tMQ57pQxUAAAAAAAAAAAAADmJ7AQ/original",  # 阿里巴巴普惠体官方源
        "https://github.com/bytedance/bytedance-typography/raw/main/fonts/Alibaba-PuHuiTi-Regular.ttf",  # GitHub源
        "https://cdn.jsdelivr.net/gh/bytedance/bytedance-typography/fonts/Alibaba-PuHuiTi-Regular.ttf"   # jsDelivr CDN
    ]

    # 步骤 A: 下载字体文件
    if not os.path.exists(FONT_FILENAME):
        print(f"本地未找到字体 '{FONT_FILENAME}'，正在尝试从下载源下载...")
        font_downloaded = False
        
        # 尝试所有可用的下载源
        for i, font_url in enumerate(font_urls):
            try:
                print(f"尝试下载源 {i+1}/{len(font_urls)}: {font_url}")
                # 增加 User-Agent 伪装成浏览器，提高下载成功率
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
                }
                response = requests.get(font_url, stream=True, headers=headers, timeout=30)  # 增加30秒超时
                response.raise_for_status()
                
                # 检查响应是否有效（至少10KB）
                if len(response.content) < 10240:
                    print(f"警告: 下载的字体文件太小，可能不完整。")
                    continue
                
                with open(FONT_FILENAME, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"字体已成功下载并保存为 '{FONT_FILENAME}'。")
                font_downloaded = True
                break  # 下载成功，退出循环
            except requests.exceptions.RequestException as e:
                print(f"下载源 {i+1} 失败: {e}")
        
        # 如果所有下载源都失败，尝试使用系统已安装的中文字体
        if not font_downloaded:
            print("所有下载源都失败，尝试使用系统已安装的中文字体...")
            # 查找系统中可用的中文字体
            system_fonts = [f for f in fm.findSystemFonts() if any(c in os.path.basename(f).lower() for c in ['simhei', 'heiti', 'microsoftyahei', 'yahei', 'song', 'simsun'])]
            
            if system_fonts:
                print(f"找到 {len(system_fonts)} 个系统中文字体，使用第一个: {os.path.basename(system_fonts[0])}")
                return fm.FontProperties(fname=system_fonts[0])
            else:
                print("[严重错误] 无法下载字体，且未找到系统中文字体。")
                print("请手动下载字体文件并放到脚本同目录下，或确保系统安装了中文字体。")
                return None
    else:
        print(f"字体 '{FONT_FILENAME}' 已在本地找到。")

    # 清理旧的字体缓存，确保新字体能被正确加载
    try:
        font_cache_dir = matplotlib.get_cachedir()
        for file in os.listdir(font_cache_dir):
            if file.endswith((".json", ".cache")):
                os.remove(os.path.join(font_cache_dir, file))
        print("Matplotlib 字体缓存已清理，以确保加载新字体。")
    except Exception as e:
        print(f"[警告] 清理字体缓存时出错: {e}")

    # 向 Matplotlib 的 fontManager 明确注册字体
    fm.fontManager.addfont(os.path.abspath(FONT_FILENAME))

    return fm.FontProperties(fname=os.path.abspath(FONT_FILENAME))


# -- 主逻辑开始 --
print("正在设置中文字体环境...")
my_font = setup_chinese_font()

if my_font is None:
    print("\n[程序终止] 字体设置失败，无法继续执行。")
    exit()
else:
    # 全局设置 Matplotlib 默认字体
    plt.rcParams['font.sans-serif'] = [my_font.get_name()]
    plt.rcParams['axes.unicode_minus'] = False
    print(f"已将 Matplotlib 全局字体设置为: '{my_font.get_name()}'")


# --- 2. 创建图的结构 (与之前相同) ---
G = nx.DiGraph()
nodes = {
    'start': '开始:\n输入专利列表', 'association': '关联技术分析师\n(Association Agent)',
    'emerging_theme': '新兴主题分析师\n(Emerging Theme Agent)', 'gap': '技术空白分析师 (VC)\n(Gap Agent)',
    'critic': '评审员\n(Critic Agent)', 'evaluation': '评估与决策分析师 (战略家)\n(Evaluation Agent)',
    'end': '结束:\n输出最终报告'
}
edges = [
    ('start', 'association'), ('start', 'emerging_theme'), ('start', 'gap'),
    ('association', 'critic'), ('emerging_theme', 'critic'), ('gap', 'critic'),
    ('critic', 'evaluation'), ('evaluation', 'end')
]
G.add_nodes_from(nodes.keys())
G.add_edges_from(edges)


# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
# --- START: 全新的“期刊级”绘图代码 ---
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvahoravvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

# --- 3. 定义布局和样式 (全新设计) ---
pos = {
    'start': (0, 4.5),
    'association': (-2.5, 3), 
    'emerging_theme': (0, 3), 
    'gap': (2.5, 3),
    'critic': (0, 1.5), 
    'evaluation': (0, 0), 
    'end': (0, -1.5)
}

# --- 专业的颜色主题 ---
phase_colors = {
    'background': '#F5F5F5', # 画布背景色
    'input_output': '#D6EAF8', # 输入/输出阶段颜色 (淡蓝)
    'analysis': '#D1F2EB',      # 分析阶段颜色 (淡青)
    'review': '#FDEDEC',        # 评审阶段颜色 (淡粉)
    'decision': '#FCF3CF',      # 决策阶段颜色 (淡黄)
    'arrow': '#566573',         # 箭头颜色
    'font': '#2C3E50',          # 主要字体颜色
    'border': '#ABB2B9'         # 节点边框颜色
}

# --- 4. 绘制图形 (全新美化流程) ---
print("\n正在以高标准绘制流程图...")
fig, ax = plt.subplots(figsize=(16, 12))
fig.patch.set_facecolor(phase_colors['background']) # 设置画布背景

# --- 步骤A: 绘制阶段背景框 ---
phase_boxes = {
    '输入': {'pos': (-4, 4.2), 'width': 8, 'height': 0.9, 'color': phase_colors['input_output']},
    '并行情报分析': {'pos': (-4, 2.4), 'width': 8, 'height': 1.5, 'color': phase_colors['analysis']},
    '批判性审查': {'pos': (-4, 1.2), 'width': 8, 'height': 0.9, 'color': phase_colors['review']},
    '综合评估与决策': {'pos': (-4, -0.6), 'width': 8, 'height': 0.9, 'color': phase_colors['decision']},
    '输出': {'pos': (-4, -1.8), 'width': 8, 'height': 0.9, 'color': phase_colors['input_output']},
}

for title, box_props in phase_boxes.items():
    rect = patches.Rectangle(
        box_props['pos'], box_props['width'], box_props['height'],
        linewidth=1.5, 
        edgecolor=phase_colors['border'], 
        facecolor=box_props['color'],
        alpha=0.6,
        linestyle='--',
        zorder=0 # 确保背景框在最底层
    )
    ax.add_patch(rect)
    # 添加阶段标题
    ax.text(box_props['pos'][0] + 0.2, box_props['pos'][1] + box_props['height']/2, 
            title, fontproperties=my_font, fontsize=14, 
            color=phase_colors['font'], va='center', ha='left', alpha=0.8)

# --- 步骤B: 绘制边/箭头 ---
nx.draw_networkx_edges(G, pos, ax=ax,
                       width=1.5,
                       edge_color=phase_colors['arrow'],
                       arrows=True,
                       arrowstyle='-|>',
                       arrowsize=20,
                       connectionstyle="arc3,rad=0.05")

# --- 步骤C: 绘制节点标签 (使用 bbox 实现卡片效果) ---
node_styles = {
    "start": {"boxstyle": "round,pad=0.5", "facecolor": "#FFFFFF", "edgecolor": phase_colors['arrow']},
    "end": {"boxstyle": "round,pad=0.5", "facecolor": "#FFFFFF", "edgecolor": phase_colors['arrow']},
    "default": {"boxstyle": "round,pad=0.5", "facecolor": "#FFFFFF", "edgecolor": phase_colors['arrow']}
}

for node, text in nodes.items():
    style = node_styles.get(node, node_styles["default"])
    nx.draw_networkx_labels(G, pos, labels={node: text}, ax=ax,
                            font_size=11,
                            font_color=phase_colors['font'],
                            bbox=style)

# --- 5. 美化并保存图形 ---
ax.set_title("多智能体协作流程图", fontsize=24, pad=20, color=phase_colors['font'])
ax.axis('off') # 移除坐标轴
plt.tight_layout()

output_filename = "multi_agent_workflow_journal_quality.png"
plt.savefig(output_filename, dpi=300, facecolor=phase_colors['background'], bbox_inches='tight')
print(f"期刊级流程图已成功生成并保存为 '{output_filename}'")

plt.show()

# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# --- END: 全新的“期刊级”绘图代码 ---
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^