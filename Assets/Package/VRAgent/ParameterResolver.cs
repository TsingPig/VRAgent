using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEditor.Events;
using UnityEngine;
using UnityEngine.Events;

namespace HenryLab.VRAgent
{
    public static class ParameterResolver
    {
        /// <summary>
        /// 根据 eventUnit 创建 UnityEvent 并绑定所有 methodCallUnit
        /// </summary>
        public static UnityEvent CreateUnityEvent(eventUnit e, bool useFileID = true)
        {
            var manager = UnityEngine.Object.FindAnyObjectByType<FileIDContainer>();
            UnityEvent evt = new UnityEvent();
            if(e.methodCallUnits == null) return evt;

            foreach(var methodCallUnit in e.methodCallUnits)
            {
                if(string.IsNullOrEmpty(methodCallUnit.script) || string.IsNullOrEmpty(methodCallUnit.methodName))
                    continue;

                // MonoBehaviour component = FindComponentByFileID(methodCallUnit.script);
                MonoBehaviour component = manager.GetComponent(methodCallUnit.script);
                if(component == null)
                {
                    Debug.LogWarning($"{Str.Tags.LogsTag} Component with script FileID {methodCallUnit.script} not found");
                    continue;
                }

                // 改进的方法查找，支持第三方库
                MethodInfo method = FindMethodSafely(component, methodCallUnit.methodName);
                if(method == null)
                {
                    Debug.LogError($"{Str.Tags.LogsTag} No parameterless method '{methodCallUnit.methodName}' found on {component.GetType().FullName} ({component.name}). Only methods without parameters are supported for UnityEvent binding.");
                    continue;
                }

                // 处理找到的方法（已确保是无参数的，除非是属性setter）
                if(method.GetParameters().Length == 0)
                {
                    // 无参数方法的标准处理
#if UNITY_EDITOR
                    if(method.ReturnType == typeof(void))
                    {
                        // 无返回值方法，直接创建 UnityAction
                        try
                        {
                            UnityAction action = System.Delegate.CreateDelegate(typeof(UnityAction), component, method) as UnityAction;
                            if(action != null)
                            {
                                UnityEventTools.AddPersistentListener(evt, action);
                                Debug.Log($"{Str.Tags.LogsTag} Successfully bound void method: {component.GetType().Name}.{method.Name}");
                            }
                            else
                            {
                                Debug.LogWarning($"{Str.Tags.LogsTag} Cannot create UnityAction for method {method.Name}");
                            }
                        }
                        catch(Exception ex)
                        {
                            Debug.LogError($"{Str.Tags.LogsTag} Failed to create delegate for {method.Name}: {ex.Message}");
                            // 备选方案：使用运行时调用
                            CreateRuntimeWrapper(evt, component, method);
                        }
                    }
                    else
                    {
                        // 有返回值的方法，创建包装器方法
                        CreateReturnValueWrapper(evt, component, method);
                    }
#endif
                }
                else if(method.GetParameters().Length == 1)
                {
                    // 特殊情况：属性setter（有一个参数）
                    Debug.LogWarning($"{Str.Tags.LogsTag} Method {method.Name} appears to be a property setter with one parameter. This is not fully supported yet.");
                }
                else
                {
                    // 这种情况理论上不应该发生，因为FindMethodSafely已经过滤了
                    Debug.LogError($"{Str.Tags.LogsTag} Method {method.Name} has {method.GetParameters().Length} parameters, which should not happen.");
                }
            }
            return evt;
        }

