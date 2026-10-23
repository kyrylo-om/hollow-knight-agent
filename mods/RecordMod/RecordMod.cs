using CoreMod;
using Modding;

namespace RecordMod
{
    public class RecordMod : Mod, ITogglableMod
    {
        public static RecordMod Instance { get; private set; }
        private FileTelemetryConsumer _consumer;

        public RecordMod() : base("RecordMod") { }

        public override string GetVersion() => GetType().Assembly.GetName().Version.ToString();

        public override void Initialize()
        {
            Instance = this;
            _consumer = new FileTelemetryConsumer();
            TelemetryProvider.RegisterConsumer(_consumer);
            Log($"Initialized RecordMod. Episodes will be saved to: {_consumer.OutputDirectory}");
        }

        public void Unload()
        {
            if (_consumer != null)
            {
                TelemetryProvider.UnregisterConsumer(_consumer);
                _consumer.Dispose();
                _consumer = null;
            }
            Log("Unloaded RecordMod.");
        }
    }
}
