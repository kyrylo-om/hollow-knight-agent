using System.Collections.Generic;
using System.Linq;

namespace CoreMod
{
    /// <summary>
    /// The PlayMaker FSM that drives a boss, with a stable numeric id per state.
    /// </summary>
    public class BossFsm
    {
        /// <summary>
        /// State id used when the active state is not in <see cref="States"/>.
        /// </summary>
        public const byte UnknownStateId = 0;

        public readonly string Name;                         // PlayMakerFSM.FsmName on the boss GameObject
        public readonly Dictionary<string, byte> States;     // State name -> id (1..255)
        private readonly Dictionary<byte, string> _names;    // id -> state name

        public BossFsm(string name, Dictionary<string, byte> states)
        {
            Name = name;
            States = states;
            _names = states.ToDictionary(s => s.Value, s => s.Key);
        }

        public byte StateId(string stateName) =>
            stateName != null && States.TryGetValue(stateName, out byte id) ? id : UnknownStateId;

        /// <summary>
        /// Returns the state name for an id, or null for <see cref="UnknownStateId"/> and unlisted ids.
        /// </summary>
        public string StateName(byte stateId) =>
            _names.TryGetValue(stateId, out string name) ? name : null;

        /// <summary>
        /// Packs a boss id (high byte) and state id (low byte) into <see cref="FrameDataHeader.BossFsmState"/>.
        /// </summary>
        public static ushort Pack(byte bossId, byte stateId) => (ushort)((bossId << 8) | stateId);
    }

    /// <summary>
    /// A Hall of Gods boss: stable numeric id, its main FSM, and its scene(s).
    /// </summary>
    public class BossInfo
    {
        public readonly byte Id;
        public readonly string Name;
        public readonly BossFsm Fsm;
        public readonly string SceneName;        // Hall of Gods scene
        public readonly string VariantSceneName; // Pantheon variant scene, or null if the pantheon reuses SceneName

        public BossInfo(byte id, string name, BossFsm fsm, string sceneName, string variantSceneName = null)
        {
            Id = id;
            Name = name;
            Fsm = fsm;
            SceneName = sceneName;
            VariantSceneName = variantSceneName;
        }
    }

    public static class BossRegistry
    {
        /// <summary>
        /// Id written to <see cref="EpisodeFileHeader.BossId"/> when the scene is not a known boss.
        /// </summary>
        public const byte UnknownBossId = 0;

