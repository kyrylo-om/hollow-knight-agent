using System;
using System.Runtime.InteropServices;

namespace CoreMod
{
    /// <summary>
    /// Physical controller buttons (1 byte).
    /// </summary>
    [Flags]
    public enum ActionButtons : byte
    {
        None      = 0,
        Jump      = 1 << 0,
        Attack    = 1 << 1,
        Dash      = 1 << 2,
        CastFocus = 1 << 3, // Tap to cast (with Up/Down for other spells); hold to focus
        Left      = 1 << 4,
        Right     = 1 << 5,
        Up        = 1 << 6,
        Down      = 1 << 7
    }

    /// <summary>
    /// Knight combat, movement, and recovery flags (2 bytes).
    /// </summary>
    [Flags]
    public enum KnightFlags : ushort
    {
        None            = 0,
        OnGround        = 1 << 0,
        TouchingWall    = 1 << 1,
        WallSliding     = 1 << 2,
        IsDashing       = 1 << 3,
        IsInvulnerable  = 1 << 4,
        CanDoubleJump   = 1 << 5,
        CanDash         = 1 << 6,
        CanAttack       = 1 << 7,  // True if nail cooldown == 0 (can swing)
        IsFocusing      = 1 << 8,  // True if channeling heal (immobilized)
        IsRecoiling     = 1 << 9,  // True if in hitstun / pogo bounce
        IsAttacking     = 1 << 10, // True during active nail swing frames
        IsCasting       = 1 << 11, // True during spell cast animation
        IsShadowDashing = 1 << 12
    }

    /// <summary>
    /// 1-bit flags packed into a single byte.
    /// Combines directional facings, invulnerability, and per-tick hit signals.
    /// </summary>
    [Flags]
    public enum FrameFlags : byte
    {
        None              = 0,
        BossFacingRight   = 1 << 0,
        KnightFacingRight = 1 << 1,
        BossInvulnerable  = 1 << 2,
        BossHit           = 1 << 3, // True if boss took damage this tick
        KnightHit         = 1 << 4, // True if knight took damage this tick
        // Bits 5..7 reserved for future flags
    }

    public enum EntityType : byte
    {
        Unknown       = 0,
        Projectile    = 1, // Needle, fireball, spit
        Hazard        = 2, // Floor spikes, falling rocks (False Knight)
        Minion        = 3, // Summoned adds / flies
        Shockwave     = 4, // Ground shockwaves
    }

    public enum EpisodeStatus : byte
    {
        InProgress   = 0,
        KnightDied   = 1,
        BossDefeated = 2,
        Aborted      = 3
    }

    public static class FrameFlagsPacking
    {
        public static FrameFlags Pack(
            bool bossFacingRight,
            bool knightFacingRight,
            bool bossInvulnerable,
            bool bossHit,
            bool knightHit)
        {
            FrameFlags flags = FrameFlags.None;
            if (bossFacingRight)   flags |= FrameFlags.BossFacingRight;
            if (knightFacingRight) flags |= FrameFlags.KnightFacingRight;
            if (bossInvulnerable)  flags |= FrameFlags.BossInvulnerable;
            if (bossHit)           flags |= FrameFlags.BossHit;
            if (knightHit)         flags |= FrameFlags.KnightHit;
            return flags;
        }
    }

    // =========================================================================
    // 1. Episode File Header (Written ONCE at file start: 16 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential)]
    public struct EpisodeFileHeader
    {
        // 8-byte field (Offset 0..7)
        public ulong Magic;               // 0x3330415441444B48 ("HKDATA03" ASCII little-endian) (8 bytes)

        // 1-byte fields (Offsets 8..11)
        public byte BossId;               // BossInfo.Id from Globals.Bosses, 0 = unknown (1 byte)
        public byte BossDifficulty;       // 0 = Attuned, 1 = Ascended, 2 = Radiant (1 byte)
        public byte NailDamage;           // 5 (Old), 9 (Sharpened), 13 (Channeled), 17 (Coiled), 21 (Pure) (1 byte)
        public byte MaxHealth;            // Max masks (5..9) (1 byte)

