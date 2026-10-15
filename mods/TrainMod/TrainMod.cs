using System;
using System.Reflection;
using Modding;
using UnityEngine;

namespace TrainMod
{
    public class TrainMod : Mod, ITogglableMod
    {
        public static TrainMod Instance { get; private set; }
        private bool _isHooked;
        private GameObject _runnerObject;

        public TrainMod() : base("TrainMod") { }

        public override string GetVersion()
        {
            Version version = Assembly.GetExecutingAssembly().GetName().Version;
            return version != null ? version.ToString() : "1.0.0.0";
        }

        public override void Initialize()
        {
            if (_isHooked) return;
            Instance = this;

            Log("Initializing TrainMod...");
            RenderingManager.Hook();

            // Spawn persistent runner object for input keys (0 for rendering toggle, 5 for restart)
            if (_runnerObject == null)
            {
                _runnerObject = new GameObject("TrainMod_Runner");
                _runnerObject.AddComponent<TrainInputWatcher>();
                UnityEngine.Object.DontDestroyOnLoad(_runnerObject);
            }

            _isHooked = true;

            Log("Initialized TrainMod.");
            Log("  [0]: Toggle Rendering (headless/no-render mode for ML training)");
            Log("  [5]: Restart current boss encounter");
        }

        public void Unload()
        {
            if (!_isHooked) return;

            RenderingManager.Unhook();

            if (_runnerObject != null)
            {
                UnityEngine.Object.Destroy(_runnerObject);
                _runnerObject = null;
            }

            _isHooked = false;

            Log("Unloaded TrainMod.");
        }
    }

    /// <summary>
    /// Persistent input listener for TrainMod controls.
    /// Runs every frame regardless of game state or active hero controller.
    /// </summary>
    public class TrainInputWatcher : MonoBehaviour
    {
        private void Update()
        {
            // Key 0: Toggle rendering
            if (Input.GetKeyDown(KeyCode.Alpha0) || Input.GetKeyDown(KeyCode.Keypad0))
            {
                bool isRendering = RenderingManager.ToggleRendering();
                Modding.Logger.Log($"[TrainMod] Toggled rendering: {(isRendering ? "ON" : "OFF (Headless / ML Speedup)")}");
            }

            // Key 5: Restart boss fight
            if (Input.GetKeyDown(KeyCode.Alpha5) || Input.GetKeyDown(KeyCode.Keypad5))
            {
                Modding.Logger.Log("[TrainMod] [Hotkey 5] Restarting boss encounter...");
                CoreMod.PantheonPracticeApi.ReloadBoss();
            }
        }
    }
}