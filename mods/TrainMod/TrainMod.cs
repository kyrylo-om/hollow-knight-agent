using Modding;
using UnityEngine;

namespace TrainMod
{
    public class TrainMod : Mod, ITogglableMod
    {
        public TrainMod() : base("TrainMod") { }

        public override string GetVersion() => GetType().Assembly.GetName().Version.ToString();

        public override void Initialize()
        {
            RenderingManager.Hook();
            ModHooks.HeroUpdateHook += OnHeroUpdate;
        }

        public void Unload()
        {
            ModHooks.HeroUpdateHook -= OnHeroUpdate;
            RenderingManager.Unhook();
        }

        private void OnHeroUpdate()
        {
            if (Input.GetKeyDown(KeyCode.Alpha0) || Input.GetKeyDown(KeyCode.Keypad0))
            {
                bool isRendering = RenderingManager.ToggleRendering();
                Log($"Toggled rendering: {(isRendering ? "ON" : "OFF (Headless / ML Speedup)")}");
            }
        }
    }
}
