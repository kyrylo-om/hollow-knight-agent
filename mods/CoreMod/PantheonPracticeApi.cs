// -------------------------------------------------------------------------------------------------
// Copyright (c) 2021 TheMulhima
// Adapted from Easier-Pantheon-Practice (https://github.com/TheMulhima/Easier-Pantheon-Practice)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
// -------------------------------------------------------------------------------------------------

using System;
using System.Collections.Generic;
using System.Linq;
using Modding;
using UnityEngine;

namespace CoreMod
{
    /// <summary>
    /// Boss difficulty tier in Hall of Gods / Godhome.
    /// </summary>
    public enum BossDifficulty
    {
        Attuned = 0,
        Ascended = 1,
        Radiant = 2
    }

    /// <summary>
    /// Metadata for a Godhome boss encounter.
    /// </summary>
    public class BossInfo
    {
        public int Index { get; set; }
        public string DisplayName { get; set; }
        public string AttunedScene { get; set; }
        public string AscendedScene { get; set; }
        public string RadiantScene { get; set; }

        public BossInfo(int index, string displayName, string attunedScene, string ascendedScene = null, string radiantScene = null)
        {
            Index = index;
            DisplayName = displayName;
            AttunedScene = attunedScene;
            AscendedScene = ascendedScene ?? attunedScene;
            RadiantScene = radiantScene ?? AscendedScene;
        }

        public string GetSceneForDifficulty(BossDifficulty difficulty)
        {
            switch (difficulty)
            {
                case BossDifficulty.Ascended:
                    return AscendedScene;
                case BossDifficulty.Radiant:
                    return RadiantScene;
                default:
                    return AttunedScene;
            }
        }
    }

    /// <summary>
    /// Public API for entering any Godhome boss encounter or Pantheon sequence on command at any difficulty.
    /// Derived from and incorporating scene transition routines from Easier-Pantheon-Practice (TheMulhima).
    /// </summary>
    public static class PantheonPracticeApi
    {
        public static string CurrentBossScene { get; private set; } = string.Empty;
        public static BossDifficulty CurrentDifficulty { get; private set; } = BossDifficulty.Attuned;

        private static float _lastReloadTime = 0f;
        private static bool _isHooked;

