using System;
using System.Linq;
using System.Reflection;
using Modding;
using UnityEngine;

namespace CoreMod
{
    /// <summary>
    /// Reads game state into <see cref="EpisodeFileHeader"/> (once per boss fight)
    /// and <see cref="FrameDataHeader"/> (every fixed tick), and logs both at debug level.
    /// </summary>
    public static class TelemetryCollector
    {
        private static bool _active;
        private static bool _episodeCompleted;
        private static uint _frameId;
        private static int _prevKnightHp;
        private static int _prevBossHp;
        private static float _invulnRemaining;

        private static BossInfo _bossInfo;
        private static HealthManager _boss;
        private static Rigidbody2D _bossBody;
        private static Collider2D _bossCollider;
        private static PlayMakerFSM _bossFsm;
        private static ushort _bossFsmState;
        private static ushort _prevBossFsmState;
        private static float _fsmStateTime;
        private static readonly EntityData[] _entities = new EntityData[64];
        private static int _entityCount;

        // HeroController.CanDash is private; it covers the cooldown and the one-dash-per-airtime rule.
        private static readonly Func<HeroController, bool> HeroCanDash =
            (Func<HeroController, bool>)Delegate.CreateDelegate(
                typeof(Func<HeroController, bool>),
                typeof(HeroController).GetMethod("CanDash", BindingFlags.NonPublic | BindingFlags.Instance));

        /// <summary>
        /// Call once per FixedUpdate. Does nothing outside boss scenes.
        /// </summary>
        public static void Tick()
        {
            if (BossSceneController.Instance == null || HeroController.instance == null)
            {
                if (_active)
                {
                    EndEpisode();
                }
                _episodeCompleted = false;
                return;
            }

            // Once the fight concludes (boss defeated or knight died), stop recording
            // while the death animation / Godhome transition plays out.
            if (_episodeCompleted)
            {
                return;
            }

            if (!_active)
            {
                // Wait until the boss scene transition finishes and the hero is placed in the arena
                if (!BossSceneController.Instance.HasTransitionedIn && HeroController.instance.transform.position.x >= 150f)
                {
                    return;
                }
                BeginEpisode();
            }

            FrameDataHeader frame = BuildFrame();
            if (CoreMod.Settings.Logging) Modding.Logger.LogDebug(Format(frame));
            TelemetryProvider.DispatchFrame(in frame, _entities, _entityCount);

            if (frame.IsDone != EpisodeStatus.InProgress)
            {
                EndEpisode();
                _episodeCompleted = true;
            }

            _frameId++;
        }

        /// <summary>
        /// Ends any active episode. Call when ticking stops (e.g. the mod is disabled).
        /// </summary>
        public static void Stop()
        {
            EndEpisode();
            _episodeCompleted = false;
        }

        // =====================================================================
        // Episode
        // =====================================================================

        private static void BeginEpisode()
        {
            _active = true;
            _episodeCompleted = false;
            _frameId = 0;
            _prevKnightHp = PlayerData.instance.health;
            _invulnRemaining = 0f;
            _bossInfo = BossRegistry.FindBossByScene(GameManager.instance.GetSceneNameString());
            BindBoss(null);

            EpisodeFileHeader header = BuildEpisodeHeader();
            if (CoreMod.Settings.Logging) Modding.Logger.LogDebug(Format(header));
            TelemetryProvider.DispatchEpisodeStart(header);
        }

        private static void EndEpisode()
        {
            if (!_active) return;
            _active = false;
            TelemetryProvider.DispatchEpisodeEnd();
            if (CoreMod.Settings.Logging) Modding.Logger.LogDebug("[Telemetry] EPISODE END");
        }

        private static EpisodeFileHeader BuildEpisodeHeader()
        {
            PlayerData pd = PlayerData.instance;
            GetArenaBounds(out float minX, out float maxX, out float minY, out float maxY);
            Vector2 knightExtents = HeroController.instance.GetComponent<Collider2D>().bounds.extents;

            return new EpisodeFileHeader
            {
                Magic = EpisodeFileHeader.ExpectedMagic,
                ArenaMinX = minX,
                ArenaMaxX = maxX,
                ArenaMinY = minY,
                ArenaMaxY = maxY,
                KnightBoundWidth = knightExtents.x,
                KnightBoundHeight = knightExtents.y,
                BossId = _bossInfo != null ? _bossInfo.Id : BossRegistry.UnknownBossId,
                BossDifficulty = (byte)BossSceneController.Instance.BossLevel,
                NailDamage = (byte)pd.nailDamage,
                MaxHealth = (byte)pd.maxHealth,
                Reserved = 0
            };
        }

