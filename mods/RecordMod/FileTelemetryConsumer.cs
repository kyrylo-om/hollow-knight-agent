using System;
using System.Collections.Concurrent;
using System.IO;
using System.Threading;
using CoreMod;

namespace RecordMod
{
    /// <summary>
    /// High-performance, thread-safe file telemetry recorder.
    /// Receives frames from CoreMod on the Unity thread and enqueues them into a BlockingCollection.
    /// A dedicated background thread drains the queue and blits entire structs directly into a 64 KB buffer,
    /// flushing to disk in bulk to eliminate syscall overhead and prevent game loop stutter.
    /// </summary>
    public class FileTelemetryConsumer : ITelemetryConsumer, IDisposable
    {
        private const int BufferSize = 8 * 1024; // 8 KB user-space buffer

        private struct QueuedPacket
        {
            public FrameDataHeader Header;
            public EntityData[] Entities;
            public int EntityCount;
        }

        private BlockingCollection<QueuedPacket> _queue;
        private Thread _writerThread;
        private FileStream _fileStream;
        private readonly byte[] _buffer = new byte[BufferSize];
        private int _bufferOffset;

        private string _currentFilePath;
        private uint _totalFramesRecorded;
        private readonly object _stateLock = new object();
        private bool _isDisposed;

        public string OutputDirectory { get; }

        public FileTelemetryConsumer()
        {
            string modDir = Path.GetDirectoryName(typeof(RecordMod).Assembly.Location);
            OutputDirectory = Path.Combine(modDir ?? ".", "Recordings");
            Directory.CreateDirectory(OutputDirectory);
        }

        public void OnEpisodeStart(EpisodeFileHeader header)
        {
            lock (_stateLock)
            {
                if (_isDisposed) return;

                CloseCurrentSession();

                string bossName = "Unknown";
                if (header.BossId > 0 && header.BossId <= BossRegistry.Bosses.Count)
                {
                    bossName = BossRegistry.Bosses[header.BossId - 1].Name.Replace(" ", "_");
                }

                string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                _currentFilePath = Path.Combine(OutputDirectory, $"episode_{bossName}_{timestamp}.bin");
                _totalFramesRecorded = 0;

                try
                {
                    _fileStream = new FileStream(_currentFilePath, FileMode.Create, FileAccess.Write, FileShare.None, 4096);
                    _bufferOffset = 0;

                    WriteEpisodeHeader(in header);

                    _queue = new BlockingCollection<QueuedPacket>(new ConcurrentQueue<QueuedPacket>());
                    _writerThread = new Thread(DiskWriterLoop)
                    {
                        Name = "RecordMod_DiskWriter",
                        IsBackground = true
                    };
                    _writerThread.Start();

                    Modding.Logger.Log($"[RecordMod] Started recording episode: {_currentFilePath}");
                }
                catch (Exception ex)
                {
                    Modding.Logger.LogError($"[RecordMod] Failed to start recording session: {ex}");
                    CloseCurrentSession();
                }
            }
        }

        public void OnFrame(in FrameDataHeader frame, EntityData[] entities, int entityCount)
        {
            var queue = _queue;
            if (queue == null || queue.IsAddingCompleted) return;

            EntityData[] copy = null;
            if (entityCount > 0 && entities != null)
            {
                copy = new EntityData[entityCount];
                Array.Copy(entities, copy, entityCount);
            }

            try
            {
                queue.Add(new QueuedPacket
                {
                    Header = frame,
                    Entities = copy,
                    EntityCount = entityCount
                });
            }
            catch (InvalidOperationException)
            {
                // Queue already closed by episode end
            }
        }

        public void OnEpisodeEnd()
        {
            lock (_stateLock)
            {
                CloseCurrentSession();
            }
        }

        private void DiskWriterLoop()
        {
            var queue = _queue;
            if (queue == null) return;

            try
            {
                foreach (QueuedPacket packet in queue.GetConsumingEnumerable())
                {
                    WriteFrame(in packet.Header, packet.Entities, packet.EntityCount);
                    _totalFramesRecorded++;
                }

                FlushBuffer();
                if (_fileStream != null)
                {
                    _fileStream.Flush();
                }
            }
            catch (Exception ex)
            {
                Modding.Logger.LogError($"[RecordMod] Error in disk writer loop: {ex}");
            }
        }

        private unsafe void WriteEpisodeHeader(in EpisodeFileHeader h)
        {
            EnsureCapacity(sizeof(EpisodeFileHeader));
            fixed (byte* dest = &_buffer[_bufferOffset])
            {
                *(EpisodeFileHeader*)dest = h;
            }
            _bufferOffset += sizeof(EpisodeFileHeader);
        }

        private unsafe void WriteFrame(in FrameDataHeader f, EntityData[] entities, int entityCount)
        {
            int frameBytes = sizeof(FrameDataHeader);
            int entitiesBytes = (entityCount > 0 && entities != null) ? entityCount * sizeof(EntityData) : 0;
            int totalBytes = frameBytes + entitiesBytes;

            EnsureCapacity(totalBytes);

            fixed (byte* dest = &_buffer[_bufferOffset])
            {
                *(FrameDataHeader*)dest = f;

                if (entitiesBytes > 0)
                {
                    fixed (EntityData* src = entities)
                    {
                        Buffer.MemoryCopy(src, dest + frameBytes, BufferSize - _bufferOffset - frameBytes, entitiesBytes);
                    }
                }
            }

            _bufferOffset += totalBytes;
        }

        private void EnsureCapacity(int bytesNeeded)
        {
            if (_bufferOffset + bytesNeeded > BufferSize)
            {
                FlushBuffer();
            }
        }

        private void FlushBuffer()
        {
            if (_bufferOffset > 0 && _fileStream != null)
            {
                _fileStream.Write(_buffer, 0, _bufferOffset);
                _bufferOffset = 0;
            }
        }

        private void CloseCurrentSession()
        {
            if (_queue != null)
            {
                try { _queue.CompleteAdding(); } catch { }
                if (_writerThread != null && _writerThread.IsAlive)
                {
                    _writerThread.Join(2000); // Wait up to 2 seconds to drain remaining queue
                }
                _queue.Dispose();
                _queue = null;
                _writerThread = null;
            }

            if (_fileStream != null)
            {
                long length = 0;
                try
                {
                    FlushBuffer();
                    _fileStream.Flush();
                    length = _fileStream.Length;
                    _fileStream.Dispose();
                }
                catch { }
                _fileStream = null;

                if (_totalFramesRecorded > 0)
                {
                    Modding.Logger.Log($"[RecordMod] Finished recording: {_currentFilePath} ({_totalFramesRecorded} frames, {length} bytes)");
                }
            }
        }

        public void Dispose()
        {
            lock (_stateLock)
            {
                if (_isDisposed) return;
                _isDisposed = true;
                CloseCurrentSession();
            }
        }
    }
}