        // Ids are persisted in episode files: append new entries, never renumber.
        public static readonly List<BossInfo> Bosses = new List<BossInfo>
        {
            new BossInfo(1,  "Gruz Mother",          BossFsms.GruzMother,         "GG_Gruz_Mother",       "GG_Gruz_Mother_V"),
            new BossInfo(2,  "Vengefly King",        BossFsms.VengeflyKing,       "GG_Vengefly",          "GG_Vengefly_V"),
            new BossInfo(3,  "Brooding Mawlek",      BossFsms.BroodingMawlek,     "GG_Brooding_Mawlek",   "GG_Brooding_Mawlek_V"),
            new BossInfo(4,  "False Knight",         BossFsms.FalseKnight,        "GG_False_Knight"),
            new BossInfo(5,  "Failed Champion",      BossFsms.FailedChampion,     "GG_Failed_Champion"),
            new BossInfo(6,  "Hornet Protector",     BossFsms.HornetProtector,    "GG_Hornet_1"),
            new BossInfo(7,  "Hornet Sentinel",      BossFsms.HornetSentinel,     "GG_Hornet_2"),
            new BossInfo(8,  "Massive Moss Charger", BossFsms.MassiveMossCharger, "GG_Mega_Moss_Charger"),
            new BossInfo(9,  "Flukemarm",            BossFsms.Flukemarm,          "GG_Flukemarm"),
            new BossInfo(10, "Mantis Lords",         BossFsms.MantisLords,        "GG_Mantis_Lords"),
            new BossInfo(11, "Sisters of Battle",    BossFsms.SistersOfBattle,    "GG_Mantis_Lords_V"),
            new BossInfo(12, "Oblobbles",            BossFsms.Oblobbles,          "GG_Oblobbles"),
            new BossInfo(13, "Hive Knight",          BossFsms.HiveKnight,         "GG_Hive_Knight"),
            new BossInfo(14, "Broken Vessel",        BossFsms.BrokenVessel,       "GG_Broken_Vessel"),
            new BossInfo(15, "Lost Kin",             BossFsms.LostKin,            "GG_Lost_Kin"),
            new BossInfo(16, "Nosk",                 BossFsms.Nosk,               "GG_Nosk",              "GG_Nosk_V"),
            new BossInfo(17, "Winged Nosk",          BossFsms.WingedNosk,         "GG_Nosk_Hornet"),
            new BossInfo(18, "The Collector",        BossFsms.TheCollector,       "GG_Collector",         "GG_Collector_V"),
            new BossInfo(19, "God Tamer",            BossFsms.GodTamer,           "GG_God_Tamer"),
            new BossInfo(20, "Crystal Guardian",     BossFsms.CrystalGuardian,    "GG_Crystal_Guardian"),
            new BossInfo(21, "Enraged Guardian",     BossFsms.EnragedGuardian,    "GG_Crystal_Guardian_2"),
            new BossInfo(22, "Uumuu",                BossFsms.Uumuu,              "GG_Uumuu",             "GG_Uumuu_V"),
            new BossInfo(23, "Traitor Lord",         BossFsms.TraitorLord,        "GG_Traitor_Lord"),
            new BossInfo(24, "Grey Prince Zote",     BossFsms.GreyPrinceZote,     "GG_Grey_Prince_Zote"),
            new BossInfo(25, "Soul Warrior",         BossFsms.SoulWarrior,        "GG_Mage_Knight",       "GG_Mage_Knight_V"),
            new BossInfo(26, "Soul Master",          BossFsms.SoulMaster,         "GG_Soul_Master"),
            new BossInfo(27, "Soul Tyrant",          BossFsms.SoulTyrant,         "GG_Soul_Tyrant"),
            new BossInfo(28, "Dung Defender",        BossFsms.DungDefender,       "GG_Dung_Defender"),
            new BossInfo(29, "White Defender",       BossFsms.WhiteDefender,      "GG_White_Defender"),
            new BossInfo(30, "Watcher Knights",      BossFsms.WatcherKnights,     "GG_Watcher_Knights"),
            new BossInfo(31, "No Eyes",              BossFsms.NoEyes,             "GG_Ghost_No_Eyes",     "GG_Ghost_No_Eyes_V"),
            new BossInfo(32, "Marmu",                BossFsms.Marmu,              "GG_Ghost_Marmu",       "GG_Ghost_Marmu_V"),
            new BossInfo(33, "Galien",               BossFsms.Galien,             "GG_Ghost_Galien"),
            new BossInfo(34, "Markoth",              BossFsms.Markoth,            "GG_Ghost_Markoth",     "GG_Ghost_Markoth_V"),
            new BossInfo(35, "Xero",                 BossFsms.Xero,               "GG_Ghost_Xero",        "GG_Ghost_Xero_V"),
            new BossInfo(36, "Gorb",                 BossFsms.Gorb,               "GG_Ghost_Gorb",        "GG_Ghost_Gorb_V"),
            new BossInfo(37, "Elder Hu",             BossFsms.ElderHu,            "GG_Ghost_Hu"),
            new BossInfo(38, "Oro & Mato",           BossFsms.OroAndMato,         "GG_Nailmasters"),
            new BossInfo(39, "Paintmaster Sheo",     BossFsms.PaintmasterSheo,    "GG_Painter"),
            new BossInfo(40, "Great Nailsage Sly",   BossFsms.GreatNailsageSly,   "GG_Sly"),
            new BossInfo(41, "Pure Vessel",          BossFsms.PureVessel,         "GG_Hollow_Knight"),
            new BossInfo(42, "Grimm",                BossFsms.Grimm,              "GG_Grimm"),
            new BossInfo(43, "Nightmare King Grimm", BossFsms.NightmareKingGrimm, "GG_Grimm_Nightmare"),
            new BossInfo(44, "Absolute Radiance",    BossFsms.AbsoluteRadiance,   "GG_Radiance")
        };

        /// <summary>
        /// Returns the boss fought in the given scene (Hall of Gods or pantheon variant), or null.
        /// </summary>
        public static BossInfo FindBossByScene(string sceneName) =>
            Bosses.FirstOrDefault(b => b.SceneName == sceneName || b.VariantSceneName == sceneName);
    }
}