        // Trailing padding field (Offsets 12..15) -> aligns struct to 16 bytes (multiple of 8)
        public int Reserved;              // Alignment padding to 16 bytes (4 bytes)

        public static readonly ulong ExpectedMagic = 0x3330415441444B48; // "HKDATA03"
    }

    // =========================================================================
    // 2. Dynamic Entity Record (32 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential)]
    public struct EntityData
    {
        // 4-byte fields (24 bytes: Offsets 0..23)
        public float X;                   // Arena coordinate X (4 bytes)
        public float Y;                   // Arena coordinate Y (4 bytes)
        public float Vx;                  // Velocity X (4 bytes)
        public float Vy;                  // Velocity Y (4 bytes)
        public float BoundWidth;          // Half-width (4 bytes)
        public float BoundHeight;         // Half-height (4 bytes)

        // 2-byte fields (4 bytes: Offsets 24..27)
        public short EntityId;            // Unique instance ID (2 bytes)
        public short Hp;                  // Current HP for secondary boss / breakable entity (2 bytes)

        // 1-byte fields (2 bytes: Offsets 28..29)
        public EntityType Kind;           // EntityType enum (1 byte)
        public byte Flags;                // Bit 0: facing_right, Bit 1: invulnerable, Bit 2: damages_knight (1 byte)

        // Trailing alignment (2 bytes: Offsets 30..31) -> rounds struct up to 32 bytes
        public ushort Reserved;           // Trailing alignment to 32 bytes (2 bytes)
    }

    // =========================================================================
    // 3. Fixed Frame Header (84 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential)]
    public struct FrameDataHeader
    {
        // --- 4-byte fields (68 bytes: Offsets 0..67) ---
        public uint FrameId;              // timestamp = frame_id * 0.02s (4 bytes)
        public float KnightX;             // Absolute arena position X (4 bytes)
        public float KnightY;             // Absolute arena position Y (4 bytes)
        public float KnightVx;            // Velocity X (4 bytes)
        public float KnightVy;            // Velocity Y (4 bytes)
        public float NailCooldown;        // Seconds until next nail swing (4 bytes)
        public float DashCooldown;        // Seconds until next dash (4 bytes)
        public float InvulnRemaining;     // Seconds of invulnerability left (4 bytes)
        public float FocusProgress;       // Heal channel progress 0..1 (4 bytes)

        // --- Boss Kinematics & Health (36 bytes) ---
        public float BossX;               // Collider center X, not transform origin (4 bytes)
        public float BossY;               // Collider center Y, not transform origin (4 bytes)
        public float BossVx;              // Velocity X (4 bytes)
        public float BossVy;              // Velocity Y (4 bytes)
        public int BossHp;                // Current Boss HP (4 bytes)
        public float FsmStateTime;        // Seconds spent in the active FSM state (4 bytes)
        public float BossBoundWidth;      // Collision half-width (4 bytes)
        public float BossBoundHeight;     // Collision half-height (4 bytes)

        // --- 2-byte fields (6 bytes: Offsets 68..73) ---
        public KnightFlags KnightFlags;   // Bitmask of knight movement/combat state (2 bytes)
        public ushort BossFsmState;       // Hash/ID of active Boss FSM state (2 bytes)
        public ushort PrevFsmState;       // Hash/ID of previous Boss FSM state (2 bytes)

        // --- 1-byte fields (8 bytes: Offsets 74..81) ---
        public byte KnightHp;             // Current HP (0..9) (1 byte)
        public byte KnightMp;             // Current MP / Soul (0..99) (1 byte)
        public byte KnightMpReserve;      // Reserve soul vessels (0..3) (1 byte)
        public EpisodeStatus IsDone;      // Episode status enum (1 byte)
        public byte EntityCount;          // Number of EntityData structs following this header (1 byte)
        public FrameFlags Flags;          // BossHit, KnightHit, Facings, Invulnerability (1 byte)
        public ActionButtons ActionPressed;// Newly pressed buttons bitmask (1 byte)
        public ActionButtons ActionHeld;  // Held down buttons bitmask (1 byte)

        // --- Alignment Padding (2 bytes: Offsets 82..83) ---
        public ushort Reserved;           // Rounds struct to 84 bytes (divisible by 4) (2 bytes)
    }
}
