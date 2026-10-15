using Modding;

namespace RecordMod
{
    public class RecordMod : Mod
    {
        public RecordMod() : base("RecordMod") { }

        public override string GetVersion() => GetType().Assembly.GetName().Version.ToString();
    }
}
