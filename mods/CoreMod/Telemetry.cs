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

    public static class DirectionPacking
    {
        /// <summary>
        /// Packs boss/knight facings and boss invulnerability into 1 byte.
        /// </summary>
        public static byte Pack(bool bossFacingRight, bool knightFacingRight, bool bossInvulnerable)
        {
            return (byte)(
                (bossFacingRight   ? (1 << 0) : 0) |
                (knightFacingRight ? (1 << 1) : 0) |
                (bossInvulnerable  ? (1 << 2) : 0)
            );
        }
    }

    // =========================================================================
    // 1. Episode File Header (Written ONCE at file start: 32 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct EpisodeFileHeader
    {
        public ulong Magic;               // 0x3330415441444B48 ("HKDATA03" ASCII little-endian) (8 bytes)
        public byte BossId;               // Boss registry index (1 byte)
        public byte BossDifficulty;       // 0 = Attuned, 1 = Ascended, 2 = Radiant (1 byte)
        public byte NailDamage;           // 5 (Old), 9 (Sharpened), 13 (Channeled), 17 (Coiled), 21 (Pure) (1 byte)
        public byte MaxHealth;            // Max masks (5..9) (1 byte)
        public float ArenaMinX;           // Left wall coordinate (4 bytes)
        public float ArenaMaxX;           // Right wall coordinate (4 bytes)
        public float ArenaMinY;           // Floor coordinate (4 bytes)
        public float ArenaMaxY;           // Ceiling coordinate (4 bytes)

        public static readonly ulong ExpectedMagic = 0x3330415441444B48; // "HKDATA03"
    }

    // =========================================================================
    // 2. Dynamic Entity Record (30 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct EntityData
    {
        public byte Kind;                 // EntityType enum (1 byte)
        public byte Flags;                // Bit 0: facing_right, Bit 1: invulnerable, Bit 2: damages_knight (1 byte)
        public short EntityId;            // Unique instance ID (2 bytes)
        public short Hp;                  // Current HP for secondary boss / breakable entity (2 bytes)

        // Absolute arena coordinates
        public float X;                   // (4 bytes)
        public float Y;                   // (4 bytes)
        public float Vx;                  // (4 bytes)
        public float Vy;                  // (4 bytes)

        // Collision extents (half-width & half-height)
        public float BoundWidth;          // (4 bytes)
        public float BoundHeight;         // (4 bytes)
    }

    // =========================================================================
    // 3. Fixed Frame Header (Every 20ms tick: 87 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct FrameDataHeader
    {
        // --- Step Metadata (7 bytes) ---
        public uint FrameId;              // timestamp = frame_id * 0.02s (4 bytes)
        public byte IsDone;               // EpisodeStatus enum (1 byte)
        public byte EntityCount;          // Number of EntityData structs following this header (1 byte)
        public byte Directions;           // Packed via DirectionPacking.Pack(...) (1 byte)

        // --- Knight Kinematics & Resources (40 bytes) ---
        public float KnightX;             // Absolute arena position X (4 bytes)
        public float KnightY;             // Absolute arena position Y (4 bytes)
        public float KnightVx;            // Velocity X (4 bytes)
        public float KnightVy;            // Velocity Y (4 bytes)
        public short KnightHp;            // Current HP (0..9) (2 bytes)
        public short KnightMp;            // Current MP / Soul (0..99) (2 bytes)
        public short KnightMpReserve;     // Reserve soul vessels (2 bytes)
        public ushort KnightFlags;        // KnightFlags bitmask (2 bytes)
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
        public ushort BossFsmState;       // Hash/ID of active Boss FSM state (2 bytes)
        public float FsmStateTime;        // Seconds spent in the active FSM state (4 bytes)
        public ushort PrevFsmState;       // Hash/ID of the previous Boss FSM state (2 bytes)
        public float BossBoundWidth;      // Collision half-width (4 bytes)
        public float BossBoundHeight;     // Collision half-height (4 bytes)

        // --- RL Step Signals & Inputs (4 bytes) ---
        public byte BossHit;              // 1 if boss lost HP this tick (1 byte)
        public byte KnightHit;            // 1 if knight lost HP this tick (1 byte)
        public byte ActionPressed;        // ActionButtons bitmask (newly pressed) (1 byte)
        public byte ActionHeld;           // ActionButtons bitmask (held down) (1 byte)
    }
}
