# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy  # type: ignore

from . src import operators, panels, preferences
from . src.keymap import register_keymaps, unregister_keymaps

bl_info = {
    "name": "Navigation Puck Addon",
    "author": "Ilya",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Navigation Puck",
    "description": "Custom navigation puck widget",
    "warning": "",
    "doc_url": "https://github.com/SonyStone/navigation_puck_addon",
    "tracker_url": "https://github.com/SonyStone/navigation_puck_addon/issues",
    "category": "3D View",
}

# Update register and unregister functions to include preferences

def register():
    preferences.register()
    operators.register()
    panels.register()
    register_keymaps()


def unregister():
    unregister_keymaps()
    panels.unregister()
    operators.unregister()
    preferences.unregister()


if __name__ == "__main__":
    register()
