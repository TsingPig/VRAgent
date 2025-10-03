import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
def plot_coverage_chart(coverage_type, filename_suffix):
    """创建单个覆盖率图表 -            # 如果值是100.00，使用更小的字体
            if value == 100.00:
                font_size = data_label_fontsize_100  # 更小的字体
            else:
                font_size = data_label_fontsize  # 正常字体
                
            ax.text(bar.get_x() + bar.get_width()/2., height + 1.8,
                    f'{value:.2f}', ha='center', va='bottom', 
                    fontsize=font_size, fontweight=font_weight, color=label_color,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', 
                             alpha=0.8, edgecolor='none'))""
    # 图表配置参数
    fig_w, fig_h = 16, 10  # 图表宽度和高度
    bar_width = 0.22  # 柱子宽度
    project_name_fontsize = 10  # 项目名字体大小
    project_name_rotation = 15  # 项目名旋转角度
    data_label_fontsize = 11  # 数据标签字体大小
    data_label_fontsize_100 = 9  # 100%时的数据标签字体大小
    legend_fontsize = 10  # 图例字体大小
    legend_title_fontsize = 11  # 图例标题字体大小
    title_fontsize = 16  # 主标题字体大小
    axis_label_fontsize = 14  # 轴标签字体大小
    
    # 瘦高的比例 - 适合12个项目
    fig, ax = plt.subplots(figsize=(fig_w, fig_h)), _h = 18, 4  # 图表宽高比例

# 数据 - Group 1 (原始数据) + Group 2 (新增数据)
data = {
    'Project': [
        # Group 1 - 原始4个项目
        'unity-vr-maze', 'unity-vr-maze', 'unity-vr-maze',
        'UnityCityView', 'UnityCityView', 'UnityCityView',
        'UnityVR', 'UnityVR', 'UnityVR',
        'escapeVr', 'escapeVr', 'escapeVr',
        # Group 2 - 新增8个项目
        'VR-Basics', 'VR-Basics', 'VR-Basics',
        'VR-Room', 'VR-Room', 'VR-Room',
        'VGuns', 'VGuns', 'VGuns',
        'VR-Adventure', 'VR-Adventure', 'VR-Adventure',
        'EE-Room', 'EE-Room', 'EE-Room',
        'EscapeGameVR', 'EscapeGameVR', 'EscapeGameVR',
        'Parkinson-VR', 'Parkinson-VR', 'Parkinson-VR',
        'VRChess', 'VRChess', 'VRChess'
    ],
    'Method': ['VRGuide', 'VRExplorer', 'VRAgent'] * 12,  # 12个项目
    'LineCoverage': [
        # Group 1 数据 (EC = Edge Coverage, 对应LineCoverage)
        66.53, 81.67, 84.86,        # maze
        67.66, 92.22, 93.08,        # UnityCityView
        64.81, 75.93, 85.19,        # UnityVR
        70.75, 84.91, 100.00,       # escapeVr
        # Group 2 数据 (VRAgent暂时用100%代替)
        41.38, 80.17, 100.00,       # VR-Basics
        40.97, 77.61, 100.00,       # VR-Room
        28.68, 77.57, 100.00,       # VGuns
        54.12, 91.76, 100.00,       # VR-Adventure
        38.08, 70.61, 100.00,       # EE-Room
        41.77, 71.08, 100.00,       # EscapeGameVR
        42.03, 95.65, 100.00,       # Parkinson-VR
        10.74, 71.74, 100.00        # VRChess
    ],
    'MethodCoverage': [
        # Group 1 数据 (MC = Method Coverage)
        70.59, 82.35, 85.29,        # maze
        78.38, 100.0, 100.0,        # UnityCityView
        84.62, 92.31, 92.31,        # UnityVR
        84.21, 84.21, 100.0,        # escapeVr
        # Group 2 数据 (VRAgent暂时用100%代替)
        53.22, 91.93, 100.00,       # VR-Basics
        50.63, 83.54, 100.00,       # VR-Room
        38.89, 77.78, 100.00,       # VGuns
        65.00, 95.00, 100.00,       # VR-Adventure
        58.06, 88.17, 100.00,       # EE-Room
        55.26, 73.68, 100.00,       # EscapeGameVR
        53.85, 100.00, 100.00,      # Parkinson-VR
        50.88, 87.72, 100.00        # VRChess
    ]
} 

df = pd.DataFrame(data)

# 所有项目按顺序排列 - 总共12个项目
all_projects = ['unity-vr-maze', 'UnityCityView', 'UnityVR', 'escapeVr',
                'VR-Basics', 'VR-Room', 'VGuns', 'VR-Adventure', 
                'EE-Room', 'EscapeGameVR', 'Parkinson-VR', 'VRChess']
methods = ['VRGuide', 'VRExplorer', 'VRAgent']

# 使用顶级会议风格的专业配色 - 参考ICSE/NeurIPS等
colors = {
    'VRGuide': ['#FF6B6B', '#FF8E8E'],     # 珊瑚红渐变 (基线方法)
    'VRExplorer': ['#4ECDC4', '#6BCF7F'],  # 青绿渐变 (对比方法)
    'VRAgent': ['#3742FA', '#5352ED']      # 深蓝紫渐变 (我们的方法，突出色)
}

def plot_coverage_chart(coverage_type, filename_suffix):
    """创建单个覆盖率图表 - 显示所有12个项目"""
    # 图表配置参数
    fig_w, fig_h = 16, 10  # 图表宽度和高度
    bar_width = 0.22  # 柱子宽度
    project_name_fontsize = 10  # 项目名字体大小
    project_name_rotation = 15  # 项目名旋转角度
    data_label_fontsize = 11  # 数据标签字体大小
    data_label_fontsize_100 = 9  # 100%时的数据标签字体大小
    legend_fontsize = 10  # 图例字体大小
    legend_title_fontsize = 11  # 图例标题字体大小
    title_fontsize = 16  # 主标题字体大小
    axis_label_fontsize = 14  # 轴标签字体大小
    
    # 瘦高的比例 - 适合12个项目
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    
    # 创建数据透视表
    pivot_data = df.pivot(index='Project', columns='Method', values=coverage_type)
    pivot_data = pivot_data.reindex(all_projects)  # 按指定顺序排列项目
    
    n_projects = len(all_projects)
    x = np.arange(n_projects) * 1.0  # 紧凑一些的间距
    
    # 为每个方法绘制柱状图 - 使用渐变色
    for i, method in enumerate(methods):
        values = pivot_data[method].values
        positions = x + (i - 1) * bar_width  # 居中对齐
        
        # 创建渐变色效果
        from matplotlib.colors import LinearSegmentedColormap
        
        # 为不同方法设置不同的视觉效果 - 使用图案和颜色组合
        if method == 'VRAgent':
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
        
        bars = ax.bar(positions, values, bar_width, label=method, 
                     color=bar_color, alpha=alpha, edgecolor=edgecolor, 
                     linewidth=linewidth, hatch=hatch)
        
        # 为VRAgent添加轻微的阴影效果突出重要性
        if method == 'VRAgent':
            shadow_bars = ax.bar(positions + 0.015, values, bar_width, 
                               color='#1B4F72', alpha=0.15, zorder=bars[0].zorder-1)
        
        # 添加数值标签 - 保留两位小数，使用更好的字体和颜色
        for bar, value in zip(bars, values):
            height = bar.get_height()
            # 根据方法使用不同的标签颜色
            if method == 'VRAgent':
                label_color = '#2C3E50'
                font_weight = 'bold'
            else:
                label_color = '#34495E'
                font_weight = 'semibold'
            
            # 如果值是100.00，使用更小的字体
            if value == 100.00:
                font_size = 8.5  # 更小的字体
            else:
                font_size = 9.5  # 正常字体
                
            ax.text(bar.get_x() + bar.get_width()/2., height + 1.8,
                    f'{value:.2f}', ha='center', va='bottom', 
                    fontsize=font_size, fontweight=font_weight, color=label_color,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', 
                             alpha=0.8, edgecolor='none'))
    
    # 设置图表属性
    ax.set_ylim(0, 115)  # 留出更多空间给标签
    ax.set_ylabel(f'{coverage_type.replace("Coverage", "")} Coverage (%)', 
                  fontsize=axis_label_fontsize, fontweight='bold', color='#2C3E50')
    ax.set_xlabel('Projects', fontsize=axis_label_fontsize, fontweight='bold', color='#2C3E50')
    
    # 专业标题 - 顶级会议风格
    coverage_name = 'Line' if 'Line' in coverage_type else 'Method'
    ax.set_title(f'{coverage_name} Coverage Comparison of VR Testing Approaches', 
                fontsize=title_fontsize, fontweight='bold', pad=30, color='#1B263B',
                fontfamily='serif')
    
    ax.set_xticks(x)
    ax.set_xticklabels(all_projects, fontsize=project_name_fontsize, color='#2C3E50', rotation=project_name_rotation, ha='right')
    
    # 图例放在右下角
    legend = ax.legend(title='Approaches', loc='lower right', frameon=True, 
                      fancybox=False, shadow=True, fontsize=legend_fontsize,
                      bbox_to_anchor=(0.98, 0.02), framealpha=0.95,
                      edgecolor='#34495E', facecolor='#FFFFFF')
    legend.get_title().set_fontweight('bold')
    legend.get_title().set_fontsize(legend_title_fontsize)
    legend.get_title().set_color('#2C3E50')
    
    # 设置图例中每个条目的图案和颜色，与柱状图保持一致
    legend_colors = {'VRAgent': '#2E86AB', 'VRExplorer': '#A23B72', 'VRGuide': '#F18F01'}
    legend_hatches = {'VRAgent': None, 'VRExplorer': '///', 'VRGuide': '...'}
    
    for method, legend_handle in zip(methods, legend.legend_handles):  # 使用新的属性名
        legend_handle.set_color(legend_colors[method])
        legend_handle.set_hatch(legend_hatches[method])
        legend_handle.set_edgecolor('#2C3E50')
        legend_handle.set_linewidth(1.5)
        legend_handle.set_alpha(0.9 if method == 'VRAgent' else 0.8)
    
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
    ax.tick_params(axis='y', labelsize=11, colors='#2C3E50')
    ax.tick_params(axis='x', labelsize=12, colors='#2C3E50')
    
    plt.tight_layout()
    plt.savefig(f'{coverage_name.lower()}_coverage_comparison_all.png', dpi=300, bbox_inches='tight')
    plt.show()

# 绘制合并后的图表 - 所有12个项目
print("生成 Line Coverage 图表 (所有12个项目)...")
plot_coverage_chart('LineCoverage', 'line')

print("生成 Method Coverage 图表 (所有12个项目)...")
plot_coverage_chart('MethodCoverage', 'method')
