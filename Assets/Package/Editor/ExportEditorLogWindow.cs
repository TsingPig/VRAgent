using UnityEditor;
using UnityEngine;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text;
using System;

public class ExportEditorLogWindow : EditorWindow
{
    private string outputDirectory = "";
    private string messagePrefix = "";
    private bool exportLog = true;
    private bool exportWarning = true;
    private bool exportError = true;
    private int maxLines = 5000;

    [MenuItem("Tools/VR Explorer/Export Console (Advanced)")]
    public static void ShowWindow()
    {
        var window = GetWindow<ExportEditorLogWindow>("导出控制台日志");
        window.minSize = new Vector2(400, 300);
        window.Show();
    }

    private void OnEnable()
    {
        // 默认输出目录为项目根目录
        outputDirectory = Application.dataPath.Replace("/Assets", "");
    }

    private void OnGUI()
    {
        GUILayout.Space(10);
        GUILayout.Label("控制台日志导出工具", EditorStyles.boldLabel);
        GUILayout.Space(10);

        // 输出目录选择
        EditorGUILayout.BeginHorizontal();
        EditorGUILayout.LabelField("输出目录:", GUILayout.Width(70));
        outputDirectory = EditorGUILayout.TextField(outputDirectory);
        if (GUILayout.Button("浏览", GUILayout.Width(60)))
        {
            string selected = EditorUtility.OpenFolderPanel("选择输出目录", outputDirectory, "");
            if (!string.IsNullOrEmpty(selected))
            {
                outputDirectory = selected;
            }
        }
        EditorGUILayout.EndHorizontal();

        GUILayout.Space(10);

        // 消息前缀过滤
        EditorGUILayout.BeginHorizontal();
        EditorGUILayout.LabelField("消息前缀:", GUILayout.Width(70));
        messagePrefix = EditorGUILayout.TextField(messagePrefix, GUILayout.ExpandWidth(true));
        EditorGUILayout.EndHorizontal();
        EditorGUILayout.HelpBox("留空表示不过滤,填写后只导出以指定前缀开头的消息", MessageType.Info);

        GUILayout.Space(10);

        // 日志类型选择
        GUILayout.Label("日志类型:", EditorStyles.boldLabel);
        exportLog = EditorGUILayout.ToggleLeft("普通日志 (Log)", exportLog);
        exportWarning = EditorGUILayout.ToggleLeft("警告 (Warning)", exportWarning);
        exportError = EditorGUILayout.ToggleLeft("错误 (Error)", exportError);

        GUILayout.Space(10);

        // 注释掉最大行数设置,因为我们直接从Console读取
        // EditorGUILayout.BeginHorizontal();
        // EditorGUILayout.LabelField("最大读取行数:", GUILayout.Width(100));
        // maxLines = EditorGUILayout.IntField(maxLines, GUILayout.Width(100));
        // EditorGUILayout.EndHorizontal();
        // EditorGUILayout.HelpBox("直接从Unity Console读取所有日志条目", MessageType.Info);

        GUILayout.Space(20);

        // 导出按钮
        GUI.enabled = !string.IsNullOrEmpty(outputDirectory) && (exportLog || exportWarning || exportError);
        if (GUILayout.Button("导出为 HTML", GUILayout.Height(40)))
        {
            ExportToHtml();
        }
        GUI.enabled = true;

        GUILayout.Space(10);
    }

    private void ExportToHtml()
    {
        try
        {
            // 直接从Unity Console获取日志条目
            var logs = GetConsoleEntries();

            if (logs.Count == 0)
            {
                EditorUtility.DisplayDialog("提示", "Console中没有日志条目", "确定");
                return;
            }

            // 生成HTML
            string html = GenerateHtml(logs);

            // 保存文件
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            string filename = $"ConsoleLog_{timestamp}.html";
            string savePath = Path.Combine(outputDirectory, filename);

            File.WriteAllText(savePath, html, Encoding.UTF8);

            EditorUtility.RevealInFinder(savePath);
            Debug.Log($"✅ 成功导出 {logs.Count} 条日志到: {savePath}");
        }
        catch (Exception ex)
        {
            EditorUtility.DisplayDialog("错误", $"导出失败: {ex.Message}", "确定");
            Debug.LogError($"导出日志失败: {ex}");
        }
    }

