import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# 全局配置参数
FIG_W, FIG_H = 22, 10
BAR_WIDTH = 0.25
PROJECT_NAME_FONTSIZE = 16.4
DATA_LABEL_FONTSIZE = 12
DATA_LABEL_FONTSIZE_100 = 11
LEGEND_FONTSIZE = 14
TITLE_FONTSIZE = 16
AXIS_LABEL_FONTSIZE = 14
AXIS_TICK_FONTSIZE = 14
AGENT_NAME = 'VRAgent'

SHOW_DATA_LABELS = True

# 数据
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
        66.53, 81.67, 84.86,
        67.66, 92.22, 93.08,
        64.81, 75.93, 85.19,
        70.75, 84.91, 100.00,
        38.08, 70.61, 62.66,
        28.68, 77.57, 75.74,
        40.97, 77.61, 77.86,
        42.03, 95.65, 95.65,
        40.97, 78.95, 82.43
    ],
    'MethodCoverage': [
        70.59, 82.35, 85.29,
        78.38, 100.00, 100.00,
        84.62, 92.31, 92.31,
        84.21, 84.21, 100.00,
        58.06, 88.17, 88.17,
        38.89, 77.78, 72.22,
        50.63, 83.54, 83.54,
        53.85, 100.00, 100.00,
        50.63, 84.92, 92.06
    ]
}

df = pd.DataFrame(data)

all_projects = [
    'maze', 'UnityCityView', 'UnityVR', 'escapeVr',
    'EE-Room', 'VGuns', 'VR-Room', 'Parkinson-VR', 'VR-Basics'
]

methods = ['VRGuide', 'VRExplorer', AGENT_NAME]

# -----------------------------
# 修改点：统一低调颜色 + 线型/标记区分
# -----------------------------
method_colors = {
    'VRGuide': '#959595',      # 中灰
    'VRExplorer': '#757575',
    AGENT_NAME: '#545454'
}

method_styles = {
    'VRGuide': {'linestyle': '--',  'marker': 'o'},
    'VRExplorer': {'linestyle': '-', 'marker': 's'},
    AGENT_NAME: {'linestyle': '-.', 'marker': 'x'}
}

def plot_butterfly_chart():
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['font.weight'] = 'normal'
    
    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(FIG_W, FIG_H))
    
    pivot_line = df.pivot(index='Project', columns='Method', values='LineCoverage').reindex(all_projects)
    pivot_method = df.pivot(index='Project', columns='Method', values='MethodCoverage').reindex(all_projects)
    
    n_projects = len(all_projects)
    x = np.arange(n_projects)
    
    # 左图：Line Coverage
    for i, method in enumerate(methods):
        values = pivot_line[method].values
        positions = x + (i - 1) * BAR_WIDTH
        
        bars = ax_left.barh(positions, -values, BAR_WIDTH,
                            color=method_colors[method],
                            edgecolor='black', linewidth=1.2,
                            label=method, alpha=0.85)
        
        # 添加标记线
        ax_left.plot(-values, positions,
                     color='black',
                     linestyle=method_styles[method]['linestyle'],
                     marker=method_styles[method]['marker'],
                     markersize=6)
        
        # 数据标签
        if SHOW_DATA_LABELS:
            for bar, value in zip(bars, values):
                width = bar.get_width()
                y_pos = bar.get_y() + bar.get_height()/2
                font_size = DATA_LABEL_FONTSIZE_100 if value==100 else DATA_LABEL_FONTSIZE
                ax_left.text(width - 2, y_pos, f'{value:.1f}%', va='center', ha='right',
                             fontsize=font_size, fontweight='semibold', color='#2D3436')
    
    # 右图：Method Coverage
    for i, method in enumerate(methods):
        values = pivot_method[method].values
        positions = x + (i - 1) * BAR_WIDTH
        
        bars = ax_right.barh(positions, values, BAR_WIDTH,
                             color=method_colors[method],
                             edgecolor='black', linewidth=1.2,
                             label=method, alpha=0.85)
        
        # 添加标记线
        ax_right.plot(values, positions,
                      color='black',
                      linestyle=method_styles[method]['linestyle'],
                      marker=method_styles[method]['marker'],
                      markersize=6)
        
        # 数据标签
        if SHOW_DATA_LABELS:
            for bar, value in zip(bars, values):
                width = bar.get_width()
                y_pos = bar.get_y() + bar.get_height()/2
                font_size = DATA_LABEL_FONTSIZE_100 if value==100 else DATA_LABEL_FONTSIZE
                ax_right.text(width + 2, y_pos, f'{value:.1f}%', va='center', ha='left',
                              fontsize=font_size, fontweight='semibold', color='#2D3436')
    
    # 左图设置
    ax_left.set_xlim(-110, 0)
    ax_left.set_xlabel('Line Coverage (%)', fontsize=AXIS_LABEL_FONTSIZE, fontweight='bold', color='#2D3436', labelpad=15)
    ax_left.set_ylabel('Projects', fontsize=AXIS_LABEL_FONTSIZE, fontweight='bold', color='#2D3436', labelpad=15)
    ax_left.set_yticks(x)
    ax_left.set_yticklabels(all_projects, fontsize=PROJECT_NAME_FONTSIZE, fontweight='medium', color='#2D3436')
    ax_left.set_xticks([-100, -80, -60, -40, -20, 0])
    ax_left.set_xticklabels(['100','80','60','40','20','0'], fontsize=AXIS_TICK_FONTSIZE, color='#2D3436')
    
    # 右图设置
    ax_right.set_xlim(0, 110)
    ax_right.set_xlabel('Method Coverage (%)', fontsize=AXIS_LABEL_FONTSIZE, fontweight='bold', color='#2D3436', labelpad=15)
    ax_right.set_yticks(x)
    ax_right.set_yticklabels([])
    
    # 标题
    ax_left.set_title('Line Coverage', fontsize=TITLE_FONTSIZE, fontweight='bold', color='#2D3436', pad=20)
    ax_right.set_title('Method Coverage', fontsize=TITLE_FONTSIZE, fontweight='bold', color='#2D3436', pad=20)
    
    # 网格和背景
    for ax in [ax_left, ax_right]:
        ax.grid(True, alpha=0.15, axis='x', linestyle='-', linewidth=0.8)
        ax.set_facecolor('#F8F9FA')
        for spine in ax.spines.values():
            spine.set_color('#BDC3C7')
            spine.set_linewidth(1.5)
    
    # 中心分隔线
    ax_left.axvline(x=-100, color='#E74C3C', linestyle='--', alpha=0.3, linewidth=1)
    ax_right.axvline(x=100, color='#E74C3C', linestyle='--', alpha=0.3, linewidth=1)
    
    # 图例
    handles, labels = ax_left.get_legend_handles_labels()
    legend = fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 0.95),
                        ncol=3, fontsize=LEGEND_FONTSIZE, frameon=True, fancybox=True,
                        shadow=True, framealpha=0.95, edgecolor='#BDC3C7')
    legend.set_title('Testing Methods', prop={'size': LEGEND_FONTSIZE+1, 'weight':'bold'})
    
    plt.tight_layout()
    plt.subplots_adjust(top=0.90, bottom=0.08, wspace=0.15)
    fig.suptitle('Coverage Comparison: Line vs Method Coverage', fontsize=18, fontweight='bold', color='#2C3E50', y=0.98)
    
    plt.savefig('butterfly_coverage_chart_minimal.png', dpi=300, bbox_inches='tight', facecolor='white')
    plt.show()

print("生成低调线条/标记区分蝴蝶图...")
plot_butterfly_chart()
