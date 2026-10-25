using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using CoreMod;

namespace TrainMod
{
    /// <summary>
    /// High-performance TCP socket server for TrainMod.
    /// Manages client connection, sends binary telemetry frames, and receives action commands in lockstep.
    /// </summary>
    public class TcpServer : IDisposable
    {
        public const int DefaultPort = 11451;
        public const uint HandshakeAckMagic = 0x4B485244; // "HKRD" in little-endian ASCII

        private TcpListener _listener;
        private TcpClient _client;
        private NetworkStream _stream;
        private readonly int _port;

        private readonly byte[] _sendBuffer = new byte[65536];
        private readonly byte[] _recvBuffer = new byte[8];
        private readonly byte[] _headerBuffer = new byte[16];

        private readonly object _lock = new object();
        private bool _isDisposed;

        public bool IsRunning { get; private set; }
        public bool IsClientConnected
        {
            get
            {
                lock (_lock)
                {
                    return _client != null && _client.Connected && _stream != null;
                }
            }
        }

        public TcpServer(int port = DefaultPort)
        {
            _port = port;
        }

        /// <summary>
        /// Starts the TCP listener on localhost without blocking.
        /// </summary>
        public void Start()
        {
            lock (_lock)
            {
                if (IsRunning || _isDisposed) return;

                try
                {
                    _listener = new TcpListener(IPAddress.Loopback, _port);
                    _listener.Server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                    _listener.Start(1);
                    IsRunning = true;
                    Modding.Logger.Log($"[TrainMod.TcpServer] Listening on 127.0.0.1:{_port}");
                }
                catch (Exception ex)
                {
                    Modding.Logger.LogError($"[TrainMod.TcpServer] Failed to start listener on port {_port}: {ex}");
                }
            }
        }

        /// <summary>
        /// Polls for a new incoming connection and completes the handshake if pending.
        /// </summary>
        public bool TryAcceptClient(in EpisodeFileHeader currentHeader)
        {
            lock (_lock)
            {
                if (!IsRunning || _isDisposed) return false;

                // If already connected, nothing to accept
                if (_client != null && _client.Connected) return true;

                // Check if any incoming connection is pending
                if (_listener == null || !_listener.Pending()) return false;

                try
                {
                    DisconnectClient();

                    _client = _listener.AcceptTcpClient();
                    _client.NoDelay = true; // Disable Nagle's algorithm for immediate dispatch
                    _client.SendBufferSize = 65536;
                    _client.ReceiveBufferSize = 65536;
                    _client.SendTimeout = 1000;
                    _client.ReceiveTimeout = 1000;

                    _stream = _client.GetStream();
                    Modding.Logger.Log($"[TrainMod.TcpServer] Client connected from {_client.Client.RemoteEndPoint}. Performing handshake...");

                    // 1. Send EpisodeFileHeader (16 bytes)
                    SendEpisodeHeader(currentHeader);

                    // 2. Read HandshakeAckMagic (4 bytes "HKRD")
                    byte[] ackBuf = new byte[4];
                    if (!ReadExact(_stream, ackBuf, 0, 4))
                    {
                        Modding.Logger.LogWarn("[TrainMod.TcpServer] Client disconnected during handshake.");
                        DisconnectClient();
                        return false;
                    }

                    uint ack = BitConverter.ToUInt32(ackBuf, 0);
                    if (ack != HandshakeAckMagic)
                    {
                        Modding.Logger.LogWarn($"[TrainMod.TcpServer] Invalid handshake magic: 0x{ack:X8} (expected 0x{HandshakeAckMagic:X8}).");
                        DisconnectClient();
                        return false;
                    }

                    Modding.Logger.Log("[TrainMod.TcpServer] Handshake successful! Lockstep training active.");
                    return true;
                }
                catch (Exception ex)
                {
                    Modding.Logger.LogError($"[TrainMod.TcpServer] Error accepting client: {ex}");
                    DisconnectClient();
                    return false;
                }
            }
        }

        /// <summary>
        /// Sends an episode header packet (16 bytes) to the client.
        /// </summary>
        public unsafe void SendEpisodeHeader(in EpisodeFileHeader header)
        {
            lock (_lock)
            {
                if (_stream == null) return;

                fixed (byte* dest = _headerBuffer)
                {
                    *(EpisodeFileHeader*)dest = header;
                }

                _stream.Write(_headerBuffer, 0, sizeof(EpisodeFileHeader));
                _stream.Flush();
            }
        }

