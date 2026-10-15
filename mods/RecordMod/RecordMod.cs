using System;
using System.Reflection;
using Modding;
using UnityEngine;

namespace RecordMod
{
    public class RecordMod : Mod, ITogglableMod
    {
        public static RecordMod Instance { get; private set; }
        private bool _isHooked;
        private GameObject _runnerObject;

        public RecordMod() : base("RecordMod") { }

        public override string GetVersion()
        {
            Version version = Assembly.GetExecutingAssembly().GetName().Version;
            return version != null ? version.ToString() : "1.0.0.0";
        }

        public override void Initialize()
        {
            if (_isHooked) return;
            Instance = this;

            Log("Initializing RecordMod...");

            // Spawn persistent runner object for input keys (5 for restart)
            if (_runnerObject == null)
            {
                _runnerObject = new GameObject("RecordMod_Runner");
                _runnerObject.AddComponent<RecordInputWatcher>();
                UnityEngine.Object.DontDestroyOnLoad(_runnerObject);
            }

            _isHooked = true;

            Log("Initialized RecordMod.");
            Log("  [5]: Restart current boss encounter");
        }

        public void Unload()
        {
            if (!_isHooked) return;

            if (_runnerObject != null)
            {
                UnityEngine.Object.Destroy(_runnerObject);
                _runnerObject = null;
            }

            _isHooked = false;

            Log("Unloaded RecordMod.");
        }
    }

    /// <summary>
    /// Persistent input listener for RecordMod controls.
    /// Runs every frame regardless of game state or active hero controller.
    /// </summary>
    public class RecordInputWatcher : MonoBehaviour
    {
        private void Update()
        {
            // Key 5: Restart boss fight
            if (Input.GetKeyDown(KeyCode.Alpha5) || Input.GetKeyDown(KeyCode.Keypad5))
            {
                Modding.Logger.Log("[RecordMod] [Hotkey 5] Restarting boss encounter...");
                CoreMod.PantheonPracticeApi.ReloadBoss();
            }
        }
    }
}