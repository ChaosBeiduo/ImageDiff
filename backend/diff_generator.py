import os
import io
import base64
import numpy as np
from PIL import Image, ImageChops
from fastapi import HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

class DiffRequest(BaseModel):
    imageA: str
    imageB: str
    threshold: float = 5.0


def check_image_files(image_a_path: str, image_b_path: str):
    """Check if image files exist"""
    if not os.path.exists(image_a_path):
        raise HTTPException(status_code=404, detail=f"Image A does not exist: {image_a_path}")
    if not os.path.exists(image_b_path):
        raise HTTPException(status_code=404, detail=f"Image B does not exist: {image_b_path}")


def encode_image(image):
    """Encode an image to a base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def load_and_resize_images(image_a_path: str, image_b_path: str):
    """Load and resize images"""
    image_a = Image.open(image_a_path).convert('RGB')
    image_b = Image.open(image_b_path).convert('RGB')

    # Resize images if they have different dimensions
    if image_a.size != image_b.size:
        width = min(image_a.width, image_b.width)
        height = min(image_a.height, image_b.height)
        image_a = image_a.resize((width, height))
        image_b = image_b.resize((width, height))
    else:
        width, height = image_a.size

    return image_a, image_b, width, height


def calculate_difference_mask(image_a, image_b, threshold_percentage):
    """Calculate difference mask between two images"""
    # Calculate difference
    diff_image = ImageChops.difference(image_a, image_b)

    # Convert to numpy array
    diff_array = np.array(diff_image)

    # Calculate threshold pixels
    threshold = int(255 * threshold_percentage / 100)

    # Calculate total difference for each pixel (sum across RGB channels)
    pixel_diff_sum = np.sum(diff_array, axis=2)

    # Create difference mask (boolean array indicating which pixels differ beyond threshold)
    diff_mask = pixel_diff_sum > threshold

    return diff_mask, diff_array, diff_image


def calculate_stats(diff_mask, image_shape):
    """Calculate difference statistics"""
    # Count different pixels
    different_pixels = np.sum(diff_mask)

    # Calculate total pixels
    total_pixels = image_shape[0] * image_shape[1]

    # Calculate difference percentage
    diff_percentage = (different_pixels / total_pixels) * 100

    return different_pixels, total_pixels, diff_percentage


def create_transparent_diff_image(image_b, diff_mask, width, height):
    """Create transparent difference image"""
    # Create a transparent image (RGBA mode)
    transparent_diff = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    transparent_array = np.array(transparent_diff)

    # Get the original pixels and convert to RGBA
    image_b_rgba = image_b.convert('RGBA')
    image_b_array = np.array(image_b_rgba)

    # Ensure full alpha channel for differing pixels
    image_b_array[..., 3] = 255  # Set alpha channel to fully opaque

    # Copy only the differing pixels to the transparent image
    for y in range(height):
        for x in range(width):
            if diff_mask[y, x]:
                transparent_array[y, x] = image_b_array[y, x]

    # Convert array back to image
    final_diff = Image.fromarray(transparent_array, 'RGBA')

    return final_diff


def save_image_to_memory(image):
    """Save image to memory"""
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr


def create_response_headers(different_pixels, diff_percentage, width, height):
    """Create response headers with difference statistics"""
    return {
        "X-Different-Pixels": str(int(different_pixels)),
        "X-Difference-Percentage": str(float(diff_percentage)),
        "X-Image-Width": str(int(width)),
        "X-Image-Height": str(int(height))
    }

async def generate_diff(request: DiffRequest):
    """Generate a difference image from two image paths with transparent background and return the image directly"""
    try:
        # Check if files exist
        check_image_files(request.imageA, request.imageB)

        # Load and resize images
        image_a, image_b, width, height = load_and_resize_images(request.imageA, request.imageB)

        # Calculate difference mask
        diff_mask, diff_array, diff_image = calculate_difference_mask(image_a, image_b, request.threshold)

        # Calculate statistics
        different_pixels, total_pixels, diff_percentage = calculate_stats(diff_mask, diff_array.shape)

        # Create transparent difference image
        final_diff = create_transparent_diff_image(image_b, diff_mask, width, height)

        # Save image to memory
        img_byte_arr = save_image_to_memory(final_diff)

        # Create response headers
        headers = create_response_headers(different_pixels, diff_percentage, width, height)

        # Return image
        return Response(
            content=img_byte_arr.getvalue(),
            media_type="image/png",
            headers=headers
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed Generating Diff Image: {str(e)}")