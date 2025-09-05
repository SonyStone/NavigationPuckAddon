
from . import imgui_example
from . import view_tools_widget
from . import test_widget
from . import test_imgui_widget

classes = (
    view_tools_widget.NavigationPuckViewToolsWidget,
    imgui_example.NavigationPuckImguiExample,
    test_widget.TestWidget,
    test_imgui_widget.TestImguiWidget,
)

# CURRENT_MAIN_WIDGET = view_tools_widget.NavigationPuckViewToolsWidget
# CURRENT_MAIN_WIDGET = imgui_example.NavigationPuckImguiExample
# CURRENT_MAIN_WIDGET = test_widget.TestWidget
CURRENT_MAIN_WIDGET = test_imgui_widget.TestImguiWidget