    private List<LogEntry> GetConsoleEntries()
    {
        var logs = new List<LogEntry>();
        
        // 使用反射获取Console窗口的日志条目
        var logEntriesType = typeof(UnityEditor.EditorWindow).Assembly.GetType("UnityEditor.LogEntries");
        if (logEntriesType == null)
        {
            Debug.LogError("无法找到 LogEntries 类型");
            return logs;
        }

        // 获取日志条目数量
        var getCountMethod = logEntriesType.GetMethod("GetCount");
        if (getCountMethod == null)
        {
            Debug.LogError("无法找到 GetCount 方法");
            return logs;
        }

        int count = (int)getCountMethod.Invoke(null, null);
        
        // 获取每个日志条目
        var getEntryInternalMethod = logEntriesType.GetMethod("GetEntryInternal");
        if (getEntryInternalMethod == null)
        {
            Debug.LogError("无法找到 GetEntryInternal 方法");
            return logs;
        }

        var logEntryType = typeof(UnityEditor.EditorWindow).Assembly.GetType("UnityEditor.LogEntry");
        if (logEntryType == null)
        {
            Debug.LogError("无法找到 LogEntry 类型");
            return logs;
        }

        for (int i = 0; i < count; i++)
        {
            var logEntry = System.Activator.CreateInstance(logEntryType);
            getEntryInternalMethod.Invoke(null, new object[] { i, logEntry });

            // 获取日志属性
            var messageProperty = logEntryType.GetField("message");
            var modeProperty = logEntryType.GetField("mode");
            
            if (messageProperty != null && modeProperty != null)
            {
                string message = (string)messageProperty.GetValue(logEntry);
                int mode = (int)modeProperty.GetValue(logEntry);

                // 转换Unity的mode到LogType
                LogType logType = LogType.Log;
                if ((mode & 0x01) != 0) logType = LogType.Error;        // Error
                else if ((mode & 0x02) != 0) logType = LogType.Assert;  // Assert  
                else if ((mode & 0x10) != 0) logType = LogType.Warning; // Warning
                else if ((mode & 0x20) != 0) logType = LogType.Log;     // Log
                else if ((mode & 0x40) != 0) logType = LogType.Exception; // Exception

                // 获取堆栈跟踪信息
                var stackTrace = new List<string>();
                try
                {
                    // 尝试获取堆栈跟踪 - 使用LogEntries.GetEntryInternal的详细信息
                    var getEntryMethod = logEntriesType.GetMethod("GetLinesAndModeFromEntryInternal");
                    if (getEntryMethod != null)
                    {
                        string outString = "";
                        int outMode = 0;
                        object[] parameters = { i, 1, outString, outMode }; // 1表示获取详细信息
                        getEntryMethod.Invoke(null, parameters);
                        
                        string fullText = (string)parameters[2];
                        if (!string.IsNullOrEmpty(fullText) && fullText != message)
                        {
                            // 分割堆栈跟踪行
                            var lines = fullText.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
                            bool foundMessage = false;
                            foreach (var line in lines)
                            {
                                if (foundMessage && !string.IsNullOrWhiteSpace(line))
                                {
                                    if (line.Contains("(at ") || line.StartsWith("  at ") || line.Contains(":line "))
                                    {
                                        stackTrace.Add(line.Trim());
                                    }
                                }
                                else if (line.Trim() == message.Trim())
                                {
                                    foundMessage = true;
                                }
                            }
                        }
                    }
                }
                catch
                {
                    // 如果获取堆栈跟踪失败，就忽略
                }

                var entry = new LogEntry
                {
                    Type = logType,
                    Message = message ?? "",
                    StackTrace = stackTrace
                };

                if (ShouldIncludeLog(entry))
                {
                    logs.Add(entry);
                }
            }
        }

        return logs;
    }

    private bool ShouldIncludeLog(LogEntry log)
    {
        // 检查日志类型
        if (log.Type == LogType.Log && !exportLog) return false;
        if (log.Type == LogType.Warning && !exportWarning) return false;
        if (log.Type == LogType.Error && !exportError) return false;

        // 消息为空则跳过 (但允许空字符串，因为有些日志就是空行)
        if (log.Message == null) return false;

        // 检查前缀 (只有在设置了前缀时才过滤)
        if (!string.IsNullOrWhiteSpace(messagePrefix))
        {
            if (!log.Message.StartsWith(messagePrefix, StringComparison.OrdinalIgnoreCase))
                return false;
        }

        return true;
    }



