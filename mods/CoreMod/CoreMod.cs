using System.Collections.Generic;
using Modding;
using UnityEngine;

namespace CoreMod
{
    public class CoreMod : Mod, ITogglableMod, IMenuMod, IGlobalSettings<CoreModSettings>
    {
        public static CoreModSettings Settings { get; private set; } = new CoreModSettings();

        public CoreMod() : base("CoreMod") { }

        public override string GetVersion() => GetType().Assembly.GetName().Version.ToString();

        public bool ToggleButtonInsideMenu => true;

        public void OnLoadGlobal(CoreModSettings s) => Settings = s;

        public CoreModSettings OnSaveGlobal() => Settings;

        public List<IMenuMod.MenuEntry> GetMenuData(IMenuMod.MenuEntry? toggleButtonEntry)
        {
            List<IMenuMod.MenuEntry> entries = new List<IMenuMod.MenuEntry>();
            if (toggleButtonEntry.HasValue)
            {
                entries.Add(toggleButtonEntry.Value);
            }
            entries.Add(new IMenuMod.MenuEntry
            {
                Name = "Logging",
                Description = "Log telemetry frames at debug level",
                Values = new[] { "Off", "On" },
                Saver = i => Settings.Logging = i == 1,
                Loader = () => Settings.Logging ? 1 : 0
            });
            return entries;
        }

        public override void Initialize()
        {
            ModHooks.HeroUpdateHook += OnHeroUpdate;
            On.HeroController.FixedUpdate += OnHeroFixedUpdate;
        }

        public void Unload()
        {
            ModHooks.HeroUpdateHook -= OnHeroUpdate;
            On.HeroController.FixedUpdate -= OnHeroFixedUpdate;
            TelemetryCollector.Stop();
        }

        private void OnHeroFixedUpdate(On.HeroController.orig_FixedUpdate orig, HeroController self)
        {
            orig(self);
            TelemetryCollector.Tick();
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
