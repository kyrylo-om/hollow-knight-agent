using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityStandardAssets.ImageEffects;

namespace TrainMod
{
    /// <summary>
    /// Turns scene rendering off and on (with VSync and the framerate cap) to speed up AI agent training.
    /// </summary>
    public static class RenderingManager
    {
        public static bool IsRenderingEnabled { get; private set; } = true;

        private static readonly Dictionary<Camera, int> _savedCullingMasks = new Dictionary<Camera, int>();
        private static readonly Dictionary<Behaviour, bool> _savedImageEffects = new Dictionary<Behaviour, bool>();
        private static int _savedVSync = 1;
        private static int _savedTargetFrameRate = -1;
        private static bool _isHooked;

        /// <summary>
        /// Hook into scene loading so cameras in newly loaded scenes are also culled while rendering is off.
        /// </summary>
        public static void Hook()
        {
            if (_isHooked) return;
            UnityEngine.SceneManagement.SceneManager.sceneLoaded += OnSceneLoaded;
            _isHooked = true;
        }

        /// <summary>
        /// Unhook scene loading listeners and restore normal rendering.
        /// </summary>
        public static void Unhook()
        {
            if (!_isHooked) return;
            UnityEngine.SceneManagement.SceneManager.sceneLoaded -= OnSceneLoaded;
            _isHooked = false;

            if (!IsRenderingEnabled)
            {
                SetRendering(true);
            }
        }

        public static bool ToggleRendering()
        {
            SetRendering(!IsRenderingEnabled);
            return IsRenderingEnabled;
        }

        public static void SetRendering(bool enable)
        {
            if (IsRenderingEnabled == enable) return;

            IsRenderingEnabled = enable;

            if (!enable)
            {
                _savedVSync = QualitySettings.vSyncCount;
                _savedTargetFrameRate = Application.targetFrameRate;

                // Uncap engine execution so the CPU loop runs at maximum speed
                QualitySettings.vSyncCount = 0;
                Application.targetFrameRate = -1;

                ApplyNoRenderingToActiveCameras();
                DisableImageEffects();

                Modding.Logger.Log("[RenderingManager] Rendering DISABLED. Culling masks set to 0, VSync disabled, framerate uncapped.");
            }
            else
            {
                QualitySettings.vSyncCount = _savedVSync;
                Application.targetFrameRate = _savedTargetFrameRate;

                RestoreActiveCameras();
                RestoreImageEffects();

                Modding.Logger.Log("[RenderingManager] Rendering ENABLED. Restored camera culling masks and display settings.");
            }
        }

        /// <summary>
        /// Sets cullingMask = 0 on active cameras, caching their original values.
        /// </summary>
        private static void ApplyNoRenderingToActiveCameras()
        {
            Camera[] cameras = Camera.allCameras;
            if (cameras == null) return;

            foreach (Camera cam in cameras)
            {
                if (cam == null) continue;

                // Letterbox clearing cameras intentionally have cullingMask == 0 to only clear solid black outside 16:9.
                // Never touch cameras that already have cullingMask == 0!
                if (cam.cullingMask == 0) continue;

                if (!_savedCullingMasks.ContainsKey(cam))
                {
                    _savedCullingMasks[cam] = cam.cullingMask;
                }

                cam.cullingMask = 0;
            }
        }

        private static void RestoreActiveCameras()
        {
            foreach (var kvp in _savedCullingMasks)
            {
                if (kvp.Key != null)
                {
                    kvp.Key.cullingMask = kvp.Value;
                }
            }

            _savedCullingMasks.Clear();
        }

        /// <summary>
        /// Disables the image effects that GameCameras.DisableImageEffects turns off, caching their original enabled state.
        /// </summary>
        private static void DisableImageEffects()
        {
            try
            {
                if (GameCameras.instance == null || GameCameras.instance.mainCamera == null) return;

                Camera cam = GameCameras.instance.mainCamera;
                foreach (Behaviour effect in new Behaviour[] { cam.GetComponent<FastNoise>(), cam.GetComponent<BloomOptimized>(), cam.GetComponent<ColorCorrectionCurves>() })
                {
                    if (effect == null) continue;
                    _savedImageEffects[effect] = effect.enabled;
                    effect.enabled = false;
                }
            }
            catch (Exception e)
            {
                Modding.Logger.LogWarn($"[RenderingManager] Failed to disable image effects: {e}");
            }
        }

        private static void RestoreImageEffects()
        {
            try
            {
                foreach (var kvp in _savedImageEffects)
                {
                    if (kvp.Key != null)
                    {
                        kvp.Key.enabled = kvp.Value;
                    }
                }
            }
            catch (Exception e)
            {
                Modding.Logger.LogWarn($"[RenderingManager] Failed to restore image effects: {e}");
            }

            _savedImageEffects.Clear();
        }

        private static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            if (!IsRenderingEnabled)
            {
                ApplyNoRenderingToActiveCameras();
            }
        }
    }
}
