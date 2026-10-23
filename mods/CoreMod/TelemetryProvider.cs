using System;
using System.Collections.Generic;

namespace CoreMod
{
    /// <summary>
    /// Consumer interface for receiving telemetry streams from CoreMod.
    /// Implemented by RecordMod (disk output) and TrainMod (TCP socket output).
    /// </summary>
    public interface ITelemetryConsumer
    {
        void OnEpisodeStart(EpisodeFileHeader header);
        void OnFrame(in FrameDataHeader frame, EntityData[] entities, int entityCount);
        void OnEpisodeEnd();
    }

    /// <summary>
    /// Shared registry for dispatching telemetry packets to active consumers.
    /// </summary>
    public static class TelemetryProvider
    {
        private static readonly List<ITelemetryConsumer> _consumers = new List<ITelemetryConsumer>();
        private static readonly object _lock = new object();

        public static void RegisterConsumer(ITelemetryConsumer consumer)
        {
            if (consumer == null) return;
            lock (_lock)
            {
                if (!_consumers.Contains(consumer))
                {
                    _consumers.Add(consumer);
                }
            }
        }

        public static void UnregisterConsumer(ITelemetryConsumer consumer)
        {
            if (consumer == null) return;
            lock (_lock)
            {
                _consumers.Remove(consumer);
            }
        }

        internal static void DispatchEpisodeStart(EpisodeFileHeader header)
        {
            lock (_lock)
            {
                for (int i = 0; i < _consumers.Count; i++)
                {
                    try
                    {
                        _consumers[i].OnEpisodeStart(header);
                    }
                    catch (Exception ex)
                    {
                        Modding.Logger.LogError($"[TelemetryProvider] Error in consumer OnEpisodeStart: {ex}");
                    }
                }
            }
        }

        internal static void DispatchFrame(in FrameDataHeader frame, EntityData[] entities, int entityCount)
        {
            lock (_lock)
            {
                for (int i = 0; i < _consumers.Count; i++)
                {
                    try
                    {
                        _consumers[i].OnFrame(in frame, entities, entityCount);
                    }
                    catch (Exception ex)
                    {
                        Modding.Logger.LogError($"[TelemetryProvider] Error in consumer OnFrame: {ex}");
                    }
                }
            }
        }

        internal static void DispatchEpisodeEnd()
        {
            lock (_lock)
            {
                for (int i = 0; i < _consumers.Count; i++)
                {
                    try
                    {
                        _consumers[i].OnEpisodeEnd();
                    }
                    catch (Exception ex)
                    {
                        Modding.Logger.LogError($"[TelemetryProvider] Error in consumer OnEpisodeEnd: {ex}");
                    }
                }
            }
        }
    }
}