        /// <summary>
        /// 安全地查找方法，支持第三方库组件
        /// 优先选择无参数版本，有参数版本将被忽略
        /// </summary>
        private static MethodInfo FindMethodSafely(MonoBehaviour component, string methodName)
        {
            try
            {
                Type componentType = component.GetType();

                // 统一策略：查找所有同名方法，优先选择无参数的
                MethodInfo[] methods = componentType.GetMethods(
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);

                MethodInfo parameterlessMethod = null;
                MethodInfo anyMethod = null;

                foreach(var m in methods)
                {
                    if(m.Name == methodName)
                    {
                        anyMethod = m; // 记录任意一个同名方法
                        if(m.GetParameters().Length == 0)
                        {
                            parameterlessMethod = m; // 找到无参数版本
                            break; // 立即返回无参数版本
                        }
                    }
                }

                if(parameterlessMethod != null)
                {
                    Debug.Log($"{Str.Tags.LogsTag} Found parameterless method {methodName} on {componentType.Name}");
                    return parameterlessMethod;
                }

                // 如果没有找到无参数版本，尝试在继承链中查找
                MethodInfo hierarchyMethod = FindMethodInHierarchy(componentType, methodName);
                if(hierarchyMethod != null)
                {
                    Debug.Log($"{Str.Tags.LogsTag} Found parameterless method {methodName} in class hierarchy of {componentType.Name}");
                    return hierarchyMethod;
                }

                // 如果还是没找到，尝试查找属性的setter
                PropertyInfo property = componentType.GetProperty(methodName.Replace("set_", ""),
                    BindingFlags.Public | BindingFlags.Instance);
                if(property != null && property.CanWrite)
                {
                    MethodInfo setter = property.GetSetMethod();
                    if(setter != null && setter.GetParameters().Length == 1) // setter通常有一个参数，但我们可以特殊处理
                    {
                        Debug.Log($"{Str.Tags.LogsTag} Found property setter for {methodName} on {componentType.Name}");
                        return setter;
                    }
                }

                // 如果找到了同名方法但都有参数，给出更明确的错误提示
                if(anyMethod != null)
                {
                    var parameters = anyMethod.GetParameters();
                    Debug.LogWarning($"{Str.Tags.LogsTag} Method {methodName} found on {componentType.Name} but has {parameters.Length} parameters. Only parameterless methods are supported for UnityEvent binding.");
                    foreach(var param in parameters)
                    {
                        Debug.LogWarning($"{Str.Tags.LogsTag} - Parameter: {param.ParameterType.Name} {param.Name}");
                    }
                }

                return null;
            }
            catch(Exception ex)
            {
                Debug.LogError($"{Str.Tags.LogsTag} Error finding method {methodName} on {component.GetType().Name}: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// 在类层次结构中查找方法
        /// </summary>
        private static MethodInfo FindMethodInHierarchy(Type type, string methodName)
        {
            Type currentType = type;
            while(currentType != null)
            {
                try
                {
                    MethodInfo method = currentType.GetMethod(methodName,
                        BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);

                    if(method != null && method.GetParameters().Length == 0)
                        return method;
                }
                catch(Exception)
                {
                    // 忽略异常，继续查找
                }

                currentType = currentType.BaseType;
            }

            // 查找接口方法
            foreach(Type interfaceType in type.GetInterfaces())
            {
                try
                {
                    MethodInfo method = interfaceType.GetMethod(methodName);
                    if(method != null && method.GetParameters().Length == 0)
                        return method;
                }
                catch(Exception)
                {
                    // 忽略异常，继续查找
                }
            }

            return null;
        }

        /// <summary>
        /// 创建运行时包装器（备选方案）
        /// </summary>
        private static void CreateRuntimeWrapper(UnityEvent evt, MonoBehaviour component, MethodInfo method)
        {
            UnityAction runtimeAction = () =>
            {
                try
                {
                    if(component != null && component.gameObject != null)
                    {
                        object result = method.Invoke(component, null);
                        Debug.Log($"{Str.Tags.LogsTag} Runtime call: {component.GetType().Name}.{method.Name}() completed");
                        if(result != null)
                            Debug.Log($"{Str.Tags.LogsTag} Result: {result}");
                    }
                }
                catch(Exception ex)
                {
                    Debug.LogError($"{Str.Tags.LogsTag} Runtime error calling {method.Name}: {ex.Message}");
                }
            };

            UnityEventTools.AddPersistentListener(evt, runtimeAction);
        }

#if UNITY_EDITOR

        /// <summary>
        /// 为有返回值的方法创建包装器，使其能够在 Inspector 中序列化
        /// </summary>
        private static void CreateReturnValueWrapper(UnityEvent evt, MonoBehaviour component, MethodInfo method)
        {
            // 创建一个包装器方法，调用原方法但忽略返回值
            string wrapperMethodName = $"_Wrapper_{method.Name}_{method.GetHashCode()}";

            // 检查是否已经存在包装器方法
            MethodInfo existingWrapper = component.GetType().GetMethod(wrapperMethodName,
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);

            if(existingWrapper == null)
            {
                // 动态创建包装器方法（运行时方案）
                UnityAction wrapperAction = () =>
                {
                    try
                    {
                        object result = method.Invoke(component, null);
                        Debug.Log($"{Str.Tags.LogsTag} Method {method.Name} returned: {result}");
                    }
                    catch(System.Exception ex)
                    {
                        Debug.LogError($"{Str.Tags.LogsTag} Error invoking {method.Name}: {ex.Message}");
                    }
                };

                // 使用 UnityEventTools.AddVoidPersistentListener 来添加可序列化的监听器
                // 这需要在目标组件上创建一个实际的void方法
                CreateAndAddVoidWrapper(evt, component, method);
            }
            else
            {
                UnityAction action = System.Delegate.CreateDelegate(typeof(UnityAction), component, existingWrapper) as UnityAction;
                if(action != null)
                    UnityEventTools.AddPersistentListener(evt, action);
            }
        }

        /// <summary>
        /// 创建并添加 void 包装器方法
        /// </summary>
        private static void CreateAndAddVoidWrapper(UnityEvent evt, MonoBehaviour component, MethodInfo originalMethod)
        {
            try
            {
                // 方案1: 尝试在同一个GameObject上找到或创建SerializableMethodWrapper
                GameObject targetGO = component.gameObject;
                SerializableMethodWrapper wrapper = targetGO.GetComponent<SerializableMethodWrapper>();

                if(wrapper == null)
                {
                    wrapper = targetGO.AddComponent<SerializableMethodWrapper>();
                    Debug.Log($"{Str.Tags.LogsTag} Added SerializableMethodWrapper to {targetGO.name}");
                }

                // 设置包装器参数
                wrapper.Setup(component, originalMethod.Name, true);

                // 添加可序列化的监听器
                UnityEventTools.AddPersistentListener(evt, wrapper.InvokeWrappedMethod);

                Debug.Log($"{Str.Tags.LogsTag} Successfully wrapped method {originalMethod.Name} with return type {originalMethod.ReturnType}");
            }
            catch(Exception ex)
            {
                Debug.LogError($"{Str.Tags.LogsTag} Failed to create wrapper for {originalMethod.Name}: {ex.Message}");

                // 备选方案：使用运行时调用（不可序列化）
                UnityAction fallbackAction = () =>
                {
                    try
                    {
                        object result = originalMethod.Invoke(component, null);
                        Debug.Log($"{Str.Tags.LogsTag} {component.name}.{originalMethod.Name}() returned: {result}");
                    }
                    catch(Exception invokeEx)
                    {
                        Debug.LogError($"{Str.Tags.LogsTag} Error invoking {originalMethod.Name}: {invokeEx.Message}");
                    }
                };

                UnityEventTools.AddPersistentListener(evt, fallbackAction);
            }
        }

#endif

        /// <summary>
        /// 绑定一组 eventUnit 到目标 UnityEvent 列表
        /// </summary>
        public static void BindEventList(List<eventUnit> eventUnits, List<UnityEvent> targetList, bool useFileID = true)
        {
            targetList.Clear();
            if(eventUnits == null) return;

            foreach(var e in eventUnits)
            {
                targetList.Add(CreateUnityEvent(e, useFileID));
            }
        }
    }

    /// <summary>
    /// 辅助组件，用于包装有返回值的方法调用，使其能在Inspector中序列化
    /// </summary>
    [System.Serializable]
    public class SerializableMethodWrapper : MonoBehaviour
    {
        [SerializeField] private MonoBehaviour targetComponent;
        [SerializeField] private string methodName;
        [SerializeField] private bool logReturnValue = true;

        /// <summary>
        /// 包装器方法，调用目标方法并处理返回值
        /// </summary>
        public void InvokeWrappedMethod()
        {
            if(targetComponent == null || string.IsNullOrEmpty(methodName))
            {
                Debug.LogWarning($"{Str.Tags.LogsTag} SerializableMethodWrapper: Invalid target or method name");
                return;
            }

            try
            {
                MethodInfo method = targetComponent.GetType().GetMethod(methodName,
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);

                if(method == null)
                {
                    Debug.LogError($"{Str.Tags.LogsTag} Method {methodName} not found on {targetComponent.GetType().Name}");
                    return;
                }

                object result = method.Invoke(targetComponent, null);

                if(logReturnValue && result != null)
                {
                    Debug.Log($"{Str.Tags.LogsTag} {targetComponent.name}.{methodName}() returned: {result}");
                }

                // 可以在这里添加额外的返回值处理逻辑
                HandleReturnValue(result, method.ReturnType);
            }
            catch(Exception ex)
            {
                Debug.LogError($"{Str.Tags.LogsTag} Error invoking {methodName}: {ex.Message}");
            }
        }

        /// <summary>
        /// 处理方法返回值
        /// </summary>
        private void HandleReturnValue(object returnValue, Type returnType)
        {
            // 这里可以根据需要处理不同类型的返回值
            // 例如：存储到变量、触发其他事件、发送消息等

            if(returnValue == null) return;

            // 示例：根据返回值类型进行不同处理
            switch(Type.GetTypeCode(returnType))
            {
                case TypeCode.Boolean:
                bool boolResult = (bool)returnValue;
                // 可以根据布尔结果触发不同行为
                break;

                case TypeCode.Int32:
                case TypeCode.Single:
                case TypeCode.Double:
                // 数值类型的处理
                break;

                case TypeCode.String:
                string stringResult = (string)returnValue;
                // 字符串类型的处理
                break;

                default:
                // 其他类型的处理
                break;
            }
        }

        /// <summary>
        /// 设置包装器参数
        /// </summary>
        public void Setup(MonoBehaviour target, string method, bool logReturn = true)
        {
            targetComponent = target;
            methodName = method;
            logReturnValue = logReturn;
        }
    }
}