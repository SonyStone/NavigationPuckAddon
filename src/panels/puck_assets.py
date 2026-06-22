import typing

from ..utils.load_image import load_image


ACTION_IMAGE_NAMES = {
    "pan": "pan_tool_wght300.png",
    "orbit": "3d_rotation_wght300.png",
    "zoom": "zoom_in_wght300.png",
    "roll": "flip_camera_wght300.png",
}

SHORTCUT_ICON_NAME = "explore_wght300.png"


def load_action_images(images: dict[str, typing.Any]) -> None:
    for action, image_name in ACTION_IMAGE_NAMES.items():
        if not images.get(action):
            images[action] = load_image(image_name)


def all_action_images_loaded(images: dict[str, typing.Any]) -> bool:
    return all(images.get(action) for action in ACTION_IMAGE_NAMES)


def load_shortcut_icon() -> typing.Any:
    return load_image(SHORTCUT_ICON_NAME)