        public static void GetArenaBounds(out float minX, out float maxX, out float minY, out float maxY)
        {
            minX = 14.0f;
            maxX = 46.0f;
            minY = 26.2f;
            maxY = 42.0f;

            Vector2 origin = Vector2.zero;
            bool hasOrigin = false;

            // 1. Prefer heroSpawn from BossSceneController (guaranteed to be inside the arena)
            if (BossSceneController.Instance != null && BossSceneController.Instance.heroSpawn != null)
            {
                origin = BossSceneController.Instance.heroSpawn.position;
                hasOrigin = true;
            }
            // 2. Or hero position if already inside the arena (< 150.0)
            else if (HeroController.instance != null && HeroController.instance.transform.position.x < 150f)
            {
                origin = HeroController.instance.transform.position;
                hasOrigin = true;
            }
            // 3. Or boss position
            else
            {
                HealthManager boss = FindBoss();
                if (boss != null)
                {
                    origin = boss.transform.position;
                    hasOrigin = true;
                }
            }

            if (hasOrigin)
            {
                // Lift origin slightly into the air to ensure downward ray does not start inside the floor collider
                origin.y += 1.5f;

                int terrainMask = 1 << (int)GlobalEnums.PhysLayers.TERRAIN;

                RaycastHit2D hitL = Physics2D.Raycast(origin, Vector2.left, 500f, terrainMask);
                RaycastHit2D hitR = Physics2D.Raycast(origin, Vector2.right, 500f, terrainMask);
                RaycastHit2D hitD = Physics2D.Raycast(origin, Vector2.down, 500f, terrainMask);
                RaycastHit2D hitU = Physics2D.Raycast(origin, Vector2.up, 500f, terrainMask);

                if (hitL.collider != null && hitR.collider != null && hitD.collider != null)
                {
                    minX = hitL.point.x;
                    maxX = hitR.point.x;
                    minY = hitD.point.y;
                    maxY = hitU.collider != null ? hitU.point.y : (minY + 20f);
                    return;
                }
            }

            // Fallback: Check CameraLockArea trigger box
            CameraLockArea lockArea = UnityEngine.Object.FindObjectOfType<CameraLockArea>();
            if (lockArea != null)
            {
                Collider2D col = lockArea.GetComponent<Collider2D>();
                if (col != null)
                {
                    Bounds b = col.bounds;
                    if (b.size.x > 2f && b.size.y > 2f)
                    {
                        minX = b.min.x;
                        maxX = b.max.x;
                        minY = b.min.y;
                        maxY = b.max.y;
                    }
                }
            }
        }

        private static HealthManager FindBoss()
        {
            HealthManager[] bosses = BossSceneController.Instance.bosses;
            return bosses != null && bosses.Length > 0 ? bosses[0] : null;
        }

        private static void BindBoss(HealthManager boss)
        {
            _boss = boss;
            _bossBody = boss != null ? boss.GetComponent<Rigidbody2D>() : null;
            _bossCollider = boss != null ? boss.GetComponent<Collider2D>() : null;
            _bossFsm = boss != null ? FindBossFsm(boss) : null;
            _prevBossHp = boss != null ? boss.hp : 0;
            _bossFsmState = 0;
            _prevBossFsmState = 0;
            _fsmStateTime = 0f;
        }

        private static PlayMakerFSM FindBossFsm(HealthManager boss)
        {
            if (_bossInfo == null)
            {
                return null;
            }

            return boss.GetComponents<PlayMakerFSM>().FirstOrDefault(fsm => fsm.FsmName == _bossInfo.Fsm.Name);
        }

        // =====================================================================
        // Frame
        // =====================================================================

