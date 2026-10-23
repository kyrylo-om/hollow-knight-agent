using System.Linq;
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
        private static uint _frameId;
        private static int _prevKnightHp;
        private static int _prevBossHp;
        private static float _invulnRemaining;

        private static HealthManager _boss;
        private static Rigidbody2D _bossBody;
        private static Collider2D _bossCollider;
        private static PlayMakerFSM _bossFsm;
        private static ushort _bossFsmState;
        private static ushort _prevBossFsmState;
        private static float _fsmStateTime;

        /// <summary>
        /// Call once per FixedUpdate. Does nothing outside boss scenes.
        /// </summary>
        public static void Tick()
        {
            if (BossSceneController.Instance == null || HeroController.instance == null)
            {
                _active = false;
                return;
            }

            if (!_active)
            {
                BeginEpisode();
            }

            FrameDataHeader frame = BuildFrame();
            Modding.Logger.LogDebug(Format(frame));
            _frameId++;
        }

        // =====================================================================
        // Episode
        // =====================================================================

        private static void BeginEpisode()
        {
            _active = true;
            _frameId = 0;
            _prevKnightHp = PlayerData.instance.health;
            _invulnRemaining = 0f;
            BindBoss(null);

            Modding.Logger.LogDebug(Format(BuildEpisodeHeader()));
        }

        private static EpisodeFileHeader BuildEpisodeHeader()
        {
            PlayerData pd = PlayerData.instance;
            BossInfo boss = Globals.FindBossByScene(GameManager.instance.GetSceneNameString());

            return new EpisodeFileHeader
            {
                Magic = EpisodeFileHeader.ExpectedMagic,
                BossId = boss != null ? boss.Id : Globals.UnknownBossId,
                BossDifficulty = (byte)BossSceneController.Instance.BossLevel,
                NailDamage = (byte)pd.nailDamage,
                MaxHealth = (byte)pd.maxHealth,
                Reserved = 0
            };
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
            PlayMakerFSM[] fsms = boss.GetComponents<PlayMakerFSM>();
            return fsms.FirstOrDefault(fsm => fsm.FsmName == "Control") ?? fsms.FirstOrDefault();
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

            var frame = new FrameDataHeader { FrameId = _frameId, EntityCount = 0 };

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

        private static void FillKnight(ref FrameDataHeader f, HeroController hc, PlayerData pd)
        {
            Vector2 position = hc.transform.position;
            Vector2 velocity = hc.GetComponent<Rigidbody2D>().velocity;
            float nailCooldown = ReflectionHelper.GetField<HeroController, float>(hc, "attack_cooldown");
            float dashCooldown = ReflectionHelper.GetField<HeroController, float>(hc, "dashCooldownTimer");

            f.KnightX = position.x;
            f.KnightY = position.y;
            f.KnightVx = velocity.x;
            f.KnightVy = velocity.y;
            f.KnightHp = (byte)pd.health;
            f.KnightMp = (byte)pd.MPCharge;
            f.KnightMpReserve = (byte)(pd.MPReserve / 33);
            f.KnightFlags = ReadKnightFlags(hc, pd, nailCooldown, dashCooldown);
            f.NailCooldown = nailCooldown;
            f.DashCooldown = dashCooldown;
            f.InvulnRemaining = _invulnRemaining;
            f.FocusProgress = 0f; // TODO placeholder
        }

        private static KnightFlags ReadKnightFlags(HeroController hc, PlayerData pd, float nailCooldown, float dashCooldown)
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
            if (dashCooldown <= 0f)                    flags |= KnightFlags.CanDash;
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

        private static ushort StateId(string stateName) => (ushort)Animator.StringToHash(stateName);

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
            $"nail={h.NailDamage} maxHp={h.MaxHealth}";

        private static string Format(FrameDataHeader f) =>
            $"[Telemetry] F={f.FrameId} status={f.IsDone} " +
            $"K(pos={f.KnightX:F2},{f.KnightY:F2} vel={f.KnightVx:F2},{f.KnightVy:F2} " +
            $"hp={f.KnightHp} mp={f.KnightMp} res={f.KnightMpReserve} " +
            $"nailCd={f.NailCooldown:F2} dashCd={f.DashCooldown:F2} invuln={f.InvulnRemaining:F2} focus={f.FocusProgress:F2} " +
            $"flags={f.KnightFlags}) " +
            $"B(pos={f.BossX:F2},{f.BossY:F2} vel={f.BossVx:F2},{f.BossVy:F2} " +
            $"bounds={f.BossBoundWidth:F2}x{f.BossBoundHeight:F2} hp={f.BossHp} " +
            $"fsm={f.BossFsmState} prev={f.PrevFsmState} t={f.FsmStateTime:F2}) " +
            $"frame={f.Flags} entities={f.EntityCount} " +
            $"in(pressed={f.ActionPressed} held={f.ActionHeld})";
    }
}
