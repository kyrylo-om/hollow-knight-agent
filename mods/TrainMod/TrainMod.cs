using CoreMod;
using Modding;
using UnityEngine;

namespace TrainMod
{
    public class TrainMod : Mod, ITogglableMod, ITelemetryConsumer
    {
        public static TrainMod Instance { get; private set; }

        private TcpServer _tcpServer;
        private EpisodeFileHeader _lastHeader = new EpisodeFileHeader
        {
            Magic = EpisodeFileHeader.ExpectedMagic,
            BossId = 0,
            BossDifficulty = 0,
            NailDamage = 21,
            MaxHealth = 9,
            Reserved = 0
        };

        public TrainMod() : base("TrainMod") { }

        public override string GetVersion() => GetType().Assembly.GetName().Version.ToString();

        public override void Initialize()
        {
            Instance = this;

            Log("Initializing TrainMod...");
            RenderingManager.Hook();
            InputInjector.Hook();

            _tcpServer = new TcpServer(TcpServer.DefaultPort);
            _tcpServer.Start();

            TelemetryProvider.RegisterConsumer(this);
            ModHooks.HeroUpdateHook += OnHeroUpdate;

            Log($"TrainMod initialized. TCP server listening on 127.0.0.1:{TcpServer.DefaultPort}.");
            Log("  [0]: Toggle Rendering (headless/ML speedup)");
            Log("  [5]: Restart current boss encounter");
            Log("  [6]: Log TCP connection status");
        }

        public void Unload()
        {
            ModHooks.HeroUpdateHook -= OnHeroUpdate;
            TelemetryProvider.UnregisterConsumer(this);

            InputInjector.Unhook();
            RenderingManager.Unhook();

            if (_tcpServer != null)
            {
                _tcpServer.Dispose();
                _tcpServer = null;
            }

            Instance = null;
            Log("Unloaded TrainMod.");
        }

        private void OnHeroUpdate()
        {
            // Hotkey 0: Toggle rendering (headless / fast ML training)
            if (Input.GetKeyDown(KeyCode.Alpha0) || Input.GetKeyDown(KeyCode.Keypad0))
            {
                bool isRendering = RenderingManager.ToggleRendering();
                Log($"Toggled rendering: {(isRendering ? "ON" : "OFF (Headless / ML Speedup)")}");
            }

            // Hotkey 5: Restart boss encounter
            if (Input.GetKeyDown(KeyCode.Alpha5) || Input.GetKeyDown(KeyCode.Keypad5))
            {
                Log("[Hotkey 5] Restarting boss encounter...");
                BossSceneHelper.ReloadBoss();
            }

            // Hotkey 6: Status check
            if (Input.GetKeyDown(KeyCode.Alpha6) || Input.GetKeyDown(KeyCode.Keypad6))
            {
                bool connected = _tcpServer != null && _tcpServer.IsClientConnected;
                Log($"[TrainMod Status] TCP Server Running: {_tcpServer?.IsRunning}, Client Connected: {connected}, Input Injecting: {InputInjector.IsInjecting}");
            }
        }

        // ITelemetryConsumer Implementation (Lockstep Frame Dispatch)

        public void OnEpisodeStart(EpisodeFileHeader header)
        {
            _lastHeader = header;
            if (_tcpServer != null && _tcpServer.IsClientConnected)
            {
                _tcpServer.SendEpisodeHeader(header);
            }
        }

        public void OnFrame(in FrameDataHeader frame, EntityData[] entities, int entityCount)
        {
            if (_tcpServer == null || !_tcpServer.IsRunning) return;

            // 1. If not connected, check if a Python client is attempting to connect
            if (!_tcpServer.IsClientConnected)
            {
                if (!_tcpServer.TryAcceptClient(in _lastHeader))
                {
                    if (InputInjector.IsInjecting)
                    {
                        InputInjector.Reset();
                    }
                    return;
                }
            }

            // 2. Lockstep exchange: Send telemetry frame to Python
            if (!_tcpServer.SendFrame(in frame, entities, entityCount))
            {
                InputInjector.Reset();
                return;
            }

            // 3. Receive action packet from Python (1000ms timeout)
            if (_tcpServer.ReceiveAction(out uint stepId, out ActionButtons actions, out byte cmdFlags, timeoutMs: 1000))
            {
                // Process command flags
                if ((cmdFlags & 0x01) != 0)
                {
                    Log($"[TrainMod] Reset encounter command received from agent at step {stepId}.");
                    BossSceneHelper.ReloadBoss();
                }

                if ((cmdFlags & 0x02) != 0)
                {
                    bool isRendering = RenderingManager.ToggleRendering();
                    Log($"[TrainMod] Rendering toggle command received from agent: {(isRendering ? "ON" : "OFF")}.");
                }

                // Inject action into HeroController and HeroActions for this tick
                InputInjector.ApplyAction(actions);
            }
            else
            {
                // Timeout or client disconnected: release inputs immediately
                InputInjector.Reset();
            }
        }

        public void OnEpisodeEnd()
        {
            InputInjector.Reset();
        }
    }
}