        private static FrameDataHeader BuildFrame()
        {
            HeroController hc = HeroController.instance;
            PlayerData pd = PlayerData.instance;

            if (_boss == null)
            {
                BindBoss(FindBoss());
            }

            CollectEntities();

            var frame = new FrameDataHeader { FrameId = _frameId, EntityCount = (byte)_entityCount };

            int bossHp = _boss != null ? _boss.hp : 0;
            (bool bossHit, bool knightHit) = DetectHits(pd.health, bossHp, hc);

            FillKnight(ref frame, hc, pd);
            FillBoss(ref frame);
            FillInputs(ref frame);

            frame.Flags = FrameFlagsPacking.Pack(
                BossFacingRight(),
                hc.cState.facingRight,
                _boss != null && _boss.IsInvincible,
                bossHit,
                knightHit);
            frame.IsDone = ReadStatus(pd.health, bossHp);

            return frame;
        }

        private static void CollectEntities()
        {
            _entityCount = 0;

            DamageHero[] damageHitboxes = UnityEngine.Object.FindObjectsOfType<DamageHero>();
            if (damageHitboxes == null) return;

            Transform bossTransform = _boss != null ? _boss.transform : null;
            Transform heroTransform = HeroController.instance != null ? HeroController.instance.transform : null;

            for (int i = 0; i < damageHitboxes.Length && _entityCount < _entities.Length; i++)
            {
                DamageHero dh = damageHitboxes[i];
                if (dh == null || !dh.gameObject.activeInHierarchy) continue;

                if (bossTransform != null && (dh.transform == bossTransform || dh.transform.IsChildOf(bossTransform)))
                    continue;

                if (heroTransform != null && (dh.transform == heroTransform || dh.transform.IsChildOf(heroTransform)))
                    continue;

                Collider2D col = dh.GetComponent<Collider2D>() ?? dh.GetComponentInChildren<Collider2D>();
                if (col == null) continue;

                bool isActivelyDamaging = dh.isActiveAndEnabled && dh.damageDealt > 0 && col.isActiveAndEnabled;

                Rigidbody2D rb = dh.GetComponent<Rigidbody2D>();
                HealthManager hm = dh.GetComponent<HealthManager>();
                Bounds b = col.bounds;
                Vector2 vel = rb != null ? rb.velocity : Vector2.zero;

                string name = dh.gameObject.name.ToLowerInvariant();

                if (hm != null && hm.hp > 0 && !name.Contains("barb"))
                    continue;

                float progress = 0f;

                if (!isActivelyDamaging)
                {
                    if (name.Contains("rock") || name.Contains("barrel") || name.Contains("rubble") ||
                        name.Contains("debris") || name.Contains("block") || name.Contains("stone") ||
                        name.Contains("ceiling"))
                    {
                        continue;
                    }

                    progress = GetTelegraphProgress(dh, isActivelyDamaging);
                    if (progress <= 0f)
                    {
                        continue;
                    }
                }

                EntityType kind = EntityType.Hazard;
                if (name.Contains("shockwave") || name.Contains("wave"))
                {
                    kind = EntityType.Shockwave;
                }
                else if (name.Contains("needle") || name.Contains("projectile") || name.Contains("shot") || name.Contains("beam") || name.Contains("laser"))
                {
                    kind = EntityType.Projectile;
                }

                bool facingRight = vel.x > 0.05f || dh.transform.localScale.x > 0;
                bool isInvulnerable = hm == null || hm.IsInvincible;
                byte flags = (byte)(
                    (facingRight ? 1 : 0) |
                    (isInvulnerable ? 2 : 0) |
                    (isActivelyDamaging ? 4 : 0)
                );

                float halfWidth;
                float halfHeight;
                float rotation = col.transform.eulerAngles.z;

                if (col is BoxCollider2D box)
                {
                    Vector3 lossy = box.transform.lossyScale;
                    halfWidth = Mathf.Abs(box.size.x * lossy.x) * 0.5f;
                    halfHeight = Mathf.Abs(box.size.y * lossy.y) * 0.5f;
                }
                else if (col is CircleCollider2D circle)
                {
                    Vector3 lossy = circle.transform.lossyScale;
                    halfWidth = circle.radius * Mathf.Max(Mathf.Abs(lossy.x), Mathf.Abs(lossy.y));
                    halfHeight = halfWidth;
                    rotation = 0f;
                }
                else
                {
                    halfWidth = b.extents.x;
                    halfHeight = b.extents.y;
                }

                _entities[_entityCount++] = new EntityData
                {
                    X = b.center.x,
                    Y = b.center.y,
                    Vx = vel.x,
                    Vy = vel.y,
                    BoundWidth = halfWidth,
                    BoundHeight = halfHeight,
                    Rotation = rotation,
                    Progress = progress,
                    EntityId = (short)dh.gameObject.GetInstanceID(),
                    Hp = (short)(hm != null ? Mathf.Clamp(hm.hp, 0, short.MaxValue) : 0),
                    Kind = kind,
                    Flags = flags,
                    Reserved = 0
                };
            }
        }