        /// <summary>
        /// Boss registry. The first 5 bosses correspond to the first 5 statues in the Hall of Gods room from left to right.
        /// </summary>
        public static readonly List<BossInfo> Bosses = new List<BossInfo>
        {
            new BossInfo(1, "Gruz Mother", "GG_Gruz_Mother", "GG_Gruz_Mother_V"),
            new BossInfo(2, "Vengefly King", "GG_Vengefly", "GG_Vengefly_V"),
            new BossInfo(3, "Brooding Mawlek", "GG_Brooding_Mawlek", "GG_Brooding_Mawlek_V"),
            new BossInfo(4, "False Knight", "GG_False_Knight"),
            new BossInfo(5, "Massive Moss Charger", "GG_Mega_Moss_Charger"),
            new BossInfo(6, "Hornet Protector", "GG_Hornet_1"),
            new BossInfo(7, "Gorb", "GG_Ghost_Gorb", "GG_Ghost_Gorb_V"),
            new BossInfo(8, "Dung Defender", "GG_Dung_Defender"),
            new BossInfo(9, "Soul Warrior", "GG_Mage_Knight", "GG_Mage_Knight_V"),
            new BossInfo(10, "Xero", "GG_Ghost_Xero", "GG_Ghost_Xero_V"),
            new BossInfo(11, "Crystal Guardian", "GG_Crystal_Guardian"),
            new BossInfo(12, "Soul Master", "GG_Soul_Master"),
            new BossInfo(13, "Oblobbles", "GG_Oblobbles"),
            new BossInfo(14, "Mantis Lords", "GG_Mantis_Lords", "GG_Mantis_Lords", "GG_Mantis_Lords_V"),
            new BossInfo(15, "Marmu", "GG_Ghost_Marmu", "GG_Ghost_Marmu_V"),
            new BossInfo(16, "Nosk", "GG_Nosk", "GG_Nosk_V"),
            new BossInfo(17, "Flukemarm", "GG_Flukemarm"),
            new BossInfo(18, "Broken Vessel", "GG_Broken_Vessel"),
            new BossInfo(19, "Galien", "GG_Ghost_Galien"),
            new BossInfo(20, "Paintmaster Sheo", "GG_Painter"),
            new BossInfo(21, "Hive Knight", "GG_Hive_Knight"),
            new BossInfo(22, "Elder Hu", "GG_Ghost_Hu"),
            new BossInfo(23, "Collector", "GG_Collector", "GG_Collector_V"),
            new BossInfo(24, "God Tamer", "GG_God_Tamer"),
            new BossInfo(25, "Troupe Master Grimm", "GG_Grimm"),
            new BossInfo(26, "Watcher Knights", "GG_Watcher_Knights"),
            new BossInfo(27, "Uumuu", "GG_Uumuu", "GG_Uumuu_V"),
            new BossInfo(28, "Winged Nosk", "GG_Nosk_Hornet"),
            new BossInfo(29, "Great Nailsage Sly", "GG_Sly"),
            new BossInfo(30, "Hornet Sentinel", "GG_Hornet_2"),
            new BossInfo(31, "Enraged Guardian", "GG_Crystal_Guardian_2"),
            new BossInfo(32, "Lost Kin", "GG_Lost_Kin"),
            new BossInfo(33, "No Eyes", "GG_Ghost_No_Eyes", "GG_Ghost_No_Eyes_V"),
            new BossInfo(34, "Traitor Lord", "GG_Traitor_Lord"),
            new BossInfo(35, "White Defender", "GG_White_Defender"),
            new BossInfo(36, "Soul Tyrant", "GG_Soul_Tyrant"),
            new BossInfo(37, "Markoth", "GG_Ghost_Markoth", "GG_Ghost_Markoth_V"),
            new BossInfo(38, "Grey Prince Zote", "GG_Grey_Prince_Zote"),
            new BossInfo(39, "Failed Champion", "GG_Failed_Champion"),
            new BossInfo(40, "Nightmare King Grimm", "GG_Grimm_Nightmare"),
            new BossInfo(41, "Pure Vessel", "GG_Hollow_Knight"),
            new BossInfo(42, "Nailmasters Oro & Mato", "GG_Nailmasters"),
            new BossInfo(43, "Sisters of Battle", "GG_Mantis_Lords_V"),
            new BossInfo(44, "Absolute Radiance", "GG_Radiance")
        };

        /// <summary>
        /// Hook scene loading listeners to track current Godhome boss scene.
        /// </summary>
        public static void Hook()
        {
            if (_isHooked) return;
            UnityEngine.SceneManagement.SceneManager.sceneLoaded += OnSceneLoaded;
            _isHooked = true;
        }

        /// <summary>
        /// Unhook scene loading listeners.
        /// </summary>
        public static void Unhook()
        {
            if (!_isHooked) return;
            UnityEngine.SceneManagement.SceneManager.sceneLoaded -= OnSceneLoaded;
            _isHooked = false;
        }

        private static void OnSceneLoaded(UnityEngine.SceneManagement.Scene scene, UnityEngine.SceneManagement.LoadSceneMode mode)
        {
            if (!string.IsNullOrEmpty(scene.name) && scene.name.StartsWith("GG_") && scene.name != "GG_Workshop" && scene.name != "GG_Atrium")
            {
                CurrentBossScene = scene.name;
            }
        }

        /// <summary>
        /// Enter a boss fight by its numeric index (1-based).
        /// Indices 1-5 correspond to the first 5 bosses in the Hall of Gods.
        /// </summary>
        public static bool EnterBoss(int bossIndex, BossDifficulty difficulty = BossDifficulty.Attuned)
        {
            BossInfo boss = Bosses.FirstOrDefault(b => b.Index == bossIndex);
            if (boss == null)
            {
                Modding.Logger.LogError($"[PantheonPracticeApi] No boss found at index {bossIndex}.");
                return false;
            }

            string scene = boss.GetSceneForDifficulty(difficulty);
            return EnterBossDirect(scene, difficulty, boss.DisplayName);
        }

