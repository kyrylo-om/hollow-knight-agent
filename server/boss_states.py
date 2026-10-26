"""Boss FSM state mappings, mirroring BossFsms.cs.

A packed FSM state (FrameDataHeader.boss_fsm_state) is boss_id << 8 | state_id.
State ids run 1..N per boss; 0 = unknown state.
"""

import numpy as np

# boss_id -> state names; state id i is at index i - 1 (ids are noted in comments)
BOSS_FSM_STATES: dict[int, list[str]] = {
    1: [  # Gruz Mother
        "Sleep",  # 1
        "Init",  # 2
        "Wake",  # 3
        "Fly",  # 4
        "Buzz",  # 5
        "Super Choose",  # 6
        "Charge Antic",  # 7
        "Charge",  # 8
        "Charge Recover L",  # 9
        "Super End",  # 10
        "Recover End",  # 11
        "Charge Recover D",  # 12
        "Charge Recover R",  # 13
        "Charge Recover U",  # 14
        "Slam Antic",  # 15
        "Check Direction",  # 16
        "Go Left",  # 17
        "Go Right",  # 18
        "Launch Up",  # 19
        "Flying",  # 20
        "Turn Left",  # 21
        "Launch Down",  # 22
        "Turn Right",  # 23
        "Slam Down",  # 24
        "Slam Up",  # 25
        "Slam End",  # 26
        "Invincible",  # 27
        "GG Boss Wake",  # 28
        "Wake Sound",  # 29
        "GG Extra Pause",  # 30
    ],
    2: [  # Vengefly King
        "Init",  # 1
        "Intro Roar Antic",  # 2
        "Intro Roar Left",  # 3
        "Idle",  # 4
        "Lurk",  # 5
        "Choose Attack",  # 6
        "Swoop Antic",  # 7
        "Swoop L",  # 8
        "Swoop Direction",  # 9
        "Swoop R",  # 10
        "Swoop Rise",  # 11
        "Summon Antic",  # 12
        "Check Dir",  # 13
        "Roar Left",  # 14
        "Roar Right",  # 15
        "Summon",  # 16
        "Roar End",  # 17
        "Swoop In",  # 18
        "Col Music",  # 19
        "Set GG",  # 20
        "Title?",  # 21
        "GG Summon",  # 22
        "Check Dir 2",  # 23
        "Intro Roar Right",  # 24
        "Check Summon",  # 25
        "Check Summon GG",  # 26
        "Wait Frame",  # 27
    ],
    3: [  # Brooding Mawlek
        "Init",  # 1
        "Dormant",  # 2
        "Wake",  # 3
        "Wake Jump",  # 4
        "Wake In Air",  # 5
        "Wake Land",  # 6
        "Wake Roar",  # 7
        "Start",  # 8
        "Roar End",  # 9
        "Idle",  # 10
        "Super Ready",  # 11
        "Super Select",  # 12
        "Super Spit",  # 13
        "Shoot",  # 14
        "Detect Hero Pos",  # 15
        "L",  # 16
        "R",  # 17
        "Super Cooldown",  # 18
        "Super Jump",  # 19
        "Detect Hero Pos 2",  # 20
        "L 2",  # 21
        "R 2",  # 22
        "Detect Hero Pos 3",  # 23
        "L 3",  # 24
        "R 3",  # 25
        "In Air",  # 26
        "Land",  # 27
        "Jump",  # 28
        "L 4",  # 29
        "R 4",  # 30
        "In Air 2",  # 31
        "Land 2",  # 32
        "Jump 2",  # 33
        "Repeat Check",  # 34
        "Pause",  # 35
        "Set Repeater",  # 36
        "Music",  # 37
        "Aim Return",  # 38
        "GG Wake",  # 39
        "Title",  # 40
    ],
    4: [  # False Knight
        "Init",  # 1
        "Idle",  # 2
        "Turn R",  # 3
        "Turn L",  # 4
        "Move Choice",  # 5
        "Jump Antic",  # 6
        "Jump",  # 7
        "Fall",  # 8
        "Land",  # 9
        "Determine Jump",  # 10
        "Random",  # 11
        "Towards",  # 12
        "Random Left",  # 13
        "Random Right",  # 14
        "JA Antic",  # 15
        "JA Check Hero Pos",  # 16
        "JA Right",  # 17
        "JA Left",  # 18
        "JA Jump",  # 19
        "JA Hit",  # 20
        "JA Recoil",  # 21
        "JA Recoil 2",  # 22
        "JA End",  # 23
        "Rise",  # 24
        "JA Rise",  # 25
        "JA Fall",  # 26
        "S Check Hero Pos",  # 27
        "S Right",  # 28
        "S Left",  # 29
        "S Antic",  # 30
        "S Jump",  # 31
        "S Rise",  # 32
        "S Fall",  # 33
        "S Land",  # 34
        "S Attack Antic",  # 35
        "S Attack",  # 36
        "S Attack Recover",  # 37
        "Run Antic",  # 38
        "Run",  # 39
        "State 1",  # 40
        "Stun Start",  # 41
        "Check Direction",  # 42
        "Stun Turn L",  # 43
        "Stun Turn R",  # 44
        "Stun In Air",  # 45
        "Stun Land",  # 46
        "Roll End",  # 47
        "Open Uuup",  # 48
        "Recover",  # 49
        "Idle Pause",  # 50
        "Rage Jump Antic",  # 51
        "Jump 2",  # 52
        "Rise 2",  # 53
        "Fall 2",  # 54
        "State 2",  # 55
        "R Attack Antic",  # 56
        "Rage",  # 57
        "Turn",  # 58
        "Dormant",  # 59
        "Opened",  # 60
        "Hit",  # 61
        "Rage End",  # 62
        "Rage Begin",  # 63
        "Slam",  # 64
        "Rage Slam",  # 65
        "Rage Check",  # 66
        "Floor Crack",  # 67
        "Floor Crack?",  # 68
        "Anim End",  # 69
        "Stun Fail",  # 70
        "JA Jump 2",  # 71
        "JA Hit 2",  # 72
        "JA Rise 2",  # 73
        "JA Fall 2",  # 74
        "JA Antic 2",  # 75
        "Floor Break",  # 76
        "Death Land",  # 77
        "JA Slam",  # 78
        "Death Open",  # 79
        "Opened 2",  # 80
        "Hit 2",  # 81
        "Death Anim Start",  # 82
        "Steam",  # 83
        "Blow",  # 84
        "Ready",  # 85
        "Death Head Land",  # 86
        "Cough",  # 87
        "Start Fall",  # 88
        "Rubble End",  # 89
        "First Idle",  # 90
        "Check",  # 91
        "Decrement Battle Enemies",  # 92
        "Land Noise",  # 93
        "Music",  # 94
        "Row Check",  # 95
        "Voice?",  # 96
        "Voice? 2",  # 97
        "To Phase 2",  # 98
        "To Phase 3",  # 99
        "Particle Pause",  # 100
        "Particle End",  # 101
        "Walls Check",  # 102
        "Random R",  # 103
        "Random L",  # 104
        "Walls Check 2",  # 105
        "Check Jump Dir",  # 106
        "Raycast L",  # 107
        "Raycast R",  # 108
        "Pause Short",  # 109
        "Pause Long",  # 110
        "Open Map Shop and Journal",  # 111
        "Esc Jump Antic",  # 112
        "Esc Jump",  # 113
        "Esc Rise",  # 114
        "Esc Fall",  # 115
        "Esc Land",  # 116
        "Escaped Idle",  # 117
        "Beta End Event",  # 118
        "Barrels?",  # 119
        "Head Reset",  # 120
        "Head Frame",  # 121
        "Check If GG",  # 122
        "Boss Death Sting",  # 123
        "Set Head Facing",  # 124
        "Chinese?",  # 125
        "Death Head Land Chinese",  # 126
        "State 3",  # 127
    ],
    5: [  # Failed Champion
        "Init",  # 1
        "Idle",  # 2
        "Turn R",  # 3
        "Turn L",  # 4
        "Move Choice",  # 5
        "Jump Antic",  # 6
        "Jump",  # 7
        "Fall",  # 8
        "Land",  # 9
        "Determine Jump",  # 10
        "Random",  # 11
        "Towards",  # 12
        "Random Left",  # 13
        "Random Right",  # 14
        "JA Antic",  # 15
        "JA Check Hero Pos",  # 16
        "JA Right",  # 17
        "JA Left",  # 18
        "JA Jump",  # 19
        "JA Hit",  # 20
        "JA Recoil",  # 21
        "JA Recoil 2",  # 22
        "JA End",  # 23
        "Rise",  # 24
        "JA Rise",  # 25
        "JA Fall",  # 26
        "S Check Hero Pos",  # 27
        "S Right",  # 28
        "S Left",  # 29
        "S Antic",  # 30
        "S Jump",  # 31
        "S Rise",  # 32
        "S Fall",  # 33
        "S Land",  # 34
        "S Attack Antic",  # 35
        "S Attack",  # 36
        "S Attack Recover",  # 37
        "Run Antic",  # 38
        "Run",  # 39
        "State 1",  # 40
        "Stun Start",  # 41
        "Check Direction",  # 42
        "Stun Turn L",  # 43
        "Stun Turn R",  # 44
        "Stun In Air",  # 45
        "Stun Land",  # 46
        "Roll End",  # 47
        "Open Uuup",  # 48
        "Recover",  # 49
        "Idle Pause",  # 50
        "Rage Jump Antic",  # 51
        "Jump 2",  # 52
        "Rise 2",  # 53
        "Fall 2",  # 54
        "State 2",  # 55
        "R Attack Antic",  # 56
        "Rage",  # 57
        "Turn",  # 58
        "Dormant",  # 59
        "Opened",  # 60
        "Hit",  # 61
        "Rage End",  # 62
        "Rage Begin",  # 63
        "Slam",  # 64
        "Rage Slam",  # 65
        "Rage Check",  # 66
        "Floor Crack",  # 67
        "Floor Crack?",  # 68
        "Anim End",  # 69
        "Stun Fail",  # 70
        "JA Jump 2",  # 71
        "JA Hit 2",  # 72
        "JA Rise 2",  # 73
        "JA Fall 2",  # 74
        "JA Antic 2",  # 75
        "Floor Break",  # 76
        "Death Land",  # 77
        "JA Slam",  # 78
        "Death Open",  # 79
        "Opened 2",  # 80
        "Hit 2",  # 81
        "Death Anim Start",  # 82
        "Steam",  # 83
        "Blow",  # 84
        "Ready",  # 85
        "Death Head Land",  # 86
        "Cough",  # 87
        "Start Fall",  # 88
        "Rubble End",  # 89
        "First Idle",  # 90
        "Check",  # 91
        "Decrement Battle Enemies",  # 92
        "Land Noise",  # 93
        "Steam 2",  # 94
        "Init 2",  # 95
        "Music",  # 96
        "Row Check",  # 97
        "Voice?",  # 98
        "Voice? 2",  # 99
        "To Phase 2",  # 100
        "To Phase 3",  # 101
        "Particle Pause",  # 102
        "Particle End",  # 103
        "Walls Check",  # 104
        "Random R",  # 105
        "Random L",  # 106
        "Walls Check 2",  # 107
        "Check Jump Dir",  # 108
        "Raycast L",  # 109
        "Raycast R",  # 110
        "Pause Short",  # 111
        "Pause Long",  # 112
        "Set PlayerData",  # 113
        "Wait for Hero",  # 114
        "Check GG",  # 115
        "Dream Return",  # 116
        "Set Head Facing",  # 117
    ],
    6: [  # Hornet Protector
        "Init",  # 1
        "Idle",  # 2
        "GDash Antic",  # 3
        "G Dash",  # 4
        "GDash Recover1",  # 5
        "GDash Recover2",  # 6
        "Pause",  # 7
        "Jump Antic",  # 8
        "Aim Jump",  # 9
        "Jump",  # 10
        "In Air",  # 11
        "Land",  # 12
        "Re Aim",  # 13
        "Set ADash",  # 14
        "ADash Antic",  # 15
        "A Dash",  # 16
        "Land Y",  # 17
        "Fire",  # 18
        "Firing R",  # 19
        "Firing L",  # 20
        "Hit Roof",  # 21
        "Wall L",  # 22
        "Jump R",  # 23
        "Wall R",  # 24
        "Jump L",  # 25
        "Sphere Antic G",  # 26
        "Sphere",  # 27
        "Sphere Recover",  # 28
        "Set Jump Only",  # 29
        "Set Sphere A",  # 30
        "Sphere Antic A",  # 31
        "Sphere A",  # 32
        "Sphere Recover A",  # 33
        "Sphere A End",  # 34
        "Aim Sphere Jump",  # 35
        "Throw Antic",  # 36
        "Throw",  # 37
        "Thrown",  # 38
        "Throw Recover",  # 39
        "Lock?",  # 40
        "Lock L",  # 41
        "Lock R",  # 42
        "Lock UL",  # 43
        "Lock UR",  # 44
        "Flip?",  # 45
        "Run",  # 46
        "Move Choice A",  # 47
        "Hard Land",  # 48
        "G Sphere?",  # 49
        "Can Throw?",  # 50
        "Move Choice B",  # 51
        "Evade Antic",  # 52
        "Evade",  # 53
        "Dmg Response",  # 54
        "Dmg Idle",  # 55
        "Run Away?",  # 56
        "Evade Land",  # 57
        "After Evade",  # 58
        "Stun Start",  # 59
        "Stun Air",  # 60
        "Stun Land",  # 61
        "Stun Recover",  # 62
        "Inert",  # 63
        "Wake",  # 64
        "Do Sphere?",  # 65
        "Refight Ready",  # 66
        "Refight Wake",  # 67
        "Escalation",  # 68
        "Flourish",  # 69
        "Run Antic",  # 70
        "Set Scale",  # 71
        "Music",  # 72
        "GG Music",  # 73
        "GG Intro 1",  # 74
        "GG Fall",  # 75
        "GG Land",  # 76
        "GG Reset",  # 77
    ],
    7: [  # Hornet Sentinel
        "Init",  # 1
        "Idle",  # 2
        "GDash Antic",  # 3
        "G Dash",  # 4
        "GDash Recover1",  # 5
        "GDash Recover2",  # 6
        "Pause",  # 7
        "Jump Antic",  # 8
        "Aim Jump",  # 9
        "Jump",  # 10
        "In Air",  # 11
        "Land",  # 12
        "Re Aim",  # 13
        "Set ADash",  # 14
        "ADash Antic",  # 15
        "A Dash",  # 16
        "Land Y",  # 17
        "Fire",  # 18
        "Firing R",  # 19
        "Firing L",  # 20
        "Hit Roof",  # 21
        "Wall L",  # 22
        "Jump R",  # 23
        "Wall R",  # 24
        "Jump L",  # 25
        "Sphere Antic G",  # 26
        "Sphere",  # 27
        "Sphere Recover",  # 28
        "Set Jump Only",  # 29
        "Set Sphere A",  # 30
        "Sphere Antic A",  # 31
        "Sphere A",  # 32
        "Sphere Recover A",  # 33
        "Sphere A End",  # 34
        "Aim Sphere Jump",  # 35
        "Throw Antic",  # 36
        "Throw",  # 37
        "Thrown",  # 38
        "Throw Recover",  # 39
        "Lock?",  # 40
        "Lock L",  # 41
        "Lock R",  # 42
        "Lock UL",  # 43
        "Lock UR",  # 44
        "Flip?",  # 45
        "Run",  # 46
        "Move Choice A",  # 47
        "Hard Land",  # 48
        "G Sphere?",  # 49
        "Can Throw?",  # 50
        "Move Choice B",  # 51
        "Evade Antic",  # 52
        "Evade",  # 53
        "Dmg Response",  # 54
        "Dmg Idle",  # 55
        "Run Away?",  # 56
        "Evade Land",  # 57
        "After Evade",  # 58
        "Stun Start",  # 59
        "Stun Air",  # 60
        "Stun Land",  # 61
        "Stun Recover",  # 62
        "Inert",  # 63
        "Wake",  # 64
        "Do Sphere?",  # 65
        "Refight Ready",  # 66
        "Refight Wake",  # 67
        "Escalation",  # 68
        "Counter Antic",  # 69
        "Counter Stance",  # 70
        "Counter End",  # 71
        "Ev Or Counter",  # 72
        "CA Antic",  # 73
        "CA 1",  # 74
        "CA 2",  # 75
        "CA Recover",  # 76
        "Barb?",  # 77
        "Barb Antic",  # 78
        "Barb Throw",  # 79
        "Barb Recover",  # 80
        "Flourish",  # 81
        "Flourish?",  # 82
        "GG Pause",  # 83
        "Music",  # 84
        "Music (not GG)",  # 85
    ],
    8: [  # Massive Moss Charger
        "Init",  # 1
        "Hidden",  # 2
        "Emerge Pause",  # 3
        "Left or Right?",  # 4
        "Emerge Right",  # 5
        "Emerge Left",  # 6
        "Emerge",  # 7
        "Charge",  # 8
        "Pause",  # 9
        "Pause 2",  # 10
        "Submerge 1",  # 11
        "Submerge CD",  # 12
        "Hero Beyond?",  # 13
        "Play Range",  # 14
        "Detach",  # 15
        "Submerge 2",  # 16
        "Submerge 3",  # 17
        "Submerge 4",  # 18
        "Hit Right",  # 19
        "Hit Left",  # 20
        "Sleep",  # 21
        "Shake",  # 22
        "Roar",  # 23
        "Roar End",  # 24
        "Attack Choice",  # 25
        "Leap Start",  # 26
        "Leap Launch",  # 27
        "In Air",  # 28
        "Land",  # 29
        "Start Pause",  # 30
        "Dormant",  # 31
        "GG Pause",  # 32
        "Title?",  # 33
        "Music",  # 34
        "Music 2",  # 35
    ],
    9: [  # Flukemarm
        "Init",  # 1
        "Idle",  # 2
        "Rage",  # 3
        "Dead",  # 4
        "Check Spawn",  # 5
        "Select Point",  # 6
        "Spawn",  # 7
        "Play Idle",  # 8
        "Roar Start",  # 9
        "Roar End",  # 10
        "Select Point 2",  # 11
        "Spawn 2",  # 12
        "Repick",  # 13
        "Spawn 2 Cancel",  # 14
        "Spawn 1 Cancel",  # 15
        "GG?",  # 16
        "Delay Roar",  # 17
    ],
    10: [  # Mantis Lords
        "Init",  # 1
        "Idle",  # 2
        "Dash Dir",  # 3
        "Dash R",  # 4
        "Dash L",  # 5
        "Dash Arrive",  # 6
        "Dash Antic",  # 7
        "Dash Attack",  # 8
        "End R",  # 9
        "End L",  # 10
        "Dash Recover",  # 11
        "Dash Leave",  # 12
        "Away",  # 13
        "Sleep",  # 14
        "Pause",  # 15
        "Dash Hit Off",  # 16
        "Dstab Pos",  # 17
        "Dstab Arrive",  # 18
        "Dstab Attack",  # 19
        "Dstab Land",  # 20
        "Dstab Leave",  # 21
        "Shift?",  # 22
        "Throw Pos",  # 23
        "Throw R",  # 24
        "Throw L",  # 25
        "Throw Antic",  # 26
        "Set Throws",  # 27
        "Throw",  # 28
        "Throw CD",  # 29
        "Keep Throwing?",  # 30
        "Wall Leave 1",  # 31
        "Wall Leave 2",  # 32
        "Arrive",  # 33
        "Start Pause",  # 34
        "Attack Choice",  # 35
        "Sub Idle",  # 36
        "S Throw R",  # 37
        "S Throw L",  # 38
        "Throw Antic 2",  # 39
        "Set Throws 2",  # 40
        "Throw 2",  # 41
        "Throw CD 2",  # 42
        "Keep Throwing? 2",  # 43
        "Arrive 2",  # 44
        "Throw Pos 2",  # 45
        "Arrive Pause",  # 46
        "Leave Pause",  # 47
        "Throw UD?",  # 48
        "Pos UD",  # 49
        "Pos DU",  # 50
        "After Throw Pause",  # 51
        "Wide Throw L",  # 52
        "Wide Throw R",  # 53
        "Narrow Throw L",  # 54
        "Narrow Throw R",  # 55
        "High Check LR",  # 56
        "Shift Y?",  # 57
        "Short GG",  # 58
        "Short GG 2",  # 59
    ],
    11: [  # Sisters of Battle
        "Init",  # 1
        "Idle",  # 2
        "Dash Dir",  # 3
        "Dash R",  # 4
        "Dash L",  # 5
        "Dash Arrive",  # 6
        "Dash Antic",  # 7
        "Dash Attack",  # 8
        "End R",  # 9
        "End L",  # 10
        "Dash Recover",  # 11
        "Dash Leave",  # 12
        "Away",  # 13
        "Sleep",  # 14
        "Pause",  # 15
        "Dash Hit Off",  # 16
        "Dstab Pos",  # 17
        "Dstab Arrive",  # 18
        "Dstab Attack",  # 19
        "Dstab Land",  # 20
        "Dstab Leave",  # 21
        "Shift?",  # 22
        "Throw Pos",  # 23
        "Throw R",  # 24
        "Throw L",  # 25
        "Throw Antic",  # 26
        "Set Throws",  # 27
        "Throw",  # 28
        "Throw CD",  # 29
        "Keep Throwing?",  # 30
        "Wall Leave 1",  # 31
        "Wall Leave 2",  # 32
        "Arrive",  # 33
        "Start Pause",  # 34
        "Attack Choice",  # 35
        "Sub Idle",  # 36
        "S Throw R",  # 37
        "S Throw L",  # 38
        "Throw Antic 2",  # 39
        "Set Throws 2",  # 40
        "Throw 2",  # 41
        "Throw CD 2",  # 42
        "Keep Throwing? 2",  # 43
        "Arrive 2",  # 44
        "Throw Pos 2",  # 45
        "Arrive Pause",  # 46
        "Leave Pause",  # 47
        "Throw UD?",  # 48
        "Pos UD",  # 49
        "Pos DU",  # 50
        "After Throw Pause",  # 51
        "Wide Throw L",  # 52
        "Wide Throw R",  # 53
        "Narrow Throw L",  # 54
        "Narrow Throw R",  # 55
        "High Check LR",  # 56
        "Shift Y?",  # 57
        "Short GG",  # 58
        "Short GG 2",  # 59
    ],
    12: [  # Oblobbles
        "Wait",  # 1
        "Attack Antic",  # 2
        "Attack",  # 3
        "CD",  # 4
        "Attack Antic 2",  # 5
        "Sleep",  # 6
        "Attack 2",  # 7
        "Attack Check",  # 8
        "Init",  # 9
        "Shoot Anim",  # 10
        "Rage Wait",  # 11
        "R Antic",  # 12
        "Raging",  # 13
    ],
    13: [  # Hive Knight
        "Init",  # 1
        "Sleep",  # 2
        "Wake",  # 3
        "Idle",  # 4
        "Stun Start",  # 5
        "Stun Air",  # 6
        "Stun Land",  # 7
        "Stun Recover",  # 8
        "Dash Antic",  # 9
        "Dash",  # 10
        "Dash Recover",  # 11
        "Dash End",  # 12
        "Jump Antic",  # 13
        "Aim Jump",  # 14
        "Jump",  # 15
        "In Air",  # 16
        "Land",  # 17
        "TeleOut 1",  # 18
        "TeleOut 2",  # 19
        "Tele Pos",  # 20
        "Aim R",  # 21
        "Aim L",  # 22
        "TeleIn 1",  # 23
        "TeleIn 2",  # 24
        "Slash 1",  # 25
        "Slash 2",  # 26
        "Slash Recover",  # 27
        "Start Fall",  # 28
        "Attack Choice",  # 29
        "Glob Antic 1",  # 30
        "Glob Strike",  # 31
        "Glob Recover",  # 32
        "Glob Antic 2",  # 33
        "Bee Roar Antic",  # 34
        "Roar",  # 35
        "Roar Recover",  # 36
        "Phase Check",  # 37
        "Phase 1",  # 38
        "Phase 2",  # 39
        "Phase 3",  # 40
        "Fall",  # 41
        "Intro Land",  # 42
        "Intro",  # 43
        "Intro End",  # 44
        "Activate",  # 45
        "Roar Cooldown",  # 46
        "Tele Pause",  # 47
        "Music",  # 48
        "Variant",  # 49
    ],
    14: [  # Broken Vessel
        "Init",  # 1
        "Pause",  # 2
        "Sleep",  # 3
        "Start Pause",  # 4
        "Rumble Start",  # 5
        "Spawning 1",  # 6
        "Spawning 2",  # 7
        "Spawning 3",  # 8
        "Spawning 4",  # 9
        "Check Final",  # 10
        "Check",  # 11
        "Stop Spawning",  # 12
        "Roar Start",  # 13
        "Roar",  # 14
        "Roar End",  # 15
        "Idle",  # 16
        "Set Dstab",  # 17
        "Jump",  # 18
        "In Air",  # 19
        "Jump Antic",  # 20
        "Land",  # 21
        "Aim Jump",  # 22
        "Aim Dstab",  # 23
        "Dstab Antic",  # 24
        "Dstab Fall",  # 25
        "Dstab Land",  # 26
        "Attack Choice",  # 27
        "Jump Check",  # 28
        "Dash Antic",  # 29
        "Dash Attack",  # 30
        "Dash Recover",  # 31
        "Dash Attack 2",  # 32
        "Dash Attack 3",  # 33
        "Dstab Recover",  # 34
        "Ohead Antic",  # 35
        "Ohead Slashing",  # 36
        "Ohead Recover",  # 37
        "Evade Antic",  # 38
        "Evade Dash",  # 39
        "Evade Recover",  # 40
        "Shake Antic",  # 41
        "Shaking Start",  # 42
        "Shaking Spawn",  # 43
        "Dash Antic 2",  # 44
        "Dash Antic 3",  # 45
        "Air Dash?",  # 46
        "Fall",  # 47
        "Set Height",  # 48
        "Set Counter",  # 49
        "Damage Response",  # 50
        "To Attack?",  # 51
        "Jump Antic 2",  # 52
        "Aim Jump 2",  # 53
        "Jump 2",  # 54
        "In Air 2",  # 55
        "Land 2",  # 56
        "Shake End",  # 57
        "First Counter",  # 58
        "Shake?",  # 59
        "Inc Dstab",  # 60
        "Stun Start",  # 61
        "Stunned",  # 62
        "Stun Recover",  # 63
        "Waiting",  # 64
        "Repause",  # 65
        "Close Gates",  # 66
        "Intro Fall",  # 67
        "Intro Land",  # 68
        "Music",  # 69
        "Set Pos",  # 70
        "GG Wait",  # 71
    ],
    15: [  # Lost Kin
        "Init",  # 1
        "Pause",  # 2
        "Roar Start",  # 3
        "Roar",  # 4
        "Roar End",  # 5
        "Idle",  # 6
        "Set Dstab",  # 7
        "Jump",  # 8
        "In Air",  # 9
        "Jump Antic",  # 10
        "Land",  # 11
        "Aim Jump",  # 12
        "Aim Dstab",  # 13
        "Dstab Antic",  # 14
        "Dstab Fall",  # 15
        "Dstab Land",  # 16
        "Attack Choice",  # 17
        "Jump Check",  # 18
        "Dash Antic",  # 19
        "Dash Attack",  # 20
        "Dash Recover",  # 21
        "Dash Attack 2",  # 22
        "Dash Attack 3",  # 23
        "Dstab Recover",  # 24
        "Ohead Antic",  # 25
        "Ohead Slashing",  # 26
        "Ohead Recover",  # 27
        "Evade Antic",  # 28
        "Evade Dash",  # 29
        "Evade Recover",  # 30
        "Shake Antic",  # 31
        "Shaking Start",  # 32
        "Shaking Spawn",  # 33
        "Dash Antic 2",  # 34
        "Dash Antic 3",  # 35
        "Air Dash?",  # 36
        "Fall",  # 37
        "Set Height",  # 38
        "Set Counter",  # 39
        "Damage Response",  # 40
        "To Attack?",  # 41
        "Jump Antic 2",  # 42
        "Aim Jump 2",  # 43
        "Jump 2",  # 44
        "In Air 2",  # 45
        "Land 2",  # 46
        "Shake End",  # 47
        "First Counter",  # 48
        "Shake?",  # 49
        "Inc Dstab",  # 50
        "Stun Start",  # 51
        "Stunned",  # 52
        "Stun Recover",  # 53
        "Waiting",  # 54
        "Repause",  # 55
        "Close Gates",  # 56
        "Intro Fall",  # 57
        "Intro Land",  # 58
        "Set X",  # 59
        "Music",  # 60
        "Set X GG",  # 61
    ],
    16: [  # Nosk
        "Init",  # 1
        "Idle",  # 2
        "Charge Init",  # 3
        "Charge R",  # 4
        "Wait",  # 5
        "Jump Init",  # 6
        "Jump",  # 7
        "Jump Land",  # 8
        "Jump Wait",  # 9
        "Roar Init",  # 10
        "Roar Loop",  # 11
        "Roar Finish",  # 12
        "Hollow Idle",  # 13
        "Trans 1",  # 14
        "Trans 2",  # 15
        "Trans 3",  # 16
        "Trans 4",  # 17
        "Trans 5",  # 18
        "Roar End",  # 19
        "Jump Antic",  # 20
        "Launch",  # 21
        "Aim Jump",  # 22
        "Rising",  # 23
        "Falling",  # 24
        "Land 2",  # 25
        "Face L",  # 26
        "Face R",  # 27
        "Charge Start",  # 28
        "Charge L",  # 29
        "C Antic 2",  # 30
        "C Antic 3",  # 31
        "Encountered",  # 32
        "Wake",  # 33
        "Spit Antic",  # 34
        "Spit 1",  # 35
        "Spit 2",  # 36
        "Spit Recover",  # 37
        "Spit 3",  # 38
        "Spit 4",  # 39
        "Spit 5",  # 40
        "Set Spit",  # 41
        "Idle No Spit",  # 42
        "Roof Jump?",  # 43
        "RS Jump Antic",  # 44
        "RS Jump",  # 45
        "Roof Antic",  # 46
        "Roof Drop",  # 47
        "Fall Antic",  # 48
        "To Fall",  # 49
        "Init R",  # 50
        "Init L",  # 51
        "GG Pause",  # 52
        "GG Activate",  # 53
    ],
    17: [  # Winged Nosk
        "Init",  # 1
        "Idle",  # 2
        "Choose Attack",  # 3
        "Swoop Antic",  # 4
        "Swoop L",  # 5
        "Swoop Direction",  # 6
        "Swoop R",  # 7
        "Swoop Rise",  # 8
        "Dormant",  # 9
        "Set Pos",  # 10
        "Init Velocity",  # 11
        "Acid Roar Antic",  # 12
        "Spit 1",  # 13
        "Spit 2",  # 14
        "Spit 3",  # 15
        "Spit 4",  # 16
        "Spit 5",  # 17
        "Acid Roar End",  # 18
        "Spit 6",  # 19
        "Summon Roar",  # 20
        "Summon Recover",  # 21
        "Summon",  # 22
        "Resummon",  # 23
        "Shift Down?",  # 24
        "HP",  # 25
        "Choose Attack 2",  # 26
        "Roof Antic",  # 27
        "Roof Up",  # 28
        "Roof Impact",  # 29
        "Globs",  # 30
        "Roof Return",  # 31
    ],
    18: [  # The Collector
        "Init",  # 1
        "Start Fall",  # 2
        "Start Land",  # 3
        "Roar",  # 4
        "Roar End",  # 5
        "Roar Antic",  # 6
        "Roar Recover",  # 7
        "Hop Start Antic",  # 8
        "Hop Start",  # 9
        "Hop",  # 10
        "Hop Land",  # 11
        "Hop Wall",  # 12
        "Set Hops",  # 13
        "Move Choice",  # 14
        "Lunge Antic",  # 15
        "Lunge Launch",  # 16
        "Lunge Air",  # 17
        "Lunge Swipe",  # 18
        "Lunge Recover",  # 19
        "Jump Antic",  # 20
        "Jump",  # 21
        "Roof",  # 22
        "Summon?",  # 23
        "Return",  # 24
        "Slam",  # 25
        "Spawn",  # 26
        "Spawn Recover",  # 27
        "Resummon Pause",  # 28
        "Repos",  # 29
        "Return Antic",  # 30
        "Phase 1",  # 31
        "Buzzer",  # 32
        "Resummon?",  # 33
        "Spitter",  # 34
        "Roller",  # 35
        "Enemy Count",  # 36
        "Move Choice None",  # 37
        "Stun Start",  # 38
        "Stun Air",  # 39
        "Stun",  # 40
        "Stun Recover",  # 41
        "Death Start",  # 42
        "Stun Hit",  # 43
        "Sleep",  # 44
        "Music",  # 45
    ],
    19: [  # God Tamer
        "Init",  # 1
        "Idle",  # 2
        "Move Choice",  # 3
        "Forward",  # 4
        "Back",  # 5
        "Scuttle",  # 6
        "Scuttle End",  # 7
        "Attack Choice",  # 8
        "RC Antic",  # 9
        "RC Charge",  # 10
        "RC Charging",  # 11
        "RC Launch",  # 12
        "RC Air",  # 13
        "RC Land",  # 14
        "Spit Turn?",  # 15
        "Spit Retreat?",  # 16
        "Spit Antic",  # 17
        "Spit",  # 18
        "Spit Recover",  # 19
        "Fire Globs",  # 20
        "Dormant",  # 21
        "Wake",  # 22
    ],
    20: [  # Crystal Guardian
        "Init",  # 1
        "Idle",  # 2
        "Aim",  # 3
        "Beam Antic",  # 4
        "Beam",  # 5
        "Beam End",  # 6
        "Beam Recover",  # 7
        "CD",  # 8
        "Facing R?",  # 9
        "Shoot Antic",  # 10
        "Cancel",  # 11
        "Pause Frame",  # 12
        "Check Facing",  # 13
        "Sleep",  # 14
        "Wake",  # 15
        "Roar Start",  # 16
        "Roar",  # 17
        "Battle Init",  # 18
        "Roar End",  # 19
        "Jump Antic",  # 20
        "Launch",  # 21
        "Aim Jump",  # 22
        "Rising",  # 23
        "Falling",  # 24
        "Land",  # 25
        "Choice",  # 26
        "Hero Range?",  # 27
        "Range Check",  # 28
        "Face Hero",  # 29
        "Aim Left",  # 30
        "Aim Right",  # 31
        "First Idle",  # 32
        "Deparents",  # 33
        "Face Knight",  # 34
        "Clamps",  # 35
        "Lasers",  # 36
        "Shoot Lasers?",  # 37
        "First GG Move",  # 38
    ],
    21: [  # Enraged Guardian
        "Init",  # 1
        "Idle",  # 2
        "Beam End",  # 3
        "Beam Recover",  # 4
        "CD",  # 5
        "Cancel",  # 6
        "Pause Frame",  # 7
        "Check Facing",  # 8
        "Wake",  # 9
        "Roar Start",  # 10
        "Roar",  # 11
        "Battle Init",  # 12
        "Roar End",  # 13
        "Jump Antic",  # 14
        "Launch",  # 15
        "Aim Jump",  # 16
        "Rising",  # 17
        "Falling",  # 18
        "Land",  # 19
        "Choice",  # 20
        "Hero Range?",  # 21
        "First Idle",  # 22
        "Aim 2",  # 23
        "Beam Antic 2",  # 24
        "Beam 2",  # 25
        "Facing R? 2",  # 26
        "Shoot Antic 2",  # 27
        "Range Check 2",  # 28
        "Face Hero 2",  # 29
        "Aim Left 2",  # 30
        "Aim Right 2",  # 31
        "Face Knight",  # 32
        "GG Wait",  # 33
        "Laser Shoot",  # 34
        "Laser Shoot?",  # 35
        "First GG Move",  # 36
    ],
    22: [  # Uumuu
        "Init",  # 1
        "Idle",  # 2
        "Attack Antic",  # 3
        "Zapping",  # 4
        "Gen",  # 5
        "Choice",  # 6
        "Attack Recover",  # 7
        "First?",  # 8
        "Multizap",  # 9
        "Pattern Choice",  # 10
        "Explode",  # 11
        "Wounded",  # 12
        "Recover Antic",  # 13
        "Recover",  # 14
        "Sleep",  # 15
        "Wake Pause",  # 16
        "Wake Rumble",  # 17
        "Burst",  # 18
        "Start",  # 19
        "Music",  # 20
        "Roar",  # 21
        "Roar End",  # 22
    ],
    23: [  # Traitor Lord
        "Init",  # 1
        "Idle",  # 2
        "Attack Antic",  # 3
        "Attack 1",  # 4
        "Attack Swipe",  # 5
        "Attack Recover",  # 6
        "Cooldown",  # 7
        "Turn",  # 8
        "Stop At Edge",  # 9
        "Set Speed",  # 10
        "Feint?",  # 11
        "Feint",  # 12
        "Walk",  # 13
        "Speed Check",  # 14
        "Active",  # 15
        "Attack Choice",  # 16
        "Jump Antic",  # 17
        "Jump",  # 18
        "DSlash Antic",  # 19
        "DSlash",  # 20
        "Land",  # 21
        "Emerge Dust",  # 22
        "Fall",  # 23
        "Intro Land",  # 24
        "Roar",  # 25
        "Roar End",  # 26
        "Roar Recover",  # 27
        "Cloth?",  # 28
        "Death Shift?",  # 29
        "Shift L",  # 30
        "Shift R",  # 31
        "Death Ready",  # 32
        "Shifted?",  # 33
        "Turn?",  # 34
        "Stab Antic",  # 35
        "Stab",  # 36
        "Smash Antic",  # 37
        "Smash",  # 38
        "Smash End",  # 39
        "End",  # 40
        "Journal",  # 41
        "Steam",  # 42
        "Ready",  # 43
        "Blow",  # 44
        "Sickle Antic",  # 45
        "Sickle Throw",  # 46
        "Throw?",  # 47
        "Slam Antic",  # 48
        "Slamming",  # 49
        "Waves",  # 50
        "Slam End",  # 51
        "Slam?",  # 52
        "Too Close?",  # 53
        "Feint 2",  # 54
        "Repeat?",  # 55
        "Repeat",  # 56
        "Sickle Throw Recover",  # 57
        "Sick Throw CD",  # 58
        "Repeat Pos Check",  # 59
        "Check L",  # 60
        "Check R",  # 61
    ],
    24: [  # Grey Prince Zote
        "Init",  # 1
        "Dormant",  # 2
        "Enter 1",  # 3
        "Enter 2",  # 4
        "Enter 3",  # 5
        "Roar",  # 6
        "Roar End",  # 7
        "Activate",  # 8
        "Idle Start",  # 9
        "Move Choice",  # 10
        "Jump Antic",  # 11
        "Jump",  # 12
        "Aim Jump",  # 13
        "In Air",  # 14
        "Land Normal",  # 15
        "Set Jumps",  # 16
        "After Jump",  # 17
        "Land Waves",  # 18
        "Fall Through?",  # 19
        "FT Through",  # 20
        "FT Fall",  # 21
        "FT Slam",  # 22
        "FT Recover",  # 23
        "Ft Waves",  # 24
        "Charge Antic",  # 25
        "Charge R",  # 26
        "Charge Fall",  # 27
        "Charge Slam",  # 28
        "Charge Start",  # 29
        "Charge L",  # 30
        "Charge Through?",  # 31
        "To CT",  # 32
        "Charge Through",  # 33
        "CT Dir",  # 34
        "CT Left",  # 35
        "CT Right",  # 36
        "Charge Through 2",  # 37
        "CT Dir 2",  # 38
        "CT In L",  # 39
        "CT In R",  # 40
        "JS Antic",  # 41
        "JS Aim",  # 42
        "JS Jump",  # 43
        "JS In Air",  # 44
        "Stomp Antic",  # 45
        "Stomp",  # 46
        "Stomp Slash",  # 47
        "Slash End",  # 48
        "Slash Recover",  # 49
        "Land Dir",  # 50
        "Slash Waves R",  # 51
        "Slash Waves L",  # 52
        "Shift?",  # 53
        "Shift Dir",  # 54
        "Stomp Shift L",  # 55
        "Stomp Shift R",  # 56
        "Spit Antic",  # 57
        "Spit Recover",  # 58
        "Spit Dir",  # 59
        "Spit L",  # 60
        "Spit R",  # 61
        "Respit?",  # 62
        "Stun Start",  # 63
        "B Roar Antic",  # 64
        "B Roar",  # 65
        "BR Recover",  # 66
        "Unconstrain Dir",  # 67
        "Unconstrain L",  # 68
        "Unconstrain R",  # 69
        "Stun Air",  # 70
        "Stun",  # 71
        "Send Event",  # 72
        "Stand",  # 73
        "Run",  # 74
        "Run Antic",  # 75
        "Run Flip",  # 76
        "Run End",  # 77
        "Pause",  # 78
        "Level Check",  # 79
        "Level 1",  # 80
        "Set Damage",  # 81
        "Move Level",  # 82
        "Move Choice 1",  # 83
        "Spit Set",  # 84
        "Turn L",  # 85
        "Turn R",  # 86
        "Level 2",  # 87
        "Move Choice 2",  # 88
        "Level 3",  # 89
        "Move Choice 3",  # 90
        "4+",  # 91
        "Enter Short",  # 92
        "Music",  # 93
        "GG Pause",  # 94
    ],
    25: [  # Soul Warrior
        "Init",  # 1
        "Idle",  # 2
        "Shoot Antic",  # 3
        "Shoot Aim",  # 4
        "Shoot",  # 5
        "Shoot CD",  # 6
        "Slash Aim",  # 7
        "Slash Antic",  # 8
        "Dash",  # 9
        "Slash",  # 10
        "Slash Recover",  # 11
        "Side Tele Aim",  # 12
        "Tele Antic",  # 13
        "Tele L",  # 14
        "Tele R",  # 15
        "Side Tele",  # 16
        "After Side Tele",  # 17
        "Pause",  # 18
        "Move Decision",  # 19
        "Can Shoot?",  # 20
        "Tele Choice",  # 21
        "Up Tele Aim",  # 22
        "Up Tele",  # 23
        "Stomp Antic",  # 24
        "Stomp Air",  # 25
        "Stomp Slash",  # 26
        "Stomp Recover",  # 27
        "Evade Check",  # 28
        "Evade Choice",  # 29
        "Evade Antic",  # 30
        "Evade Dir",  # 31
        "Evade Right",  # 32
        "Evade",  # 33
        "Evade Recover",  # 34
        "Televade",  # 35
        "Stop",  # 36
        "Sleep",  # 37
        "Wake",  # 38
        "Cancel Frame",  # 39
        "Init Blast",  # 40
        "GG Pause",  # 41
        "GG Music",  # 42
    ],
    26: [  # Soul Master
        "Init",  # 1
        "Idle",  # 2
        "Teleport",  # 3
        "Tele Line",  # 4
        "Tele Away",  # 5
        "Pause",  # 6
        "Away Valid?",  # 7
        "Tele Top Y",  # 8
        "Tele Spinner X",  # 9
        "After Tele",  # 10
        "HS Summon",  # 11
        "HS Orb",  # 12
        "HS Dir",  # 13
        "HS Right",  # 14
        "HS Left",  # 15
        "HS Stop",  # 16
        "HS Tele Out",  # 17
        "HS Ret Left",  # 18
        "Hs Ret Right",  # 19
        "Reactivate",  # 20
        "HS Dissipate",  # 21
        "Tele Charge",  # 22
        "Charge Dir",  # 23
        "Charge Left",  # 24
        "Charge Right",  # 25
        "Charge Stop",  # 26
        "Tele Bot Y",  # 27
        "Set Shots",  # 28
        "Shot Antic",  # 29
        "Shot",  # 30
        "Tele Shoot",  # 31
        "Attack Choice",  # 32
        "Next?",  # 33
        "Damaged Idle",  # 34
        "Set Idle Timer",  # 35
        "Shoot Valid?",  # 36
        "Tele Quake",  # 37
        "TeleportQ",  # 38
        "Tele Line Q",  # 39
        "Quake Antic",  # 40
        "Quake Down",  # 41
        "Quake Land",  # 42
        "Re Pos",  # 43
        "Quake Waves",  # 44
        "Damage Tele Away",  # 45
        "Attack Instead",  # 46
        "Charge Antic",  # 47
        "Fakeout?",  # 48
        "Fake Down",  # 49
        "Reset",  # 50
        "Stun Init",  # 51
        "Stun L",  # 52
        "Stun R",  # 53
        "Stun Start 1",  # 54
        "Stun Start 2",  # 55
        "Stunned",  # 56
        "Stun Reset",  # 57
        "Stun Hit",  # 58
        "Stun Hit L",  # 59
        "Stun Hit R",  # 60
        "Sleep",  # 61
        "Start Arena",  # 62
        "Silhouette Rise",  # 63
        "Silhouette Summon",  # 64
        "Set Entry Point",  # 65
        "Teleport In",  # 66
        "Roar",  # 67
        "Roar End",  # 68
        "Encountered?",  # 69
        "Quick Start",  # 70
        "GG Pause",  # 71
        "Set Entry Point GG",  # 72
        "Music",  # 73
    ],
    27: [  # Soul Tyrant
        "Init",  # 1
        "Idle",  # 2
        "Teleport",  # 3
        "Tele Line",  # 4
        "Tele Away",  # 5
        "Pause",  # 6
        "Away Valid?",  # 7
        "Tele Top Y",  # 8
        "Tele Spinner X",  # 9
        "After Tele",  # 10
        "HS Summon",  # 11
        "HS Orb",  # 12
        "HS Dir",  # 13
        "HS Right",  # 14
        "HS Left",  # 15
        "HS Stop",  # 16
        "HS Tele Out",  # 17
        "HS Ret Left",  # 18
        "Hs Ret Right",  # 19
        "Reactivate",  # 20
        "HS Dissipate",  # 21
        "Tele Charge",  # 22
        "Charge Dir",  # 23
        "Charge Left",  # 24
        "Charge Right",  # 25
        "Charge Stop",  # 26
        "Tele Bot Y",  # 27
        "Set Shots",  # 28
        "Shot Antic",  # 29
        "Shot",  # 30
        "Tele Shoot",  # 31
        "Attack Choice",  # 32
        "Next?",  # 33
        "Damaged Idle",  # 34
        "Set Idle Timer",  # 35
        "Shoot Valid?",  # 36
        "Tele Quake",  # 37
        "TeleportQ",  # 38
        "Tele Line Q",  # 39
        "Quake Antic",  # 40
        "Quake Down",  # 41
        "Quake Land",  # 42
        "Re Pos",  # 43
        "Quake Waves",  # 44
        "Damage Tele Away",  # 45
        "Attack Instead",  # 46
        "Charge Antic",  # 47
        "Fakeout?",  # 48
        "Fake Down",  # 49
        "Reset",  # 50
        "Stun Init",  # 51
        "Stun L",  # 52
        "Stun R",  # 53
        "Stun Start 1",  # 54
        "Stun Start 2",  # 55
        "Stunned",  # 56
        "Stun Reset",  # 57
        "Stun Hit",  # 58
        "Stun Hit L",  # 59
        "Stun Hit R",  # 60
        "Sleep",  # 61
        "Set Entry Point",  # 62
        "Teleport In",  # 63
        "Roar",  # 64
        "Roar End",  # 65
        "Encountered?",  # 66
        "Quick Start",  # 67
        "Music",  # 68
        "GG Enter",  # 69
    ],
    28: [  # Dung Defender
        "Init",  # 1
        "Idle",  # 2
        "Dive In 1",  # 3
        "Dive In 2",  # 4
        "Underground",  # 5
        "Erupt Tunneling",  # 6
        "Tunneling L",  # 7
        "Tunneling R",  # 8
        "Erupt Antic",  # 9
        "Erupt Out",  # 10
        "Erupt Fall",  # 11
        "Erupt Land",  # 12
        "Set Min X",  # 13
        "Set Max X",  # 14
        "Throw Antic 1",  # 15
        "Set Throws",  # 16
        "Throw 1",  # 17
        "Set Throw Speed",  # 18
        "Keep Throwing?",  # 19
        "Throw Antic 2",  # 20
        "Throw Antic 3",  # 21
        "RJ Set",  # 22
        "After Throw?",  # 23
        "Roll Speed",  # 24
        "RJ Antic",  # 25
        "RJ Launch",  # 26
        "RJ In Air",  # 27
        "RJ Bounce",  # 28
        "RJ Wall",  # 29
        "RJ Unroll",  # 30
        "RJ Speed Adjust",  # 31
        "TD Set",  # 32
        "Dolph Dir",  # 33
        "Dolph Antic",  # 34
        "Diving",  # 35
        "Dolph Dives",  # 36
        "Repeat?",  # 37
        "Dolphin Recover",  # 38
        "DT Set",  # 39
        "To Dolph Pause",  # 40
        "Timer",  # 41
        "Evade Check",  # 42
        "Evade Dir",  # 43
        "Evade Start",  # 44
        "Evade Ball",  # 45
        "Evade Recover",  # 46
        "Will Evade?",  # 47
        "Reset Evade",  # 48
        "Stun Set",  # 49
        "Stun Launch",  # 50
        "Stun In Air",  # 51
        "Stun Land",  # 52
        "Stun Recover",  # 53
        "Throw 2",  # 54
        "Move Choice",  # 55
        "Sleep",  # 56
        "Wake",  # 57
        "First?",  # 58
        "Erupt Out First",  # 59
        "Roar?",  # 60
        "Roar End",  # 61
        "Set Rage",  # 62
        "Erupt Antic R",  # 63
        "Rage In",  # 64
        "Rage?",  # 65
        "Rage Roar",  # 66
        "Quaked Out",  # 67
        "Ball Hit Up",  # 68
        "Ball Hit Left",  # 69
        "Ball Hit Right",  # 70
        "Roll Voice",  # 71
        "Stop Voice",  # 72
        "DO Intro?",  # 73
        "Rage HP",  # 74
        "GG Pause",  # 75
    ],
}


def get_fsm_state_name(packed_state: int) -> str:
    """'Name (id)', or 'Unknown (id)' for state 0 and ids missing from the table."""
    boss_id = packed_state >> 8
    state_id = packed_state & 0xFF
    states = BOSS_FSM_STATES.get(boss_id, [])
    name = states[state_id - 1] if 0 < state_id <= len(states) else "Unknown"
    return f"{name} ({state_id})"


def fsm_state_names(boss_id: int) -> list[str]:
    """One-hot column names for a boss: column 0 is the unknown state, column i is state id i."""
    return ["Unknown", *BOSS_FSM_STATES[boss_id]]


def fsm_one_hot(packed_states: np.ndarray, boss_id: int) -> np.ndarray:
    """(T,) packed FSM states -> (T, N + 1) float32 one-hot; unknown or out-of-range ids map to column 0."""
    n_states = len(BOSS_FSM_STATES[boss_id])
    state_id = packed_states & 0xFF
    return np.eye(n_states + 1, dtype=np.float32)[np.where(state_id <= n_states, state_id, 0)]