    private string GenerateHtml(List<LogEntry> logs)
    {
        var sb = new StringBuilder();
        
        sb.AppendLine("<!DOCTYPE html>");
        sb.AppendLine("<html lang='zh-CN'>");
        sb.AppendLine("<head>");
        sb.AppendLine("    <meta charset='UTF-8'>");
        sb.AppendLine("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>");
        sb.AppendLine("    <title>Unity Console Log Export</title>");
        sb.AppendLine("    <style>");
        sb.AppendLine("        body { font-family: 'Consolas', 'Monaco', monospace; margin: 20px; background: #1e1e1e; color: #d4d4d4; }");
        sb.AppendLine("        .header { background: #252526; padding: 20px; border-radius: 8px; margin-bottom: 20px; }");
        sb.AppendLine("        .header h1 { margin: 0; color: #4ec9b0; }");
        sb.AppendLine("        .header .info { margin-top: 10px; color: #858585; font-size: 14px; }");
        sb.AppendLine("        .log-entry { background: #252526; margin: 10px 0; padding: 15px; border-radius: 5px; border-left: 4px solid; }");
        sb.AppendLine("        .log-entry.log { border-color: #4ec9b0; }");
        sb.AppendLine("        .log-entry.warning { border-color: #dcdcaa; background: #2d2d20; }");
        sb.AppendLine("        .log-entry.error { border-color: #f48771; background: #2d2020; }");
        sb.AppendLine("        .log-type { font-weight: bold; margin-bottom: 8px; padding: 3px 8px; border-radius: 3px; display: inline-block; }");
        sb.AppendLine("        .log-type.log { background: #1a4040; color: #4ec9b0; }");
        sb.AppendLine("        .log-type.warning { background: #3d3d20; color: #dcdcaa; }");
        sb.AppendLine("        .log-type.error { background: #3d2020; color: #f48771; }");
        sb.AppendLine("        .message { color: #d4d4d4; margin: 10px 0; white-space: pre-wrap; word-wrap: break-word; }");
        sb.AppendLine("        .stacktrace { color: #858585; font-size: 12px; margin-top: 10px; padding: 10px; background: #1e1e1e; border-radius: 3px; white-space: pre-wrap; }");
        sb.AppendLine("        .stacktrace-toggle { color: #569cd6; cursor: pointer; text-decoration: underline; margin-top: 5px; display: inline-block; }");
        sb.AppendLine("        .stacktrace-toggle:hover { color: #8ac6ff; }");
        sb.AppendLine("        .stacktrace.collapsed { display: none; }");
        sb.AppendLine("    </style>");
        sb.AppendLine("</head>");
        sb.AppendLine("<body>");
        
        // Header
        sb.AppendLine("    <div class='header'>");
        sb.AppendLine($"        <h1>Unity Console Log Export</h1>");
        sb.AppendLine($"        <div class='info'>导出时间: {DateTime.Now:yyyy-MM-dd HH:mm:ss} | 总计: {logs.Count} 条日志</div>");
        if (!string.IsNullOrEmpty(messagePrefix))
        {
            sb.AppendLine($"        <div class='info'>前缀过滤: \"{messagePrefix}\"</div>");
        }
        sb.AppendLine("    </div>");

        // Logs
        int logId = 0;
        foreach (var log in logs)
        {
            string typeClass = log.Type.ToString().ToLower();
            string typeText = log.Type == LogType.Log ? "LOG" : (log.Type == LogType.Warning ? "WARNING" : "ERROR");
            
            sb.AppendLine($"    <div class='log-entry {typeClass}'>");
            sb.AppendLine($"        <div class='log-type {typeClass}'>{typeText}</div>");
            sb.AppendLine($"        <div class='message'>{EscapeHtml(log.Message)}</div>");
            
            if (log.StackTrace.Count > 0)
            {
                sb.AppendLine($"        <span class='stacktrace-toggle' onclick='toggleStackTrace({logId})'>显示堆栈跟踪 ▼</span>");
                sb.AppendLine($"        <div id='stack{logId}' class='stacktrace collapsed'>{EscapeHtml(string.Join("\n", log.StackTrace))}</div>");
            }
            
            sb.AppendLine("    </div>");
            logId++;
        }

        sb.AppendLine("    <script>");
        sb.AppendLine("        function toggleStackTrace(id) {");
        sb.AppendLine("            const stack = document.getElementById('stack' + id);");
        sb.AppendLine("            const toggle = stack.previousElementSibling;");
        sb.AppendLine("            if (stack.classList.contains('collapsed')) {");
        sb.AppendLine("                stack.classList.remove('collapsed');");
        sb.AppendLine("                toggle.textContent = '隐藏堆栈跟踪 ▲';");
        sb.AppendLine("            } else {");
        sb.AppendLine("                stack.classList.add('collapsed');");
        sb.AppendLine("                toggle.textContent = '显示堆栈跟踪 ▼';");
        sb.AppendLine("            }");
        sb.AppendLine("        }");
        sb.AppendLine("    </script>");
        sb.AppendLine("</body>");
        sb.AppendLine("</html>");

        return sb.ToString();
    }

    private string EscapeHtml(string text)
    {
        return text.Replace("&", "&amp;")
                   .Replace("<", "&lt;")
                   .Replace(">", "&gt;")
                   .Replace("\"", "&quot;")
                   .Replace("'", "&#39;");
    }

    private class LogEntry
    {
        public LogType Type;
        public string Message;
        public List<string> StackTrace;
    }
}
