from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from typing import List
import numpy as np
from PIL import Image, ImageChops
from config import SCREENSHOTS_DIR, DIFF_OUTPUT_DIR

app = FastAPI(title="Director Screenshots Comparison API")

# Allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)

app.mount("/diff_images", StaticFiles(directory=DIFF_OUTPUT_DIR), name="diff_images")
app.mount("/screenshots", StaticFiles(directory=SCREENSHOTS_DIR), name="screenshots")


# Define request models
class TargetRequest(BaseModel):
    pass  # Empty request body, as getting targets doesn't require parameters


class BuildRequest(BaseModel):
    target: str


class MovieRequest(BaseModel):
    target: str
    build: str


class FrameRequest(BaseModel):
    target: str
    build: str
    movie: str


class ImageRequest(BaseModel):
    target: str
    build: str
    movie: str
    frame: str


class DiffRequest(BaseModel):
    imageA: str  # Path to image A
    imageB: str  # Path to image B
    threshold: float = 5.0


@app.post("/api/targets", response_model=List[str])
async def get_targets(request: TargetRequest = Body(default=None)):
    """Get all targets"""
    try:
        targets = [d for d in os.listdir(SCREENSHOTS_DIR)
                   if os.path.isdir(os.path.join(SCREENSHOTS_DIR, d))]
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed getting targets: {str(e)}")


@app.post("/api/builds", response_model=List[str])
async def get_builds(request: BuildRequest):
    """Get builds for a specified target"""
    target_dir = os.path.join(SCREENSHOTS_DIR, request.target)
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail=f"Target '{request.target}' does not exist")

    try:
        builds = [d for d in os.listdir(target_dir)
                  if os.path.isdir(os.path.join(target_dir, d))]

        builds.sort(key=lambda x: int(x) if x.isdigit() else float('inf'))
        return builds
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed getting builds: {str(e)}")


@app.post("/api/movies", response_model=List[str])
async def get_movies(request: MovieRequest):
    build_dir = os.path.join(SCREENSHOTS_DIR, request.target, request.build)
    print(f"Looking for movies in: {build_dir}")

    if not os.path.exists(build_dir):
        raise HTTPException(status_code=404, detail=f"Build path '{build_dir}' does not exist")

    try:
        movie_names = set()
        for file in os.listdir(build_dir):
            if file.endswith('.png'):
                movie_name = file.rsplit('-', 1)[0]
                movie_names.add(movie_name)

        result = sorted(list(movie_names))
        print(f"Found movies: {result}")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed getting movies: {str(e)}")


@app.post("/api/frames", response_model=List[str])
async def get_frames(request: FrameRequest):
    """Get frames for a specified target, build, and movie"""
    build_dir = os.path.join(SCREENSHOTS_DIR, request.target, request.build)
    if not os.path.exists(build_dir):
        raise HTTPException(status_code=404, detail=f"Build path '{build_dir}' does not exist")

    try:
        frame_numbers = []
        for file in os.listdir(build_dir):
            if file.startswith(f"{request.movie}-") and file.endswith('.png'):
                frame_number = file.rsplit('-', 1)[1].replace('.png', '')
                frame_numbers.append(frame_number)

        frame_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
        return frame_numbers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed getting frames: {str(e)}")

@app.post("/api/image")
async def get_image(request: ImageRequest):
    """Directly return the image file"""
    image_path = os.path.join(SCREENSHOTS_DIR, request.target, request.build,
                              f"{request.movie}-{request.frame}.png")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Image does not exist: {image_path}")

    # Return the image file directly
    return FileResponse(
        image_path,
        media_type="image/png",
        filename=f"{request.movie}-{request.frame}.png"
    )


from fastapi.responses import FileResponse
import io

@app.post("/api/diff")
async def generate_diff(request: DiffRequest):
    """Generate a difference image from two image paths and return the image directly"""
    try:
        # Check if files exist
        if not os.path.exists(request.imageA):
            raise HTTPException(status_code=404, detail=f"Image A does not exist: {request.imageA}")
        if not os.path.exists(request.imageB):
            raise HTTPException(status_code=404, detail=f"Image B does not exist: {request.imageB}")

        # Open images
        image_a = Image.open(request.imageA).convert('RGB')
        image_b = Image.open(request.imageB).convert('RGB')

        # Resize images
        if image_a.size != image_b.size:
            width = min(image_a.width, image_b.width)
            height = min(image_a.height, image_b.height)
            image_a = image_a.resize((width, height))
            image_b = image_b.resize((width, height))
        else:
            width, height = image_a.size

        # Calculate difference
        diff_image = ImageChops.difference(image_a, image_b)

        # Convert to numpy array
        diff_array = np.array(diff_image)

        # Calculate pixels
        threshold = int(255 * request.threshold / 100)

        # Calculate total difference for each pixel (sum across RGB channels)
        pixel_diff_sum = np.sum(diff_array, axis=2)

        # Create difference mask (boolean array indicating which pixels differ beyond threshold)
        diff_mask = pixel_diff_sum > threshold

        # Count different pixels
        different_pixels = np.sum(diff_mask)

        # Calculate total pixels
        total_pixels = diff_array.shape[0] * diff_array.shape[1]

        # Calculate difference percentage
        diff_percentage = (different_pixels / total_pixels) * 100

        # Create array to highlight differences
        highlight = np.zeros_like(diff_array)
        highlight[diff_mask] = [255, 0, 0]  # Set different pixels to red

        # Create final difference image
        final_diff = image_b.copy()
        final_diff_array = np.array(final_diff)

        # Apply highlight to each channel
        for i in range(3):
            # Get current channel
            channel = final_diff_array[..., i]
            # Apply blend effect for masked pixels
            if np.any(diff_mask):  # Ensure there are difference pixels
                channel_values = channel[diff_mask]
                highlight_values = highlight[diff_mask, i]
                mixed_values = channel_values * 0.7 + highlight_values * 0.3
                channel[diff_mask] = mixed_values.astype(np.uint8)

        # Convert array back to image
        final_diff = Image.fromarray(final_diff_array)

        # Save image to memory
        img_byte_arr = io.BytesIO()
        final_diff.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        # Create response headers with difference statistics
        headers = {
            "X-Different-Pixels": str(int(different_pixels)),
            "X-Difference-Percentage": str(float(diff_percentage)),
            "X-Image-Width": str(int(width)),
            "X-Image-Height": str(int(height))
        }

        # Return the image directly
        return Response(
            content=img_byte_arr.getvalue(),
            media_type="image/png",
            headers=headers
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed Generating Diff Image: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <html>
        <head>
            <title>Director Screenshots Comparison API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .container { margin-top: 20px; }
            </style>
        </head>
        <body>
            <h1>Director Screenshots Comparison API</h1>
            <div class="container">
                <p>Welcome to the Director Screenshots Comparison API.</p>
                <p>Visit <a href="/docs">/docs</a> for the interactive API documentation.</p>
            </div>
        </body>
    </html>
    """
    return html_content

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)