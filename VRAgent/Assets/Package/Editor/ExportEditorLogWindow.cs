using UnityEditor;
using UnityEngine;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System;

public class ExportEditorLogWindow : EditorWindow
{
    private string outputDirectory = "";
    private bool exportLog = true;
    private bool exportWarning = true;
    private bool exportError = true;
    private string messagePrefix = "";

    private static readonly List<LogRecord> logs = new();

    [MenuItem("Tools/VR Explorer/Export Console (Simple)")]
    public static void ShowWindow()
    {
        var window = GetWindow<ExportEditorLogWindow>("导出控制台日志");
        window.minSize = new Vector2(400, 300);
        window.Show();
    }

    private void OnEnable()
    {
        outputDirectory = Application.dataPath.Replace("/Assets", "");

        // 注册日志回调，只在编辑器运行时生效
        Application.logMessageReceivedThreaded -= HandleLog;
        Application.logMessageReceivedThreaded += HandleLog;
    }

    private void OnDisable()
    {
        Application.logMessageReceivedThreaded -= HandleLog;
    }

    private void OnGUI()
    {
        GUILayout.Label("控制台日志导出", EditorStyles.boldLabel);
        GUILayout.Space(10);

        EditorGUILayout.BeginHorizontal();
        EditorGUILayout.LabelField("输出目录:", GUILayout.Width(70));
        outputDirectory = EditorGUILayout.TextField(outputDirectory);
        if(GUILayout.Button("浏览", GUILayout.Width(60)))
        {
            string selected = EditorUtility.OpenFolderPanel("选择输出目录", outputDirectory, "");
            if(!string.IsNullOrEmpty(selected))
                outputDirectory = selected;
        }
        EditorGUILayout.EndHorizontal();

        GUILayout.Space(10);
        messagePrefix = EditorGUILayout.TextField("消息前缀:", messagePrefix);
        EditorGUILayout.HelpBox("留空表示不过滤，仅导出 Console 显示内容，不含堆栈。", MessageType.Info);

        GUILayout.Space(10);
        exportLog = EditorGUILayout.ToggleLeft("普通日志 (Log)", exportLog);
        exportWarning = EditorGUILayout.ToggleLeft("警告 (Warning)", exportWarning);
        exportError = EditorGUILayout.ToggleLeft("错误 (Error)", exportError);

        GUILayout.Space(20);

        GUI.enabled = logs.Count > 0;
        if(GUILayout.Button($"导出为 HTML ({logs.Count} 条)", GUILayout.Height(40)))
        {
            ExportToHtml();
        }
        GUI.enabled = true;

        GUILayout.Space(10);
        if(GUILayout.Button("清空缓存"))
        {
            logs.Clear();
        }
    }

    private void HandleLog(string message, string stackTrace, LogType type)
    {
        lock(logs)
        {
            logs.Add(new LogRecord
            {
                Time = DateTime.Now,
                Type = type,
                Message = message
            });
        }
    }

    private void ExportToHtml()
    {
        try
        {
            var filtered = logs.FindAll(l =>
            {
                if(!string.IsNullOrWhiteSpace(messagePrefix) && !l.Message.StartsWith(messagePrefix))
                    return false;

                return (l.Type == LogType.Log && exportLog)
                    || (l.Type == LogType.Warning && exportWarning)
                    || ((l.Type == LogType.Error || l.Type == LogType.Exception) && exportError);
            });

            if(filtered.Count == 0)
            {
                EditorUtility.DisplayDialog("提示", "没有符合条件的日志。", "确定");
                return;
            }

            string html = GenerateHtml(filtered);
            string filename = $"ConsoleLog_{DateTime.Now:yyyyMMdd_HHmmss}.html";
            string path = Path.Combine(outputDirectory, filename);
            File.WriteAllText(path, html, Encoding.UTF8);
            EditorUtility.RevealInFinder(path);

            Debug.Log($"✅ 成功导出 {filtered.Count} 条日志到: {path}");
        }
        catch(Exception ex)
        {
            Debug.LogError($"导出失败: {ex}");
        }
    }

    private string GenerateHtml(List<LogRecord> list)
    {
        var sb = new StringBuilder();
        sb.AppendLine("<html><head><meta charset='utf-8'><style>");
        sb.AppendLine("body{font-family:Consolas;background:#1e1e1e;color:#d4d4d4;padding:20px;}");
        sb.AppendLine("h2{color:#61dafb;}");
        sb.AppendLine(".log{color:#4ec9b0;}");
        sb.AppendLine(".warn{color:#f9d23b;}");
        sb.AppendLine(".err{color:#ff6b6b;}");
        sb.AppendLine(".day-header{margin-top:30px;padding:8px;background:#333;border-radius:6px;font-size:16px;font-weight:bold;}");
        sb.AppendLine(".entry{margin:4px 0;line-height:1.4em;}");
        sb.AppendLine("</style></head><body>");
        sb.AppendLine($"<h2>Unity Console Export ({DateTime.Now:yyyy-MM-dd HH:mm:ss})</h2>");
        sb.AppendLine("<hr>");

        // 按日期分组
        var byDay = new SortedDictionary<string, List<LogRecord>>();
        foreach(var l in list)
        {
            string day = l.Time.ToString("yyyy-MM-dd");
            if(!byDay.ContainsKey(day))
                byDay[day] = new List<LogRecord>();
            byDay[day].Add(l);
        }

        foreach(var kv in byDay)
        {
            sb.AppendLine($"<div class='day-header'>📅 {kv.Key}</div>");
            foreach(var l in kv.Value)
            {
                string cls = l.Type == LogType.Warning ? "warn" :
                             (l.Type == LogType.Error || l.Type == LogType.Exception ? "err" : "log");

                // 不转义 Unity 的 <color> 标签
                string msg = EscapeExceptColor(l.Message);

                sb.AppendLine($"<div class='entry {cls}'><b>[{l.Time:HH:mm:ss}] [{l.Type}]</b> {msg}</div>");
            }
        }

        sb.AppendLine("</body></html>");
        return sb.ToString();
    }

    /// <summary>
    /// 转义 HTML 特殊字符，但保留 Unity 的 <color=...> 标签
    /// </summary>
    private string EscapeExceptColor(string text)
    {
        if(string.IsNullOrEmpty(text)) return "";

        // 先转义
        text = text.Replace("&", "&amp;")
                   .Replace("<", "&lt;")
                   .Replace(">", "&gt;");

        // 再恢复 Unity 的 <color> 标签
        text = System.Text.RegularExpressions.Regex.Replace(text,
            "&lt;color=([^&]*)&gt;", "<color=$1>");
        text = text.Replace("&lt;/color&gt;", "</color>");

        // 处理 Unity 的 color 标签为 HTML span
        text = System.Text.RegularExpressions.Regex.Replace(text,
            "<color=([^>]+)>(.*?)</color>",
            "<span style='color:$1'>$2</span>",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase | System.Text.RegularExpressions.RegexOptions.Singleline);

        return text;
    }


    private class LogRecord
    {
        public DateTime Time;
        public LogType Type;
        public string Message;
    }
}
