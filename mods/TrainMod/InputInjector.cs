using CoreMod;
using UnityEngine;

namespace TrainMod
{
    /// <summary>
    /// Injects synthetic controller actions into Hollow Knight's HeroActions and HeroController.
    /// Intercepts LookForInput to override directional axes and commits button states to InControl.
    /// </summary>
    public static class InputInjector
    {
        private static bool _isHooked;
        private static ActionButtons _currentAction = ActionButtons.None;

        public static bool IsInjecting { get; private set; }

        public static void Hook()
        {
            if (_isHooked) return;
            On.HeroController.LookForInput += OnLookForInput;
            _isHooked = true;
        }

        public static void Unhook()
        {
            if (!_isHooked) return;
            On.HeroController.LookForInput -= OnLookForInput;
            _isHooked = false;
            Reset();
        }

        /// <summary>
        /// Injects an action mask for the current physics tick.
        /// </summary>
        public static void ApplyAction(ActionButtons action)
        {
            IsInjecting = true;
            _currentAction = action;

            var inputHandler = InputHandler.Instance;
            if (inputHandler != null && inputHandler.inputActions != null)
            {
                var a = inputHandler.inputActions;
                ulong tick = (ulong)Time.frameCount;
                float dt = Time.fixedDeltaTime;

                bool jump = (action & ActionButtons.Jump) != 0;
                bool attack = (action & ActionButtons.Attack) != 0;
                bool dash = (action & ActionButtons.Dash) != 0;
                bool cast = (action & ActionButtons.CastFocus) != 0;
                bool left = (action & ActionButtons.Left) != 0;
                bool right = (action & ActionButtons.Right) != 0;
                bool up = (action & ActionButtons.Up) != 0;
                bool down = (action & ActionButtons.Down) != 0;

                a.jump.CommitWithState(jump, tick, dt);
                a.attack.CommitWithState(attack, tick, dt);
                a.dash.CommitWithState(dash, tick, dt);
                a.cast.CommitWithState(cast, tick, dt);
                a.focus.CommitWithState(cast, tick, dt);
                a.left.CommitWithState(left, tick, dt);
                a.right.CommitWithState(right, tick, dt);
                a.up.CommitWithState(up, tick, dt);
                a.down.CommitWithState(down, tick, dt);
            }

            var hc = HeroController.instance;
            if (hc != null)
            {
                hc.move_input = (_currentAction.HasFlag(ActionButtons.Right) ? 1f : 0f) - (_currentAction.HasFlag(ActionButtons.Left) ? 1f : 0f);
                hc.vertical_input = (_currentAction.HasFlag(ActionButtons.Up) ? 1f : 0f) - (_currentAction.HasFlag(ActionButtons.Down) ? 1f : 0f);
            }
        }

        /// <summary>
        /// Disengages injection and clears all active button states, restoring full player control.
        /// </summary>
        public static void Reset()
        {
            if (!IsInjecting) return;
            IsInjecting = false;
            _currentAction = ActionButtons.None;

            var inputHandler = InputHandler.Instance;
            if (inputHandler != null && inputHandler.inputActions != null)
            {
                var a = inputHandler.inputActions;
                ulong tick = (ulong)Time.frameCount;
                float dt = Time.fixedDeltaTime;

                a.jump.CommitWithState(false, tick, dt);
                a.attack.CommitWithState(false, tick, dt);
                a.dash.CommitWithState(false, tick, dt);
                a.cast.CommitWithState(false, tick, dt);
                a.focus.CommitWithState(false, tick, dt);
                a.left.CommitWithState(false, tick, dt);
                a.right.CommitWithState(false, tick, dt);
                a.up.CommitWithState(false, tick, dt);
                a.down.CommitWithState(false, tick, dt);
            }

            var hc = HeroController.instance;
            if (hc != null)
            {
                hc.move_input = 0f;
                hc.vertical_input = 0f;
            }
        }

        private static void OnLookForInput(On.HeroController.orig_LookForInput orig, HeroController self)
        {
            orig(self);

            if (IsInjecting)
            {
                self.move_input = (_currentAction.HasFlag(ActionButtons.Right) ? 1f : 0f) - (_currentAction.HasFlag(ActionButtons.Left) ? 1f : 0f);
                self.vertical_input = (_currentAction.HasFlag(ActionButtons.Up) ? 1f : 0f) - (_currentAction.HasFlag(ActionButtons.Down) ? 1f : 0f);
            }
        }
    }
}
