import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# 全局配置参数
FIG_W, FIG_H = 17, 4.5  # 图表宽度和高度
BAR_WIDTH = 0.27  # 柱子宽度
PROJECT_NAME_FONTSIZE = 13.5  # 项目名字体大小
PROJECT_NAME_ROTATION = 10  # 项目名旋转角度
DATA_LABEL_FONTSIZE = 10  # 数据标签字体大小
DATA_LABEL_FONTSIZE_100 = 9  # 100%时的数据标签字体大小
LEGEND_FONTSIZE = 13  # 图例字体大小
LEGEND_TITLE_FONTSIZE = 16  # 图例标题字体大小
TITLE_FONTSIZE = 18  # 主标题字体大小
AXIS_LABEL_FONTSIZE = 11  # 轴标签字体大小
AXIS_TICK_FONTSIZE = 12  # 轴刻度字体大小
AGENT_NAME = 'VRAgent'   # 我们的方法名称

# 显示控制参数
SHOW_DATA_LABELS = True  # 是否显示数据标签（一键隐藏/显示）

# 数据 - Group 1 (原始数据) + Group 2 (新增数据)
data = {
    'Project': [
        'maze', 'maze', 'maze',
        'UnityCityView', 'UnityCityView', 'UnityCityView',
        'UnityVR', 'UnityVR', 'UnityVR',
        'escapeVr', 'escapeVr', 'escapeVr',
        'EE-Room', 'EE-Room', 'EE-Room',
        'VGuns', 'VGuns', 'VGuns',
        'VR-Room', 'VR-Room', 'VR-Room',
        'Parkinson-VR', 'Parkinson-VR', 'Parkinson-VR',
        'VR-Basics', 'VR-Basics', 'VR-Basics'
    ],
    'Method': ['VRGuide', 'VRExplorer', AGENT_NAME] * 9,
    'LineCoverage': [
        66.53, 81.67, 84.86,       # maze
        67.66, 92.22, 93.08,       # UnityCityView
        64.81, 75.93, 85.19,       # UnityVR
        70.75, 84.91, 100.00,      # escapeVr
        38.08, 70.61, 62.66,       # EE-Room
        28.68, 77.57, 75.74,       # VGuns
        40.97, 77.61, 77.86,       # VR-Room
        42.03, 95.65, 95.65,       # Parkinson-VR
        40.97, 78.95, 82.43        # VR-Basics
    ],
    'MethodCoverage': [
        70.59, 82.35, 85.29,       # maze
        78.38, 100.00, 100.00,     # UnityCityView
        84.62, 92.31, 92.31,       # UnityVR
        84.21, 84.21, 100.00,      # escapeVr
        58.06, 88.17, 88.17,       # EE-Room
        38.89, 77.78, 72.22,       # VGuns
        50.63, 83.54, 83.54,       # VR-Room
        53.85, 100.00, 100.00,     # Parkinson-VR
        50.63, 84.92, 92.06        # VR-Basics
    ]
}


df = pd.DataFrame(data)

# 所有项目按顺序排列 - 总共9个项目
all_projects = [
    'maze', 'UnityCityView', 'UnityVR', 'escapeVr',
    'EE-Room', 'VGuns', 'VR-Room', 'Parkinson-VR', 'VR-Basics'
]

methods = ['VRGuide', 'VRExplorer', AGENT_NAME]

# 使用顶级会议风格的专业配色 - 参考ICSE/NeurIPS等
colors = {
    'VRGuide': ['#FF6B6B', '#FF8E8E'],     # 珊瑚红渐变 (基线方法)
    'VRExplorer': ['#4ECDC4', '#6BCF7F'],  # 青绿渐变 (对比方法)
    AGENT_NAME: ['#3742FA', '#5352ED']      # 深蓝紫渐变 (我们的方法，突出色)
}