        /// <summary>
        /// Enter a boss fight by boss display name or scene name.
        /// </summary>
        public static bool EnterBoss(string bossNameOrScene, BossDifficulty difficulty = BossDifficulty.Attuned)
        {
            if (string.IsNullOrEmpty(bossNameOrScene)) return false;

            // Check if matches display name
            BossInfo boss = Bosses.FirstOrDefault(b =>
                string.Equals(b.DisplayName, bossNameOrScene, StringComparison.OrdinalIgnoreCase));

            if (boss != null)
            {
                string scene = boss.GetSceneForDifficulty(difficulty);
                return EnterBossDirect(scene, difficulty, boss.DisplayName);
            }

            // Fallback: treat as direct scene name
            string sceneName = bossNameOrScene;
            string displayName = sceneName;
            BossInfo match = Bosses.FirstOrDefault(b =>
                b.AttunedScene == sceneName || b.AscendedScene == sceneName || b.RadiantScene == sceneName);
            if (match != null)
            {
                displayName = match.DisplayName;
            }

            return EnterBossDirect(sceneName, difficulty, displayName);
        }

        /// <summary>
        /// Direct scene loader with difficulty setup.
        /// </summary>
        public static bool EnterBossDirect(string sceneName, BossDifficulty difficulty, string displayName = "")
        {
            var gm = GameManager.instance;
            var hc = HeroController.instance;

            if (gm == null || hc == null)
            {
                Modding.Logger.LogError("[PantheonPracticeApi] Cannot transition: GameManager or HeroController is null.");
                return false;
            }

            if (gm.IsInSceneTransition)
            {
                return false;
            }

            CurrentBossScene = sceneName;
            CurrentDifficulty = difficulty;

            Modding.Logger.Log($"[PantheonPracticeApi] Entering boss '{(!string.IsNullOrEmpty(displayName) ? displayName : sceneName)}' [Scene: {sceneName}] at difficulty: {difficulty} (Level {(int)difficulty})");

            // Setup dream return target to Hall of Gods
            PlayerData.instance.dreamReturnScene = "GG_Workshop";
            PlayerData.instance.bossReturnEntryGate = "door_dreamReturn";
            PlayerData.instance.bossStatueTargetLevel = (int)difficulty;

            StaticVariableList.SetValue<string>("bossSceneToLoad", sceneName);

            // Setup BossSceneController callback to configure the chosen difficulty
            BossSceneController.SetupEvent = delegate (BossSceneController bsc)
            {
                if (bsc != null)
                {
                    bsc.BossLevel = (int)difficulty;
                    bsc.DreamReturnEvent = "DREAM RETURN";
                    bsc.OnBossSceneComplete += delegate
                    {
                        bsc.DoDreamReturn();
                    };
                }
            };

            // Replicate the FSM sequence from Hall of Gods
            PlayMakerFSM.BroadcastEvent("BOX DOWN DREAM");
            PlayMakerFSM.BroadcastEvent("CONVO CANCEL");

            hc.ClearMPSendEvents();
            gm.TimePasses();
            gm.ResetSemiPersistentItems();
            hc.enterWithoutInput = true;
            hc.AcceptInput();

            gm.BeginSceneTransition(new GameManager.SceneLoadInfo
            {
                SceneName = sceneName,
                EntryGateName = "door_dreamEnter",
                EntryDelay = 0f,
                Visualization = GameManager.SceneLoadVisualizations.GodsAndGlory,
                PreventCameraFadeOut = true
            });

            return true;
        }

