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

from . src import operators, panels
from . src.keymap import register_keymaps, unregister_keymaps

bl_info = {
    "name": "Heavypoly Tools",
    "author": "Your Name",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Heavypoly",
    "description": "Custom tools for Blender workflow enhancement",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}


def register():
    operators.register()
    panels.register()
    register_keymaps()


def unregister():
    unregister_keymaps()
    panels.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
