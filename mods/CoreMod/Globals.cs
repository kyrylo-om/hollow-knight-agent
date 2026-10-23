using System.Collections.Generic;
using System.Linq;

namespace CoreMod
{
    /// <summary>
    /// A Hall of Gods boss: stable numeric id plus its scene(s).
    /// </summary>
    public class BossInfo
    {
        public readonly byte Id;
        public readonly string Name;
        public readonly string SceneName;        // Hall of Gods scene
        public readonly string VariantSceneName; // Pantheon variant scene, or null if the pantheon reuses SceneName

        public BossInfo(byte id, string name, string sceneName, string variantSceneName = null)
        {
            Id = id;
            Name = name;
            SceneName = sceneName;
            VariantSceneName = variantSceneName;
        }
    }

    public static class Globals
    {
        /// <summary>
        /// Id written to <see cref="EpisodeFileHeader.BossId"/> when the scene is not a known boss.
        /// </summary>
        public const byte UnknownBossId = 0;

        // Ids are persisted in episode files: append new entries, never renumber.
        public static readonly List<BossInfo> Bosses = new List<BossInfo>
        {
            new BossInfo(1,  "Gruz Mother",          "GG_Gruz_Mother",       "GG_Gruz_Mother_V"),
            new BossInfo(2,  "Vengefly King",        "GG_Vengefly",          "GG_Vengefly_V"),
            new BossInfo(3,  "Brooding Mawlek",      "GG_Brooding_Mawlek",   "GG_Brooding_Mawlek_V"),
            new BossInfo(4,  "False Knight",         "GG_False_Knight"),
            new BossInfo(5,  "Failed Champion",      "GG_Failed_Champion"),
            new BossInfo(6,  "Hornet Protector",     "GG_Hornet_1"),
            new BossInfo(7,  "Hornet Sentinel",      "GG_Hornet_2"),
            new BossInfo(8,  "Massive Moss Charger", "GG_Mega_Moss_Charger"),
            new BossInfo(9,  "Flukemarm",            "GG_Flukemarm"),
            new BossInfo(10, "Mantis Lords",         "GG_Mantis_Lords"),
            new BossInfo(11, "Sisters of Battle",    "GG_Mantis_Lords_V"),
            new BossInfo(12, "Oblobbles",            "GG_Oblobbles"),
            new BossInfo(13, "Hive Knight",          "GG_Hive_Knight"),
            new BossInfo(14, "Broken Vessel",        "GG_Broken_Vessel"),
            new BossInfo(15, "Lost Kin",             "GG_Lost_Kin"),
            new BossInfo(16, "Nosk",                 "GG_Nosk",              "GG_Nosk_V"),
            new BossInfo(17, "Winged Nosk",          "GG_Nosk_Hornet"),
            new BossInfo(18, "The Collector",        "GG_Collector",         "GG_Collector_V"),
            new BossInfo(19, "God Tamer",            "GG_God_Tamer"),
            new BossInfo(20, "Crystal Guardian",     "GG_Crystal_Guardian"),
            new BossInfo(21, "Enraged Guardian",     "GG_Crystal_Guardian_2"),
            new BossInfo(22, "Uumuu",                "GG_Uumuu",             "GG_Uumuu_V"),
            new BossInfo(23, "Traitor Lord",         "GG_Traitor_Lord"),
            new BossInfo(24, "Grey Prince Zote",     "GG_Grey_Prince_Zote"),
            new BossInfo(25, "Soul Warrior",         "GG_Mage_Knight",       "GG_Mage_Knight_V"),
            new BossInfo(26, "Soul Master",          "GG_Soul_Master"),
            new BossInfo(27, "Soul Tyrant",          "GG_Soul_Tyrant"),
            new BossInfo(28, "Dung Defender",        "GG_Dung_Defender"),
            new BossInfo(29, "White Defender",       "GG_White_Defender"),
            new BossInfo(30, "Watcher Knights",      "GG_Watcher_Knights"),
            new BossInfo(31, "No Eyes",              "GG_Ghost_No_Eyes",     "GG_Ghost_No_Eyes_V"),
            new BossInfo(32, "Marmu",                "GG_Ghost_Marmu",       "GG_Ghost_Marmu_V"),
            new BossInfo(33, "Galien",               "GG_Ghost_Galien"),
            new BossInfo(34, "Markoth",              "GG_Ghost_Markoth",     "GG_Ghost_Markoth_V"),
            new BossInfo(35, "Xero",                 "GG_Ghost_Xero",        "GG_Ghost_Xero_V"),
            new BossInfo(36, "Gorb",                 "GG_Ghost_Gorb",        "GG_Ghost_Gorb_V"),
            new BossInfo(37, "Elder Hu",             "GG_Ghost_Hu"),
            new BossInfo(38, "Oro & Mato",           "GG_Nailmasters"),
            new BossInfo(39, "Paintmaster Sheo",     "GG_Painter"),
            new BossInfo(40, "Great Nailsage Sly",   "GG_Sly"),
            new BossInfo(41, "Pure Vessel",          "GG_Hollow_Knight"),
            new BossInfo(42, "Grimm",                "GG_Grimm"),
            new BossInfo(43, "Nightmare King Grimm", "GG_Grimm_Nightmare"),
            new BossInfo(44, "Absolute Radiance",    "GG_Radiance")
        };

        /// <summary>
        /// Returns the boss fought in the given scene (Hall of Gods or pantheon variant), or null.
        /// </summary>
        public static BossInfo FindBossByScene(string sceneName) =>
            Bosses.FirstOrDefault(b => b.SceneName == sceneName || b.VariantSceneName == sceneName);
    }
}