        /// <summary>
        /// Sends a frame packet (84 bytes header + 40 bytes * entityCount) over the socket.
        /// </summary>
        public unsafe bool SendFrame(in FrameDataHeader frame, EntityData[] entities, int entityCount)
        {
            lock (_lock)
            {
                if (_stream == null || _client == null || !_client.Connected) return false;

                int frameBytes = sizeof(FrameDataHeader);
                int entitiesBytes = (entityCount > 0 && entities != null) ? entityCount * sizeof(EntityData) : 0;
                int totalBytes = frameBytes + entitiesBytes;

                if (totalBytes > _sendBuffer.Length)
                {
                    Modding.Logger.LogError($"[TrainMod.TcpServer] Frame payload size {totalBytes} exceeds buffer length {_sendBuffer.Length}.");
                    return false;
                }

                try
                {
                    fixed (byte* dest = _sendBuffer)
                    {
                        *(FrameDataHeader*)dest = frame;

                        if (entitiesBytes > 0)
                        {
                            fixed (EntityData* src = entities)
                            {
                                Buffer.MemoryCopy(src, dest + frameBytes, _sendBuffer.Length - frameBytes, entitiesBytes);
                            }
                        }
                    }

                    _stream.Write(_sendBuffer, 0, totalBytes);
                    _stream.Flush();
                    return true;
                }
                catch (Exception ex)
                {
                    Modding.Logger.LogWarn($"[TrainMod.TcpServer] Failed to send frame: {ex.Message}");
                    DisconnectClient();
                    return false;
                }
            }
        }

        /// <summary>
        /// Reads an 8-byte ActionPacket from the client (step_id: uint32, action_held: uint8, command_flags: uint8, reserved: uint16).
        /// Returns false if timeout occurs or client disconnects.
        /// </summary>
        public bool ReceiveAction(out uint stepId, out ActionButtons actions, out byte commandFlags, int timeoutMs = 1000)
        {
            stepId = 0;
            actions = ActionButtons.None;
            commandFlags = 0;

            lock (_lock)
            {
                if (_stream == null || _client == null || !_client.Connected) return false;

                try
                {
                    _client.ReceiveTimeout = timeoutMs;
                    if (!ReadExact(_stream, _recvBuffer, 0, 8))
                    {
                        Modding.Logger.LogWarn("[TrainMod.TcpServer] Client disconnected while reading action.");
                        DisconnectClient();
                        return false;
                    }

                    stepId = BitConverter.ToUInt32(_recvBuffer, 0);
                    actions = (ActionButtons)_recvBuffer[4];
                    commandFlags = _recvBuffer[5];
                    return true;
                }
                catch (IOException ex)
                {
                    Modding.Logger.LogWarn($"[TrainMod.TcpServer] ReceiveAction timeout or I/O error: {ex.Message}");
                    DisconnectClient();
                    return false;
                }
                catch (Exception ex)
                {
                    Modding.Logger.LogError($"[TrainMod.TcpServer] ReceiveAction unexpected error: {ex}");
                    DisconnectClient();
                    return false;
                }
            }
        }

        public void DisconnectClient()
        {
            lock (_lock)
            {
                if (_stream != null)
                {
                    try { _stream.Close(); } catch { }
                    _stream = null;
                }

                if (_client != null)
                {
                    try { _client.Close(); } catch { }
                    _client = null;
                    Modding.Logger.Log("[TrainMod.TcpServer] Client disconnected. Input control restored to player.");
                }
            }
        }

        public void Stop()
        {
            lock (_lock)
            {
                DisconnectClient();

                if (_listener != null)
                {
                    try { _listener.Stop(); } catch { }
                    _listener = null;
                }

                IsRunning = false;
                Modding.Logger.Log("[TrainMod.TcpServer] Server stopped.");
            }
        }

        public void Dispose()
        {
            if (_isDisposed) return;
            _isDisposed = true;
            Stop();
        }

        private static bool ReadExact(NetworkStream stream, byte[] buffer, int offset, int count)
        {
            int totalRead = 0;
            while (totalRead < count)
            {
                int read = stream.Read(buffer, offset + totalRead, count - totalRead);
                if (read <= 0) return false; // Stream closed
                totalRead += read;
            }
            return true;
        }
    }
}
