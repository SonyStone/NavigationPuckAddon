from . import navigation_puck_widget

classes = (
    navigation_puck_widget.NavigationPuckWidgetOperator,
    navigation_puck_widget.NavigationPuckHotkeyOperator,
    navigation_puck_widget.NavigationPuckShortcutOperator,
)


def register() -> None:
    navigation_puck_widget.register()


def unregister() -> None:
    navigation_puck_widget.unregister()
