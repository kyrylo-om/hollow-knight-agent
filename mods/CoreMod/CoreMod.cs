using System;
using System.Reflection;
using Modding;

namespace CoreMod
{
    public class CoreMod : Mod, ITogglableMod
    {
        public static CoreMod Instance { get; private set; }
        private bool _isHooked;

        public CoreMod() : base("CoreMod") { }

        public override string GetVersion()
        {
            Version version = Assembly.GetExecutingAssembly().GetName().Version;
            return version != null ? version.ToString() : "1.0.0.0";
        }

        public override void Initialize()
        {
            if (_isHooked) return;
            Instance = this;

            Log("Initializing CoreMod (PantheonPracticeApi)...");
            PantheonPracticeApi.Hook();
            _isHooked = true;

            Log("Initialized CoreMod.");
        }

        public void Unload()
        {
            if (!_isHooked) return;

            PantheonPracticeApi.Unhook();
            _isHooked = false;

            Log("Unloaded CoreMod.");
        }
    }
}