        private static float GetTelegraphProgress(DamageHero dh, bool isActivelyDamaging)
        {
            if (isActivelyDamaging)
            {
                return 0f;
            }

            PlayMakerFSM[] fsms = dh.GetComponents<PlayMakerFSM>();
            if (fsms == null || fsms.Length == 0)
            {
                fsms = dh.GetComponentsInParent<PlayMakerFSM>();
            }

            if (fsms != null)
            {
                for (int i = 0; i < fsms.Length; i++)
                {
                    PlayMakerFSM fsm = fsms[i];
                    if (fsm == null || fsm.Fsm == null) continue;

                    string state = fsm.ActiveStateName?.ToLowerInvariant() ?? "";
                    if (state.Contains("land") || state.Contains("impact") || state.Contains("shatter") ||
                        state.Contains("break") || state.Contains("burst") || state.Contains("die") ||
                        state.Contains("dead") || state.Contains("destroy") || state.Contains("recycle") ||
                        state.Contains("dissipate") || state.Contains("fade") || state.Contains("idle") ||
                        state.Contains("dormant"))
                    {
                        continue;
                    }

                    var vars = fsm.FsmVariables;
                    if (vars != null)
                    {
                        var timer = vars.FindFsmFloat("Timer") ?? vars.FindFsmFloat("Time Left") ?? vars.FindFsmFloat("Countdown");
                        if (timer != null && timer.Value > 0f)
                        {
                            return timer.Value;
                        }

                        var antic = vars.FindFsmFloat("Antic Time") ?? vars.FindFsmFloat("Telegraph Time") ?? vars.FindFsmFloat("Aim Time") ?? vars.FindFsmFloat("Charge Time");
                        if (antic != null && antic.Value > 0f)
                        {
                            return antic.Value;
                        }

                        var timeVar = vars.FindFsmFloat("Time");
                        if (timeVar != null && timeVar.Value > 0f)
                        {
                            return timeVar.Value;
                        }
                    }
                }
            }

            string objName = dh.gameObject.name.ToLowerInvariant();
            if ((objName.Contains("beam") || objName.Contains("laser") || objName.Contains("shot")) &&
                _bossFsm != null && _bossFsm.Fsm != null)
            {
                string bossState = _bossFsm.ActiveStateName?.ToLowerInvariant() ?? "";
                if (bossState.Contains("aim") || bossState.Contains("laser antic") || bossState.Contains("beam antic"))
                {
                    var aimVar = _bossFsm.FsmVariables?.FindFsmFloat("Aim Time") ?? _bossFsm.FsmVariables?.FindFsmFloat("Antic Time");
                    if (aimVar != null && aimVar.Value > 0f)
                    {
                        return Mathf.Max(0f, aimVar.Value - _fsmStateTime);
                    }
                    return Mathf.Max(0.01f, _fsmStateTime);
                }
            }

            return 0f;
        }