def plot_coverage_chart(coverage_type, filename_suffix):
    """创建单个覆盖率图表 - 显示所有12个项目"""
    # 瘦高的比例 - 适合12个项目
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
    
    # 创建数据透视表
    pivot_data = df.pivot(index='Project', columns='Method', values=coverage_type)
    pivot_data = pivot_data.reindex(all_projects)  # 按指定顺序排列项目
    
    n_projects = len(all_projects)
    x = np.arange(n_projects) * 1.0  # 紧凑一些的间距
    
    # 收集所有标签信息用于防重叠处理
    label_info = []
    all_bars = []
    
    # 为每个方法绘制柱状图 - 使用渐变色
    for i, method in enumerate(methods):
        values = pivot_data[method].values
        positions = x + (i - 1) * BAR_WIDTH  # 居中对齐
        
        # 创建渐变色效果
        from matplotlib.colors import LinearSegmentedColormap
        
        # 为不同方法设置不同的视觉效果 - 使用图案和颜色组合
        if method == AGENT_NAME:
            # 我们的方法 - 实心 + 深色
            bar_color = '#2E86AB'  # 专业蓝
            alpha = 0.9
            edgecolor = '#1B4F72'
            linewidth = 2.0
            hatch = None  # 实心，突出重要性
        elif method == 'VRExplorer':
            # 对比方法 - 斜线图案
            bar_color = '#A23B72'  # 深紫红
            alpha = 0.8
            edgecolor = '#6C2C5F'
            linewidth = 1.5
            hatch = '///'  # 斜线图案
        else:  # VRGuide - 基线方法 - 点图案
            bar_color = '#F18F01'  # 橙色
            alpha = 0.7
            edgecolor = '#B8690C'
            linewidth = 1.0
            hatch = '...'  # 点图案
        
        bars = ax.bar(positions, values, BAR_WIDTH, label=method, 
                     color=bar_color, alpha=alpha, edgecolor=edgecolor, 
                     linewidth=linewidth, hatch=hatch)
        
        # 为VRAgent添加轻微的阴影效果突出重要性
        if method == AGENT_NAME:
            shadow_bars = ax.bar(positions + 0.015, values, BAR_WIDTH, 
                               color='#1B4F72', alpha=0.15, zorder=bars[0].zorder-1)
        
        # 收集标签信息而不直接绘制
        if SHOW_DATA_LABELS:
            for j, (bar, value) in enumerate(zip(bars, values)):
                height = bar.get_height()
                x_pos = bar.get_x() + bar.get_width()/2.
                
                # 根据方法使用不同的标签颜色
                if method == AGENT_NAME:
                    label_color = '#2C3E50'
                    font_weight = 'bold'
                else:
                    label_color = '#34495E'
                    font_weight = 'semibold'
                
                # 如果值是100.00，使用更小的字体
                if value == 100.00:
                    font_size = DATA_LABEL_FONTSIZE_100
                else:
                    font_size = DATA_LABEL_FONTSIZE
                
                # 存储标签信息
                label_info.append({
                    'x': x_pos,
                    'y': height + 1.8,
                    'text': f'{value:.2f}',
                    'color': label_color,
                    'fontsize': font_size,
                    'fontweight': font_weight,
                    'project_idx': j,
                    'method_idx': i,
                    'original_y': height + 1.8
                })
        
        all_bars.extend(bars)
    
    # 智能防重叠标签处理
    if SHOW_DATA_LABELS and label_info:
        # 按项目分组处理重叠
        for proj_idx in range(n_projects):
            # 获取当前项目的所有标签
            current_project_labels = [label for label in label_info if label['project_idx'] == proj_idx]
            current_project_labels.sort(key=lambda x: x['y'])  # 按y坐标排序
            
            # 检测和调整重叠
            min_distance = 4.5  # 最小间距
            for i in range(1, len(current_project_labels)):
                prev_label = current_project_labels[i-1]
                curr_label = current_project_labels[i]
                
                # 如果距离太近，调整当前标签位置
                if curr_label['y'] - prev_label['y'] < min_distance:
                    curr_label['y'] = prev_label['y'] + min_distance
            
            # 绘制调整后的标签
            for label in current_project_labels:
                ax.text(label['x'], label['y'], label['text'],
                       ha='center', va='bottom', 
                       fontsize=label['fontsize'], 
                       fontweight=label['fontweight'], 
                       color=label['color'])
    
    # 设置图表属性
    ax.set_ylim(0, 115)  # 留出更多空间给标签
    ax.set_ylabel(f'{coverage_type.replace("Coverage", "")} Coverage (%)', 
                  fontsize=AXIS_LABEL_FONTSIZE, fontweight='bold', color='#2C3E50')
    
    # 专业标题 - 顶级会议风格
    coverage_name = 'Line' if 'Line' in coverage_type else 'Method'
    # ax.set_title(f'{coverage_name} Coverage Comparison of VR Testing Approaches', 
    #             fontsize=TITLE_FONTSIZE, fontweight='bold', pad=30, color='#1B263B',
    #             fontfamily='serif')
    
    ax.set_xticks(x)
    ax.set_xticklabels(all_projects, fontsize=PROJECT_NAME_FONTSIZE, color='#2C3E50', rotation=PROJECT_NAME_ROTATION, ha='right')
    
    # 图例横着一排放在左下角
    legend = ax.legend(title='', loc='lower left', frameon=True, 
                      fancybox=False, shadow=True, fontsize=LEGEND_FONTSIZE,
                      bbox_to_anchor=(0.0, 0.0), framealpha=0.95,
                      edgecolor='#34495E', facecolor='#FFFFFF', ncol=3)
    # 图例标题已设为空字符串，无需设置标题样式
    
    # 设置图例中每个条目的图案和颜色，与柱状图保持一致
    legend_colors = {AGENT_NAME: '#2E86AB', 'VRExplorer': '#A23B72', 'VRGuide': '#F18F01'}
    legend_hatches = {AGENT_NAME: None, 'VRExplorer': '///', 'VRGuide': '...'}
    
    for method, legend_handle in zip(methods, legend.legend_handles):  # 使用新的属性名
        legend_handle.set_color(legend_colors[method])
        legend_handle.set_hatch(legend_hatches[method])
        legend_handle.set_edgecolor('#2C3E50')
        legend_handle.set_linewidth(1.5)
        legend_handle.set_alpha(0.9 if method == AGENT_NAME else 0.8)
    
    # 精致的网格线 - IEEE/ACM期刊风格
    ax.grid(True, alpha=0.15, axis='y', linestyle='-', linewidth=0.5, color='#D5DBDB')
    ax.set_axisbelow(True)
    
    # 添加轻微的背景色
    ax.set_facecolor('#FDFEFE')
    
    # 隐藏顶部和右边的边框，保留底部和左边
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['left'].set_color('#95A5A6')
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['bottom'].set_color('#95A5A6')
    
    # 美化y轴刻度
    ax.tick_params(axis='y', labelsize=AXIS_TICK_FONTSIZE, colors='#2C3E50')
    ax.tick_params(axis='x', labelsize=PROJECT_NAME_FONTSIZE, colors='#2C3E50')
    
    plt.tight_layout()
    plt.savefig(f'{coverage_name.lower()}_coverage_comparison_all.png', dpi=300, bbox_inches='tight')
    plt.show()

# 绘制合并后的图表 - 所有12个项目
print("生成 Line Coverage 图表 (所有12个项目)...")
plot_coverage_chart('LineCoverage', 'line')

print("生成 Method Coverage 图表 (所有12个项目)...")
plot_coverage_chart('MethodCoverage', 'method')