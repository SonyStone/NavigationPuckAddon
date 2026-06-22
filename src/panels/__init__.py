from . import navigation_puck_operators

classes = (
    navigation_puck_operators.NavigationPuckWidgetOperator,
    navigation_puck_operators.NavigationPuckHotkeyOperator,
    navigation_puck_operators.NavigationPuckShortcutOperator,
)


def register() -> None:
    navigation_puck_operators.register()


def unregister() -> None:
    navigation_puck_operators.unregister()