        private static void FillKnight(ref FrameDataHeader f, HeroController hc, PlayerData pd)
        {
            Vector2 position = hc.GetComponent<Collider2D>().bounds.center;
            Vector2 velocity = hc.GetComponent<Rigidbody2D>().velocity;
            float nailCooldown = ReflectionHelper.GetField<HeroController, float>(hc, "attack_cooldown");
            float dashCooldown = ReflectionHelper.GetField<HeroController, float>(hc, "dashCooldownTimer");
            float shadowDashCooldown = ReflectionHelper.GetField<HeroController, float>(hc, "shadowDashTimer");

            // A shadow dash makes the knight immune to enemy damage until the dash ends (dash_timer > DASH_TIME)
            float invulnRemaining = _invulnRemaining;
            if (hc.cState.shadowDashing)
            {
                float dashTimer = ReflectionHelper.GetField<HeroController, float>(hc, "dash_timer");
                invulnRemaining = Mathf.Max(invulnRemaining, hc.DASH_TIME - dashTimer);
            }

            f.KnightX = position.x;
            f.KnightY = position.y;
            f.KnightVx = velocity.x;
            f.KnightVy = velocity.y;
            f.KnightHp = (byte)pd.health;
            f.KnightMp = (byte)pd.MPCharge;
            f.KnightMpReserve = (byte)(pd.MPReserve / 33);
            f.KnightFlags = ReadKnightFlags(hc, pd, nailCooldown);
            f.NailCooldown = nailCooldown;
            f.DashCooldown = dashCooldown;
            f.ShadowDashCooldown = Mathf.Max(0f, shadowDashCooldown);
            f.InvulnRemaining = invulnRemaining;
            f.FocusProgress = 0f; // TODO placeholder
        }

        private static KnightFlags ReadKnightFlags(HeroController hc, PlayerData pd, float nailCooldown)
        {
            HeroControllerStates s = hc.cState;
            bool doubleJumped = ReflectionHelper.GetField<HeroController, bool>(hc, "doubleJumped");
            KnightFlags flags = KnightFlags.None;

            if (s.onGround)                            flags |= KnightFlags.OnGround;
            if (s.touchingWall)                        flags |= KnightFlags.TouchingWall;
            if (s.wallSliding)                         flags |= KnightFlags.WallSliding;
            if (s.dashing)                             flags |= KnightFlags.IsDashing;
            if (s.invulnerable)                        flags |= KnightFlags.IsInvulnerable;
            if (pd.hasDoubleJump && !doubleJumped)     flags |= KnightFlags.CanDoubleJump;
            if (HeroCanDash(hc))                       flags |= KnightFlags.CanDash;
            if (nailCooldown <= 0f)                    flags |= KnightFlags.CanAttack;
            if (s.focusing)                            flags |= KnightFlags.IsFocusing;
            if (s.recoiling)                           flags |= KnightFlags.IsRecoiling;
            if (s.attacking)                           flags |= KnightFlags.IsAttacking;
            if (s.shadowDashing)                       flags |= KnightFlags.IsShadowDashing;
            // TODO: IsCasting (derive from hc.spellControl FSM)

            return flags;
        }

        private static void FillBoss(ref FrameDataHeader f)
        {
            if (_boss == null)
            {
                return;
            }

            if (_bossCollider != null)
            {
                Bounds bounds = _bossCollider.bounds;
                f.BossX = bounds.center.x;
                f.BossY = bounds.center.y;
                f.BossBoundWidth = bounds.extents.x;
                f.BossBoundHeight = bounds.extents.y;
            }

            if (_bossBody != null)
            {
                f.BossVx = _bossBody.velocity.x;
                f.BossVy = _bossBody.velocity.y;
            }

            f.BossHp = _boss.hp;

            UpdateBossFsm();
            f.BossFsmState = _bossFsmState;
            f.PrevFsmState = _prevBossFsmState;
            f.FsmStateTime = _fsmStateTime;
        }

        private static void UpdateBossFsm()
        {
            if (_bossFsm == null)
            {
                return;
            }

            ushort state = StateId(_bossFsm.ActiveStateName);
            if (state != _bossFsmState)
            {
                _prevBossFsmState = _bossFsmState;
                _bossFsmState = state;
                _fsmStateTime = 0f;
            }
            else
            {
                _fsmStateTime += Time.fixedDeltaTime;
            }
        }

        private static ushort StateId(string stateName) =>
            BossFsm.Pack(_bossInfo.Id, _bossInfo.Fsm.StateId(stateName));

        private static bool BossFacingRight() => _boss != null && _boss.transform.localScale.x > 0f;

        private static (bool bossHit, bool knightHit) DetectHits(int knightHp, int bossHp, HeroController hc)
        {
            bool bossHit = bossHp < _prevBossHp;
            bool knightHit = knightHp < _prevKnightHp;

            if (knightHit)
            {
                _invulnRemaining = hc.INVUL_TIME;
            }
            else if (!hc.cState.invulnerable)
            {
                _invulnRemaining = 0f;
            }
            else
            {
                _invulnRemaining = Mathf.Max(0f, _invulnRemaining - Time.fixedDeltaTime);
            }

            _prevBossHp = bossHp;
            _prevKnightHp = knightHp;
            return (bossHit, knightHit);
        }

