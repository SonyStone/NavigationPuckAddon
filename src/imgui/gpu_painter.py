
import typing
import blf
import gpu
import gpu_extras
import bpy

from . import Rect, Theme


class GPUPainter:
    """Handles drawing operations"""

    def __init__(self, theme: Theme):
        self.theme = theme

    def draw_rect(
        self,
        rect: Rect,
        color: typing.Tuple[float, float, float, float]
    ):
        """Draw filled rectangle"""
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        batch = gpu_extras.batch.batch_for_shader(  # type: ignore
            shader, 'TRI_FAN',
            {
                "pos": [
                    (rect.x, rect.y),
                    (rect.x + rect.width, rect.y),
                    (rect.x + rect.width, rect.y + rect.height),
                    (rect.x, rect.y + rect.height)
                ]
            }
        )

        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)  # type: ignore

    def draw_rect_outline(
        self,
        rect: Rect,
        color: typing.Tuple[float, float, float, float],
        width: float = 1.0
    ):
        """Draw rectangle outline"""
        # Draw outline as four rectangles
        # Top
        self.draw_rect(Rect(rect.x, rect.y + rect.height -
                       width, rect.width, width), color)
        # Bottom
        self.draw_rect(Rect(rect.x, rect.y, rect.width, width), color)
        # Left
        self.draw_rect(Rect(rect.x, rect.y, width, rect.height), color)
        # Right
        self.draw_rect(Rect(rect.x + rect.width - width,
                       rect.y, width, rect.height), color)

    def draw_text(
        self,
        text: str,
        pos: typing.Tuple[float, float],
        color: typing.Tuple[float, float, float, float]
    ):
        """Draw text at position"""
        font_id = 0
        blf.position(font_id, pos[0], pos[1], 0)
        blf.size(font_id, self.theme.font_size)
        blf.color(font_id, *color)
        blf.draw(font_id, text)

    def draw_image(self, image_path: str, pos: typing.Tuple[float, float], size: typing.Optional[typing.Tuple[float, float]] = None):
        """Draw image at position"""
        try:
            # Load image if not already loaded
            image = bpy.data.images.load(image_path, check_existing=True)
            
            if not image:
                return
            
            # Get image dimensions
            img_width, img_height = image.size
            
            # Use provided size or original image size
            if size:
                width, height = size
            else:
                width, height = img_width, img_height
            
            # Ensure image has a GPU texture
            image.gl_load()

            # Enable alpha blending for transparency
            gpu.state.blend_set('ALPHA')
            
            # Disable depth testing for UI elements
            gpu.state.depth_test_set('NONE')

            # Use the built-in IMAGE shader
            shader = gpu.shader.from_builtin('IMAGE')
            
            # Convert screen coordinates
            x, y = pos
            
            # Create quad vertices
            vertices = [
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height)
            ]
            
            # Texture coordinates - no flipping, direct mapping
            tex_coords = [
                (0, 1),  # Bottom-left
                (1, 1),  # Bottom-right  
                (1, 0),  # Top-right
                (0, 0)   # Top-left
            ]
            
            # Create batch
            batch = gpu_extras.batch.batch_for_shader(  # type: ignore
                shader, 'TRI_FAN',
                {
                    "pos": vertices,
                    "texCoord": tex_coords
                }
            )
            
            # Create texture from image with proper filtering
            texture = gpu.texture.from_image(image)
            
            # Bind texture and draw
            shader.bind()
            shader.uniform_sampler("image", texture)
            batch.draw(shader)  # type: ignore

            # Ensure proper GPU state for text rendering
            gpu.state.blend_set('ALPHA')
            gpu.state.depth_test_set('NONE')
            
        except (RuntimeError, AttributeError, OSError):
            # Fallback to drawing a rectangle if image loading fails
            if size:
                rect = Rect(pos[0], pos[1], size[0], size[1])
                self.draw_rect(rect, (0.5, 0.5, 0.5, 1.0))  # Gray rectangle as fallback


    def get_text_size(self, text: str) -> typing.Tuple[float, float]:
        """Get text dimensions"""
        font_id = 0
        blf.size(font_id, self.theme.font_size)
        width, height = blf.dimensions(font_id, text)
        return (width, height)
        
