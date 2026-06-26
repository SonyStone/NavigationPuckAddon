import bpy
import mathutils

from ..utils.modal import add_modal_handler
from ..utils.operator_return import OperatorReturn, OperatorReturnType
from . import activation_runtime
from ..activation import ACTIVATION_HOTKEY_MENU, MODIFIER_KEY_STATE_ATTRS, get_activation_mode
from .editor_context import (
    context_key,
    editor_context_override_at_event,
    event_position_in_context,
    event_window_position_is_in_context_area,
    find_supported_editor_overrides,
    is_supported_editor_context,
    make_context_override,
)
from .puck_invocation import _invoke_navigation_puck_widget
from .puck_menu import NavigationPuckWidget
from .shortcut_overlay import NavigationPuckShortcut


class NavigationPuckWidgetOperator(bpy.types.Operator):
    """Show the Navigation Puck viewport overlay."""
    bl_idname = "navigation_puck.widget"
    bl_label = "Navigation Puck"
    bl_options = {'REGISTER'}

    follow_mouse: bpy.props.BoolProperty(default=False) # type: ignore
    drag_select: bpy.props.BoolProperty(default=False) # type: ignore
    dismiss_on_key_release: bpy.props.BoolProperty(default=False) # type: ignore
    dismiss_key_type: bpy.props.StringProperty(default="") # type: ignore
    anchor_x: bpy.props.FloatProperty(default=-1.0) # type: ignore
    anchor_y: bpy.props.FloatProperty(default=-1.0) # type: ignore

    app = NavigationPuckWidget()

    # Override Operator method
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Start the modal operator and initialize widget

        Called once when the operator is invoked
        """
        anchor = None
        if self.anchor_x >= 0.0 and self.anchor_y >= 0.0:
            anchor = mathutils.Vector((self.anchor_x, self.anchor_y))

        if self.app.is_running:
            return self.app.reopen(
                context,
                event,
                self.follow_mouse,
                self.drag_select,
                anchor,
                self.dismiss_on_key_release,
                self.dismiss_key_type,
            )

        if not add_modal_handler(context, self):
            return OperatorReturn.CANCELLED

        return self.app.invoke(
            context,
            event,
            self.follow_mouse,
            self.drag_select,
            anchor,
            self.dismiss_on_key_release,
            self.dismiss_key_type,
        )

    # Override Operator method
    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        """
        Handle widget events

        Called on any mouse move or click event, as well as every frame
        """

        return self.app.event_handler(context, event)


class NavigationPuckHotkeyOperator(bpy.types.Operator):
    """Open the Navigation Puck from a keymap item."""
    bl_idname = "navigation_puck.hotkey"
    bl_label = "Navigation Puck Hotkey"
    bl_options = {'INTERNAL'}

    @staticmethod
    def _operator_result_for_event(result: OperatorReturnType, event: bpy.types.Event) -> OperatorReturnType:
        if 'CANCELLED' in result:
            return OperatorReturn.CANCELLED

        if event.type in MODIFIER_KEY_STATE_ATTRS:
            return OperatorReturn.PASS_THROUGH

        return OperatorReturn.FINISHED

    def _invoke_in_editor_context(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        *,
        require_event_in_context: bool = True,
    ) -> OperatorReturnType:
        if not is_supported_editor_context(context):
            return OperatorReturn.CANCELLED

        if require_event_in_context and not event_window_position_is_in_context_area(context, event):
            return OperatorReturn.CANCELLED

        anchor = event_position_in_context(context, event, mathutils.Vector((-1.0, -1.0)))
        context_override = make_context_override(context, anchor)
        try:
            result = _invoke_navigation_puck_widget(
                context,
                anchor,
                drag_select=False,
                dismiss_on_key_release=True,
                dismiss_key_type=event.type,
                context_override=context_override,
            )
        except RuntimeError as ex:
            print(f"Navigation Puck hotkey failed to open menu: {ex}")
            return OperatorReturn.CANCELLED

        return self._operator_result_for_event(result, event)

    def _invoke_with_override(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
        override: dict[str, object],
        *,
        require_event_in_context: bool,
        failure_message: str,
    ) -> OperatorReturnType:
        try:
            with context.temp_override(**override):
                return self._invoke_in_editor_context(
                    bpy.context,
                    event,
                    require_event_in_context=require_event_in_context,
                )
        except (ReferenceError, RuntimeError, TypeError) as ex:
            print(f"{failure_message}: {ex}")
            return OperatorReturn.CANCELLED

    def _invoke_first_supported_editor_context(
        self,
        context: bpy.types.Context,
        event: bpy.types.Event,
    ) -> OperatorReturnType:
        for override in find_supported_editor_overrides(context.window_manager):
            result = self._invoke_with_override(
                context,
                event,
                override,
                require_event_in_context=False,
                failure_message="Navigation Puck hotkey failed to use fallback editor context",
            )
            if 'CANCELLED' not in result:
                return result

        return OperatorReturn.CANCELLED

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if get_activation_mode(context) != ACTIVATION_HOTKEY_MENU:
            return OperatorReturn.PASS_THROUGH

        target_override = editor_context_override_at_event(context, event)
        if target_override:
            result = self._invoke_with_override(
                context,
                event,
                target_override,
                require_event_in_context=True,
                failure_message="Navigation Puck hotkey failed to use cursor editor context",
            )
            if 'CANCELLED' not in result:
                return result

        result = self._invoke_in_editor_context(context, event)
        if 'CANCELLED' not in result:
            return result

        return self._invoke_first_supported_editor_context(context, event)


class NavigationPuckShortcutOperator(bpy.types.Operator):
    """Run the always-available Navigation Puck viewport shortcut."""
    bl_idname = "navigation_puck.shortcut"
    bl_label = "Navigation Puck Shortcut"
    bl_options = {'INTERNAL'}

    restart_context: bpy.props.BoolProperty(default=False) # type: ignore

    apps: dict[tuple[int, int, int, int], NavigationPuckShortcut] = {}

    @classmethod
    def get_app(cls, key: tuple[int, int, int, int]) -> NavigationPuckShortcut | None:
        return cls.apps.get(key)

    @classmethod
    def has_active_pointer_interaction(
        cls,
        *,
        excluding: NavigationPuckShortcut | None = None,
    ) -> bool:
        return any(
            app is not excluding and app.is_running and app._has_active_pointer_interaction()
            for app in cls.apps.values()
        )

    @classmethod
    def ensure_app(cls, context: bpy.types.Context) -> NavigationPuckShortcut:
        key = context_key(context)
        app = cls.apps.get(key)
        if app is None:
            app = NavigationPuckShortcut()
            cls.apps[key] = app
        return app

    @classmethod
    def reveal_after_menu(
        cls,
        context: bpy.types.Context,
        key: tuple[int, int, int, int] | None,
        mouse_pos: mathutils.Vector,
    ) -> None:
        app = cls.apps.get(key) if key is not None else cls.apps.get(context_key(context))
        if app:
            app.reveal_after_menu(mouse_pos)

    @classmethod
    def shutdown_all(cls) -> None:
        for app in cls.apps.values():
            app.shutdown()
        cls.apps.clear()

    @classmethod
    def prune_missing(cls, existing_keys: set[tuple[int, int, int, int]]) -> None:
        for key, app in list(cls.apps.items()):
            if key not in existing_keys:
                app.shutdown()
                del cls.apps[key]

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if not is_supported_editor_context(context):
            return OperatorReturn.CANCELLED

        self.app = self.ensure_app(context)

        if self.app.is_running and not self.restart_context:
            self.app.refresh_context(context)
            return OperatorReturn.CANCELLED

        if not add_modal_handler(context, self):
            return OperatorReturn.CANCELLED

        self.modal_generation = self.app.next_modal_generation()
        return self.app.invoke(context, event)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> OperatorReturnType:
        if getattr(self, "modal_generation", None) != self.app.modal_generation:
            return OperatorReturn.FINISHED
        return self.app.event_handler(context, event)


refresh_activation_runtime = activation_runtime.refresh_activation_runtime


def register() -> None:
    activation_runtime.configure(NavigationPuckShortcutOperator)
    activation_runtime.refresh_activation_runtime(bpy.context)


def unregister() -> None:
    activation_runtime.shutdown()
    NavigationPuckWidgetOperator.app.shutdown()
