// -------------------------------------------------------------------------------------------------
// Copyright (c) 2026 Antigravity / Hollow Knight Agent Team
// Licensed under GNU Affero General Public License v3.0
// -------------------------------------------------------------------------------------------------

using System;
using System.Collections.Generic;
using Modding;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace TrainMod
{
    /// <summary>
    /// Controls camera rendering, VSync, framerate uncapping, and simulation time scale
    /// to enable ultra-fast execution for machine learning and AI agent training.
    /// </summary>
    public static class RenderingManager
    {
        /// <summary>
        /// Whether scene rendering is currently active.
        /// When false, camera culling masks are set to 0, VSync is disabled, and framerates are uncapped.
        /// </summary>
        public static bool IsRenderingEnabled { get; private set; } = true;

        /// <summary>
        /// Available simulation speed multipliers.
        /// </summary>
        public static readonly float[] SpeedPresets = new float[] { 0.5f, 1.0f, 2.0f, 5.0f, 10.0f, 20.0f };

        private static int _currentSpeedIndex = 1; // Default: 1.0f
        private static readonly Dictionary<Camera, int> _savedCullingMasks = new Dictionary<Camera, int>();
        private static int _savedVSync = 1;
        private static int _savedTargetFrameRate = -1;
        private static bool _isHooked;

        /// <summary>
        /// Hook into scene loading to ensure newly created cameras also have rendering disabled
        /// when running in headless / no-render mode.
        /// </summary>
        public static void Hook()
        {
            if (_isHooked) return;
            UnityEngine.SceneManagement.SceneManager.sceneLoaded += OnSceneLoaded;
            _isHooked = true;
        }

        /// <summary>
        /// Unhook scene loading listeners and restore normal rendering and time scale.
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

            ResetTimeScale();
        }

        /// <summary>
        /// Toggles rendering on and off.
        /// </summary>
        public static bool ToggleRendering()
        {
            SetRendering(!IsRenderingEnabled);
            return IsRenderingEnabled;
        }

        /// <summary>
        /// Enables or disables scene rendering.
        /// Disabling rendering clears camera culling masks to 0 and removes VSync/framerate caps.
        /// </summary>
        public static void SetRendering(bool enable)
        {
            if (IsRenderingEnabled == enable) return;

            IsRenderingEnabled = enable;

            if (!enable)
            {
                // 1. Save original VSync and Framerate settings
                _savedVSync = QualitySettings.vSyncCount;
                _savedTargetFrameRate = Application.targetFrameRate;

                // 2. Uncap engine execution so the CPU loop runs at maximum speed
                QualitySettings.vSyncCount = 0;
                Application.targetFrameRate = -1;

                // 3. Set camera culling masks to 0 (culls active layers, 0 draw calls, 0 sprite rendering)
                ApplyNoRenderingToActiveCameras();

                // 4. Disable image effects if GameCameras is available
                try
                {
                    if (GameCameras.instance != null)
                    {
                        GameCameras.instance.DisableImageEffects();
                    }
                }
                catch { }

                Modding.Logger.Log("[RenderingManager] Rendering DISABLED. Culling masks set to 0, VSync disabled, framerate uncapped.");
            }
            else
            {
                // 1. Restore VSync and Target Framerate
                QualitySettings.vSyncCount = _savedVSync;
                Application.targetFrameRate = _savedTargetFrameRate;

                // 2. Restore camera culling masks
                RestoreActiveCameras();

                // 3. Re-enable image effects
                try
                {
                    if (GameCameras.instance != null)
                    {
                        GameCameras.instance.EnableImageEffects(true, true);
                    }
                }
                catch { }

                Modding.Logger.Log("[RenderingManager] Rendering ENABLED. Restored camera culling masks and display settings.");
            }
        }

        /// <summary>
        /// Applies cullingMask = 0 to active rendering cameras while caching their original values.
        /// Ignores cameras that already have cullingMask == 0 (such as letterbox border clearers).
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

        /// <summary>
        /// Restores cached culling masks to all cameras.
        /// </summary>
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

        private static void OnSceneLoaded(Scene scene, LoadSceneMode mode)
        {
            // If running with rendering disabled, ensure any new cameras in the loaded scene are also culled
            if (!IsRenderingEnabled)
            {
                ApplyNoRenderingToActiveCameras();
            }
        }

        #region Time Scale Controls

        /// <summary>
        /// Gets the current simulation time scale multiplier.
        /// </summary>
        public static float CurrentTimeScale => Time.timeScale;

        /// <summary>
        /// Sets a custom simulation time scale (clamped to a minimum of 0.05).
        /// </summary>
        public static void SetTimeScale(float scale)
        {
            float target = Mathf.Max(0.05f, scale);
            Time.timeScale = target;
            Modding.Logger.Log($"[RenderingManager] Time scale set to: {target:F1}x");
        }

        /// <summary>
        /// Increases the simulation speed to the next preset multiplier.
        /// </summary>
        public static float IncreaseSpeed()
        {
            if (_currentSpeedIndex < SpeedPresets.Length - 1)
            {
                _currentSpeedIndex++;
            }
            float target = SpeedPresets[_currentSpeedIndex];
            SetTimeScale(target);
            return target;
        }

        /// <summary>
        /// Decreases the simulation speed to the previous preset multiplier.
        /// </summary>
        public static float DecreaseSpeed()
        {
            if (_currentSpeedIndex > 0)
            {
                _currentSpeedIndex--;
            }
            float target = SpeedPresets[_currentSpeedIndex];
            SetTimeScale(target);
            return target;
        }

        /// <summary>
        /// Resets the simulation speed back to standard real-time (1.0x).
        /// </summary>
        public static void ResetTimeScale()
        {
            _currentSpeedIndex = 1; // 1.0f
            SetTimeScale(1.0f);
        }

        #endregion
    }
}
