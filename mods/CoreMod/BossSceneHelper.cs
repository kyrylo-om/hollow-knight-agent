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
    /// Public API for entering any Hall of Gods boss encounter on command at any difficulty.
    /// Derived from and incorporating scene transition routines from Easier-Pantheon-Practice (TheMulhima).
    /// </summary>
    public static class BossSceneHelper
    {
        private static string _lastBossScene;
        private static BossDifficulty _lastDifficulty;
        private static float _lastReloadTime;

        /// <summary>
        /// Enter a boss scene (e.g. "GG_Gruz_Mother") at the given difficulty, as if through its Hall of Gods statue.
        /// </summary>
        public static bool EnterBoss(string sceneName, BossDifficulty difficulty)
        {
            var gm = GameManager.instance;
            var hc = HeroController.instance;

            if (gm == null || hc == null)
            {
                Modding.Logger.LogError("[BossSceneHelper] Cannot transition: GameManager or HeroController is null.");
                return false;
            }

            if (gm.IsInSceneTransition)
            {
                return false;
            }

            _lastBossScene = sceneName;
            _lastDifficulty = difficulty;

            Modding.Logger.Log($"[BossSceneHelper] Entering boss scene '{sceneName}' at difficulty: {difficulty}");

            // Setup dream return target to Hall of Gods
            PlayerData.instance.dreamReturnScene = "GG_Workshop";
            PlayerData.instance.bossReturnEntryGate = "door_dreamReturn";
            // PlayerData.instance.bossStatueTargetLevel = (int)difficulty;

            // StaticVariableList.SetValue<string>("bossSceneToLoad", sceneName);

            // Setup BossSceneController callback to configure the chosen difficulty
            BossSceneController.SetupEvent = delegate (BossSceneController bsc)
            {
                if (bsc != null)
                {
                    bsc.BossLevel = (int)difficulty;
                    bsc.DreamReturnEvent = "DREAM RETURN";
                    bsc.OnBossSceneComplete += bsc.DoDreamReturn;
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
        /// Reloads the current boss fight (however it was entered) at its difficulty,
        /// or the last boss entered through <see cref="EnterBoss"/> when not in a boss scene.
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

            var bsc = BossSceneController.Instance;
            if (bsc != null)
            {
                return EnterBoss(gm.GetSceneNameString(), (BossDifficulty)bsc.BossLevel);
            }

            if (string.IsNullOrEmpty(_lastBossScene))
            {
                Modding.Logger.LogWarn("[BossSceneHelper] Cannot reload: not in a boss scene and no boss entered yet.");
                return false;
            }

            return EnterBoss(_lastBossScene, _lastDifficulty);
        }
    }
}
