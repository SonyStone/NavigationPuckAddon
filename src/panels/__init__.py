from . import navigation_puck_widget

CURRENT_MAIN_WIDGET = navigation_puck_widget.NavigationPuckWidgetOperator

classes = (
    CURRENT_MAIN_WIDGET,
    navigation_puck_widget.NavigationPuckHotkeyOperator,
    navigation_puck_widget.NavigationPuckShortcutOperator,
)


def register() -> None:
    navigation_puck_widget.register()


def unregister() -> None:
    navigation_puck_widget.unregister()
