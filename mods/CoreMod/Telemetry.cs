using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace CoreMod
{
    /// <summary>
    /// Common combat charms bitmask (4 bytes) - recorded once in EpisodeFileHeader.
    /// </summary>
    [Flags]
    public enum CharmFlags : uint
    {
        None                = 0,
        WaywardCompass      = 1 << 0,
        GatheringSwarm      = 1 << 1,
        StalwartShell       = 1 << 2,
        SoulCatcher         = 1 << 3,
        ShamanStone         = 1 << 4,  // High priority: spell damage & size
        SoulEater           = 1 << 5,
        Dashmaster          = 1 << 6,  // Downward dash & dash cooldown reduction
        Sprintmaster        = 1 << 7,
        Grubsong            = 1 << 8,
        SpellTwister        = 1 << 9,  // Reduced MP spell cost
        SteadyBody          = 1 << 10, // No attack knockback
        HeavyBlow           = 1 << 11,
        QuickSlash          = 1 << 12, // High priority: faster nail swing
        Longnail            = 1 << 13, // +15% nail reach
        MarkOfPride         = 1 << 14, // High priority: +25% nail reach
        FuryOfTheFallen     = 1 << 15,
        ThornsOfAgony       = 1 << 16,
        BaldursShell        = 1 << 17,
        Flukenest           = 1 << 18,
        DefendersCrest      = 1 << 19,
        ShapeOfUnn          = 1 << 20, // Slug movement during heal
        QuickFocus          = 1 << 21, // Faster heal time
        DeepFocus           = 1 << 22,
        NailmastersGlory    = 1 << 23, // 0.75s nail charge time
        FragileHeart        = 1 << 24,
        FragileStrength     = 1 << 25, // 1.5x nail damage
        DreamWielder        = 1 << 26,
        SharpShadow         = 1 << 27, // Longer dash + dash damage
        UnbreakableStrength = 1 << 28
    }

    /// <summary>
    /// Physical controller action buttons (1 byte).
    /// </summary>
    [Flags]
    public enum ActionButtons : byte
    {
        None        = 0,
        Jump        = 1 << 0,
        Attack      = 1 << 1, // Hold to charge; release to unleash Nail Art
        Dash        = 1 << 2,
        CastFocus   = 1 << 3,
        SuperDash   = 1 << 4,
        DreamNail   = 1 << 5,
        QuickCast   = 1 << 6
    }

    /// <summary>
    /// Knight combat, movement, and recovery flags (2 bytes).
    /// </summary>
    [Flags]
    public enum KnightFlags : ushort
    {
        None           = 0,
        OnGround       = 1 << 0,
        TouchingWall   = 1 << 1,
        WallSliding    = 1 << 2,
        IsDashing      = 1 << 3,
        IsInvulnerable = 1 << 4,
        CanDoubleJump  = 1 << 5,
        CanDash        = 1 << 6,
        CanAttack      = 1 << 7,  // True if nail cooldown == 0 (can swing)
        IsFocusing     = 1 << 8,  // True if channeling heal (immobilized)
        IsRecoiling    = 1 << 9,  // True if in hitstun / pogo bounce
        NailCharged    = 1 << 10, // True if nail art is ready to release
        IsAttacking    = 1 << 11  // True during active nail swing frames
    }

    public enum EntityType : byte
    {
        Unknown       = 0,
        Projectile    = 1, // Needle, fireball, spit
        Hazard        = 2, // Floor spikes, falling rocks (False Knight)
        Minion        = 3, // Summoned adds / flies
        Shockwave     = 4, // Ground shockwaves
        SecondaryBoss = 5  // 2nd Mantis Sister (Mantis Lords Phase 2)
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
        /// Packs boss/knight facings, boss invulnerability, and 2-axis movement into 1 byte.
        /// </summary>
        public static byte Pack(bool bossFacingRight, bool knightFacingRight, bool bossInvulnerable, int moveX, int moveY)
        {
            // moveX and moveY are clamped to -1..1 and mapped to 0..2 (2 bits)
            int mx = (Math.Max(-1, Math.Min(1, moveX)) + 1) & 0x03;
            int my = (Math.Max(-1, Math.Min(1, moveY)) + 1) & 0x03;

            return (byte)(
                (bossFacingRight   ? (1 << 0) : 0) |
                (knightFacingRight ? (1 << 1) : 0) |
                (bossInvulnerable  ? (1 << 2) : 0) |
                (mx << 3) |
                (my << 5)
            );
        }
    }

    // =========================================================================
    // 1. Episode File Header (Written ONCE at file start: 32 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct EpisodeFileHeader
    {
        public ulong Magic;               // 0x3230415441444B48 ("HKDATA02" ASCII little-endian) (8 bytes)
        public byte BossId;               // Boss registry index (1 byte)
        public byte BossDifficulty;       // 0 = Attuned, 1 = Ascended, 2 = Radiant (1 byte)
        public byte NailDamage;           // 5 (Old), 9 (Sharpened), 13 (Channeled), 17 (Coiled), 21 (Pure) (1 byte)
        public byte MaxHealth;            // Max masks (5..9) (1 byte)
        public uint Charms;               // CharmFlags bitmask (4 bytes)
        public float ArenaMinX;           // Left wall coordinate (4 bytes)
        public float ArenaMaxX;           // Right wall coordinate (4 bytes)
        public float ArenaMinY;           // Floor coordinate (4 bytes)
        public float ArenaMaxY;           // Ceiling coordinate (4 bytes)

        public static readonly ulong ExpectedMagic = 0x3230415441444B48; // "HKDATA02"
    }

    // =========================================================================
    // 2. Dynamic Entity Record (Supports multi-boss like Mantis Lords: 32 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct EntityData
    {
        public byte EntityType;           // EntityType enum (1 byte)
        public byte Flags;                // Bit 0: facing_right, Bit 1: invulnerable (1 byte)
        public ushort FsmState;           // For secondary boss (Mantis 2): active FSM state (2 bytes)
        public short EntityId;            // Unique instance ID (2 bytes)
        public short Hp;                  // Current HP for secondary boss / breakable entity (2 bytes)

        // Relative coordinates to Knight: (entity - knight)
        public float RelX;                // (4 bytes)
        public float RelY;                // (4 bytes)
        public float RelVx;               // (4 bytes)
        public float RelVy;               // (4 bytes)

        // Collision extents (half-width & half-height)
        public float BoundWidth;          // (4 bytes)
        public float BoundHeight;         // (4 bytes)
    }

    // =========================================================================
    // 3. Fixed Frame Header (Every 20ms tick: 72 bytes)
    // =========================================================================
    [StructLayout(LayoutKind.Sequential, Pack = 1)]
    public struct FrameDataHeader
    {
        // --- Step Metadata (8 bytes) ---
        public uint FrameId;              // timestamp = frame_id * 0.02s (4 bytes)
        public byte IsDone;               // EpisodeStatus enum (1 byte)
        public byte EntityCount;          // Number of EntityData structs following this header (1 byte)
        public byte Directions;           // Packed via DirectionPacking.Pack(...) (1 byte)
        public byte Pad0;                 // Alignment padding (1 byte)

        // --- Knight Kinematics & Resources (28 bytes) ---
        public float KnightX;             // Absolute arena position X (4 bytes)
        public float KnightY;             // Absolute arena position Y (4 bytes)
        public float KnightVx;            // Velocity X (4 bytes)
        public float KnightVy;            // Velocity Y (4 bytes)
        public short KnightHp;            // Current HP (0..9) (2 bytes)
        public short KnightMp;            // Current MP / Soul (0..99) (2 bytes)
        public short KnightMpReserve;     // Reserve soul vessels (2 bytes)
        public ushort KnightFsmState;     // Hash/ID of current Knight animation/state (2 bytes)
        public ushort KnightFlags;        // KnightFlags bitmask (2 bytes)
        public ushort Pad1;               // Alignment padding (2 bytes)

        // --- Boss Kinematics & Health (24 bytes) ---
        public float BossX;               // Absolute arena position X (4 bytes)
        public float BossY;               // Absolute arena position Y (4 bytes)
        public float BossVx;              // Velocity X (4 bytes)
        public float BossVy;              // Velocity Y (4 bytes)
        public int BossHp;                // Current Boss HP (4 bytes)
        public ushort BossFsmState;       // Hash/ID of active Boss FSM state (2 bytes)
        public ushort Pad2;               // Alignment padding (2 bytes)

        // --- RL Step Signals & Inputs (12 bytes) ---
        public short DamageDealtToBoss;   // HP lost by boss this tick (2 bytes)
        public short DamageTakenByKnight; // HP lost by knight this tick (2 bytes)
        public float StepReward;          // Precomputed scalar reward (4 bytes)
        public byte ActionPressed;        // ActionButtons bitmask (newly pressed) (1 byte)
        public byte ActionHeld;           // ActionButtons bitmask (held down) (1 byte)
        public ushort Pad3;               // Alignment padding (2 bytes)
    }

    public static class TelemetryValidation
    {
        [Conditional("DEBUG")]
        public static void AssertSizes()
        {
            int episodeSize = Marshal.SizeOf(typeof(EpisodeFileHeader));
            int entitySize  = Marshal.SizeOf(typeof(EntityData));
            int frameSize   = Marshal.SizeOf(typeof(FrameDataHeader));

            if (episodeSize != 32)
                throw new InvalidOperationException($"EpisodeFileHeader must be 32 bytes, was {episodeSize}");
            if (entitySize != 32)
                throw new InvalidOperationException($"EntityData must be 32 bytes, was {entitySize}");
            if (frameSize != 72)
                throw new InvalidOperationException($"FrameDataHeader must be 72 bytes, was {frameSize}");
        }
    }
}
