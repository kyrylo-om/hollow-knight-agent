using Modding;
using UnityEngine;

namespace CoreMod
{
    public class CoreMod : Mod
    {
        public CoreMod() : base("CoreMod") { }

        public override string GetVersion() => GetType().Assembly.GetName().Version.ToString();

        public override void Initialize()
        {
            ModHooks.HeroUpdateHook += OnHeroUpdate;
        }

        private void OnHeroUpdate()
        {
            if (Input.GetKeyDown(KeyCode.Alpha5) || Input.GetKeyDown(KeyCode.Keypad5))
            {
                Log("[Hotkey 5] Restarting boss encounter...");
                BossSceneHelper.ReloadBoss();
            }
        }
    }
}
