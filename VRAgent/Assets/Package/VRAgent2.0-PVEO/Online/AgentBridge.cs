using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

namespace HenryLab.VRAgent.Online
{
    // =====================================================================
    //  AgentBridge — TCP Server running inside Unity
    //
    //  Listens on a configurable port (default 6400).
    //  Python client connects, sends commands, receives responses.
    //
    //  Wire format:  [4-byte LE length][UTF-8 JSON body]
    //
    //  Threading model:
    //    - TCP accept loop + read loop run on background threads
    //    - Received commands are enqueued to a ConcurrentQueue
    //    - Main thread (Update) dequeues and processes via callback
    //    - Responses are sent from main thread through the socket
    // =====================================================================

    public class AgentBridge : MonoBehaviour
    {
        [Header("Network Settings")]
        [SerializeField] private int port = 6400;
        [SerializeField] private bool autoStart = true;

        // --- Events ---
        /// <summary>
        /// Fired on the MAIN THREAD whenever a command arrives.
        /// Subscriber should process the command and call SendResponse().
        /// </summary>
        public event Action<AgentCommand> OnCommandReceived;

        // --- State ---
        private TcpListener _listener;
        private TcpClient _client;
        private NetworkStream _stream;
        private Thread _acceptThread;
        private Thread _readThread;
        private volatile bool _running;
        private readonly ConcurrentQueue<AgentCommand> _inbox = new();
        private readonly object _writeLock = new();

        public bool IsConnected => _client is { Connected: true };
        public int Port => port;

        // =================================================================
        // Lifecycle
        // =================================================================

        private void Awake()
        {
            if(autoStart) StartServer();
        }

        private void OnDestroy()
        {
            StopServer();
        }

        private void OnApplicationQuit()
        {
            StopServer();
        }

        private void Update()
        {
            // Drain inbox on main thread
            while(_inbox.TryDequeue(out AgentCommand cmd))
            {
                try
                {
                    OnCommandReceived?.Invoke(cmd);
                }
                catch(Exception ex)
                {
                    Debug.LogError($"[AgentBridge] Error handling command: {ex}");
                    SendResponse(AgentResponse.MakeError(cmd?.requestId, ex.Message));
                }
            }
        }

        // =================================================================
        // Public API
        // =================================================================

        public void StartServer()
        {
            if(_running) return;
            _running = true;

            _listener = new TcpListener(IPAddress.Loopback, port);
            _listener.Start();

            Debug.Log($"[AgentBridge] TCP Server listening on 127.0.0.1:{port}");

            _acceptThread = new Thread(AcceptLoop) { IsBackground = true, Name = "AgentBridge-Accept" };
            _acceptThread.Start();
        }

        public void StopServer()
        {
            _running = false;

            try { _stream?.Close(); } catch { }
            try { _client?.Close(); } catch { }
            try { _listener?.Stop(); } catch { }

            _stream = null;
            _client = null;

            Debug.Log("[AgentBridge] Server stopped");
        }

        /// <summary>
        /// Send a response back to the Python client.
        /// Must be called from the main thread (or any thread — write is locked).
        /// </summary>
        public void SendResponse(AgentResponse response)
        {
            if(_stream == null || !_stream.CanWrite)
            {
                Debug.LogWarning("[AgentBridge] Cannot send — no active connection");
                return;
            }

            try
            {
                string json = response.Serialize();
                byte[] body = Encoding.UTF8.GetBytes(json);
                byte[] header = BitConverter.GetBytes(body.Length); // 4 bytes LE

                lock(_writeLock)
                {
                    _stream.Write(header, 0, 4);
                    _stream.Write(body, 0, body.Length);
                    _stream.Flush();
                }
            }
            catch(Exception ex)
            {
                Debug.LogError($"[AgentBridge] Send failed: {ex.Message}");
            }
        }

        // =================================================================
        // Background threads
        // =================================================================

        private void AcceptLoop()
        {
            while(_running)
            {
                try
                {
                    Debug.Log("[AgentBridge] Waiting for Python client...");
                    TcpClient newClient = _listener.AcceptTcpClient();

                    // Disconnect previous client if any
                    if(_client != null)
                    {
                        Debug.Log("[AgentBridge] Disconnecting previous client");
                        try { _stream?.Close(); } catch { }
                        try { _client?.Close(); } catch { }
                    }

                    _client = newClient;
                    _client.NoDelay = true;
                    _stream = _client.GetStream();

                    Debug.Log($"[AgentBridge] Python client connected from {_client.Client.RemoteEndPoint}");

                    // Start read loop for this client
                    _readThread = new Thread(ReadLoop) { IsBackground = true, Name = "AgentBridge-Read" };
                    _readThread.Start();

                    // Block accept thread until client disconnects (one client at a time)
                    _readThread.Join();

                    Debug.Log("[AgentBridge] Client disconnected");
                }
                catch(SocketException) when(!_running)
                {
                    break; // Server shutting down
                }
                catch(Exception ex)
                {
                    if(_running) Debug.LogError($"[AgentBridge] Accept error: {ex.Message}");
                }
            }
        }

        private void ReadLoop()
        {
            byte[] headerBuf = new byte[4];

            while(_running && _client is { Connected: true })
            {
                try
                {
                    // Read 4-byte length prefix
                    if(!ReadExact(_stream, headerBuf, 4)) break;
                    int length = BitConverter.ToInt32(headerBuf, 0);

                    if(length <= 0 || length > 10 * 1024 * 1024) // Max 10 MB
                    {
                        Debug.LogWarning($"[AgentBridge] Invalid message length: {length}");
                        break;
                    }

                    // Read body
                    byte[] bodyBuf = new byte[length];
                    if(!ReadExact(_stream, bodyBuf, length)) break;

                    string json = Encoding.UTF8.GetString(bodyBuf);
                    AgentCommand cmd = AgentCommand.Deserialize(json);

                    if(cmd != null)
                    {
                        // Handle Ping immediately on background thread (low latency)
                        if(cmd.type == CommandType.Ping.ToString())
                        {
                            SendResponse(new AgentResponse
                            {
                                type = ResponseType.Pong.ToString(),
                                requestId = cmd.requestId,
                                success = true,
                            });
                        }
                        else if(cmd.type == CommandType.Shutdown.ToString())
                        {
                            Debug.Log("[AgentBridge] Shutdown command received");
                            SendResponse(new AgentResponse
                            {
                                type = ResponseType.Pong.ToString(),
                                requestId = cmd.requestId,
                                success = true,
                            });
                            break;
                        }
                        else
                        {
                            _inbox.Enqueue(cmd);
                        }
                    }
                }
                catch(IOException)
                {
                    break; // Connection closed
                }
                catch(Exception ex)
                {
                    if(_running) Debug.LogError($"[AgentBridge] Read error: {ex.Message}");
                    break;
                }
            }
        }

        /// <summary>Read exactly n bytes from stream. Returns false on EOF.</summary>
        private static bool ReadExact(NetworkStream stream, byte[] buffer, int count)
        {
            int offset = 0;
            while(offset < count)
            {
                int read = stream.Read(buffer, offset, count - offset);
                if(read == 0) return false; // EOF
                offset += read;
            }
            return true;
        }
    }
}
