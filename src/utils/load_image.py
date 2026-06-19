
import typing
import os
import bpy

def load_image(image_name: str) -> typing.Optional[bpy.types.Image]:
    """Load an image from the given path, or return existing if already loaded"""

    addon_dir = os.path.dirname(os.path.dirname(__file__))
    image_path = os.path.join(addon_dir, 'assets', image_name)
    try:
        image = bpy.data.images.load(
            image_path, check_existing=True)  # type: ignore
        return image
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return None