        private static EpisodeStatus ReadStatus(int knightHp, int bossHp)
        {
            if (knightHp <= 0) return EpisodeStatus.KnightDied;
            if (_boss != null && bossHp <= 0) return EpisodeStatus.BossDefeated;
            return EpisodeStatus.InProgress;
        }

        // =====================================================================
        // Input
        // =====================================================================

        private static void FillInputs(ref FrameDataHeader f)
        {
            HeroActions actions = InputHandler.Instance.inputActions;
            f.ActionHeld = ReadHeld(actions);
            f.ActionPressed = ReadPressed(actions);
        }

        private static ActionButtons ReadHeld(HeroActions a)
        {
            ActionButtons b = ActionButtons.None;
            if (a.jump.IsPressed)   b |= ActionButtons.Jump;
            if (a.attack.IsPressed) b |= ActionButtons.Attack;
            if (a.dash.IsPressed)   b |= ActionButtons.Dash;
            if (a.cast.IsPressed)   b |= ActionButtons.CastFocus;
            if (a.left.IsPressed)   b |= ActionButtons.Left;
            if (a.right.IsPressed)  b |= ActionButtons.Right;
            if (a.up.IsPressed)     b |= ActionButtons.Up;
            if (a.down.IsPressed)   b |= ActionButtons.Down;
            return b;
        }

        private static ActionButtons ReadPressed(HeroActions a)
        {
            ActionButtons b = ActionButtons.None;
            if (a.jump.WasPressed)   b |= ActionButtons.Jump;
            if (a.attack.WasPressed) b |= ActionButtons.Attack;
            if (a.dash.WasPressed)   b |= ActionButtons.Dash;
            if (a.cast.WasPressed)   b |= ActionButtons.CastFocus;
            if (a.left.WasPressed)   b |= ActionButtons.Left;
            if (a.right.WasPressed)  b |= ActionButtons.Right;
            if (a.up.WasPressed)     b |= ActionButtons.Up;
            if (a.down.WasPressed)   b |= ActionButtons.Down;
            return b;
        }

        // =====================================================================
        // Formatting
        // =====================================================================

        private static string Format(EpisodeFileHeader h) =>
            $"[Telemetry] EPISODE magic=0x{h.Magic:X16} boss={h.BossId} diff={h.BossDifficulty} " +
            $"nail={h.NailDamage} maxHp={h.MaxHealth} knight={h.KnightBoundWidth:F2}x{h.KnightBoundHeight:F2} " +
            $"arena=({h.ArenaMinX:F2}..{h.ArenaMaxX:F2}, {h.ArenaMinY:F2}..{h.ArenaMaxY:F2})";

        private static string Format(FrameDataHeader f) =>
            $"[Telemetry] F={f.FrameId} status={f.IsDone} " +
            $"K(pos={f.KnightX:F2},{f.KnightY:F2} vel={f.KnightVx:F2},{f.KnightVy:F2} " +
            $"hp={f.KnightHp} mp={f.KnightMp} res={f.KnightMpReserve} " +
            $"nailCd={f.NailCooldown:F2} dashCd={f.DashCooldown:F2} sdashCd={f.ShadowDashCooldown:F2} invuln={f.InvulnRemaining:F2} focus={f.FocusProgress:F2} " +
            $"flags={f.KnightFlags}) " +
            $"B(pos={f.BossX:F2},{f.BossY:F2} vel={f.BossVx:F2},{f.BossVy:F2} " +
            $"bounds={f.BossBoundWidth:F2}x{f.BossBoundHeight:F2} hp={f.BossHp} " +
            $"fsm=\"{StateName(f.BossFsmState)}\" prev=\"{StateName(f.PrevFsmState)}\" t={f.FsmStateTime:F2}) " +
            $"frame={f.Flags} entities={f.EntityCount} " +
            $"in(pressed={f.ActionPressed} held={f.ActionHeld})";

        // Low byte of a packed FSM state is the state id; the high byte is the boss id.
        private static string StateName(ushort packedState) =>
            _bossInfo?.Fsm.StateName((byte)packedState) ?? "?";
    }
}