        /// <summary>
        /// Enter a Pantheon sequence by index (1 to 5).
        /// 1 = Master, 2 = Artist, 3 = Sage, 4 = Knight, 5 = Hallownest.
        /// </summary>
        public static bool EnterPantheon(int pantheonNumber, BossSequenceController.ChallengeBindings bindings = default)
        {
            var gm = GameManager.instance;
            var hc = HeroController.instance;
            if (gm == null || hc == null) return false;
            if (gm.IsInSceneTransition) return false;

            // Search loaded BossSequence objects
            BossSequence[] allSequences = Resources.FindObjectsOfTypeAll<BossSequence>();
            string targetDoorKey = $"BossDoor_{pantheonNumber}";
            BossSequence sequence = null;

            if (allSequences != null && allSequences.Length > 0)
            {
                // Try matching by index or tier name
                sequence = allSequences.FirstOrDefault(s =>
                    s != null && s.name.IndexOf($"Tier {pantheonNumber}", StringComparison.OrdinalIgnoreCase) >= 0);

                if (sequence == null && pantheonNumber >= 1 && pantheonNumber <= allSequences.Length)
                {
                    sequence = allSequences[pantheonNumber - 1];
                }
            }

            if (sequence == null)
            {
                // Fallback: search for BossSequenceDoor objects currently in scene (e.g. GG_Atrium)
                var doors = UnityEngine.Object.FindObjectsOfType<BossSequenceDoor>();
                if (doors != null && doors.Length >= pantheonNumber)
                {
                    sequence = doors[pantheonNumber - 1].bossSequence;
                }
            }

            if (sequence == null)
            {
                Modding.Logger.LogError($"[PantheonPracticeApi] BossSequence for Pantheon {pantheonNumber} could not be resolved.");
                return false;
            }

            string firstScene = sequence.GetSceneAt(0);
            if (string.IsNullOrEmpty(firstScene))
            {
                Modding.Logger.LogError($"[PantheonPracticeApi] First scene of Pantheon {pantheonNumber} is invalid.");
                return false;
            }

            Modding.Logger.Log($"[PantheonPracticeApi] Starting Pantheon {pantheonNumber} ({sequence.name}) starting at scene '{firstScene}'");

            BossSequenceController.SetupNewSequence(sequence, bindings, targetDoorKey);

            PlayerData.instance.dreamReturnScene = "GG_Atrium";
            PlayMakerFSM.BroadcastEvent("BOX DOWN DREAM");
            PlayMakerFSM.BroadcastEvent("CONVO CANCEL");

            hc.ClearMPSendEvents();
            gm.TimePasses();
            gm.ResetSemiPersistentItems();
            hc.enterWithoutInput = true;
            hc.AcceptInput();

            gm.BeginSceneTransition(new GameManager.SceneLoadInfo
            {
                SceneName = firstScene,
                EntryGateName = "door_dreamEnter",
                EntryDelay = 0f,
                Visualization = GameManager.SceneLoadVisualizations.GodsAndGlory,
                PreventCameraFadeOut = true
            });

            return true;
        }

        /// <summary>
        /// Returns the player back to the Hall of Gods workshop (GG_Workshop).
        /// </summary>
        public static void ReturnToHallOfGods()
        {
            var gm = GameManager.instance;
            if (gm == null || gm.IsInSceneTransition) return;

            gm.BeginSceneTransition(new GameManager.SceneLoadInfo
            {
                SceneName = "GG_Workshop",
                EntryGateName = "left1",
                EntryDelay = 0f,
                Visualization = GameManager.SceneLoadVisualizations.GodsAndGlory,
                PreventCameraFadeOut = true
            });
        }

        /// <summary>
        /// Reloads the current boss fight in the current difficulty.
        /// </summary>
        public static bool ReloadBoss()
        {
            if (Time.unscaledTime - _lastReloadTime < 0.8f)
            {
                return false;
            }

            var gm = GameManager.instance;
            if (gm == null || gm.IsInSceneTransition)
            {
                return false;
            }

            _lastReloadTime = Time.unscaledTime;

            if (string.IsNullOrEmpty(CurrentBossScene))
            {
                string currentScene = gm.GetSceneNameString();
                if (!string.IsNullOrEmpty(currentScene) && currentScene.StartsWith("GG_"))
                {
                    return EnterBossDirect(currentScene, CurrentDifficulty);
                }
                Modding.Logger.LogWarn("[PantheonPracticeApi] Cannot reload: CurrentBossScene is not set and current scene is not a GG_ boss room.");
                return false;
            }

            return EnterBossDirect(CurrentBossScene, CurrentDifficulty);
        }
    }
}
