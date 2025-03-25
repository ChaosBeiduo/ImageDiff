from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import glob
from typing import List, Dict, Any
import numpy as np
from PIL import Image, ImageChops
import io
import time
from pathlib import Path

from config import SCREENSHOTS_DIR, DIFF_OUTPUT_DIR

app = FastAPI(title="Director Screenshots Comparison API")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(DIFF_OUTPUT_DIR, exist_ok=True)

app.mount("/diff_images", StaticFiles(directory=DIFF_OUTPUT_DIR), name="diff_images")


class DiffRequest(BaseModel):
    targetA: str
    targetB: str
    threshold: float = 5.0


@app.get("/api/targets", response_model=List[str])
async def get_targets():
    """Get all targets"""
    try:
        targets = [d for d in os.listdir(SCREENSHOTS_DIR)
                  if os.path.isdir(os.path.join(SCREENSHOTS_DIR, d))]
        return targets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取targets失败: {str(e)}")


@app.get("/api/builds", response_model=List[str])
async def get_builds(target: str = Query(..., description="Target名称")):
    """Get bundles from selected target"""
    target_dir = os.path.join(SCREENSHOTS_DIR, target)
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail=f"Target '{target}' 不存在")

    try:
        builds = [d for d in os.listdir(target_dir)
                 if os.path.isdir(os.path.join(target_dir, d))]

        builds.sort(key=lambda x: int(x) if x.isdigit() else float('inf'))
        return builds
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取builds失败: {str(e)}")


@app.get("/api/movies", response_model=List[str])
async def get_movies(target: str = Query(..., description="Target名称")):
    """TODO: Get movies from selected bundle"""

    target_dir = os.path.join(SCREENSHOTS_DIR, target)
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail=f"Target '{target}' 不存在")

    try:
        build_dirs = [d for d in os.listdir(target_dir)
                     if os.path.isdir(os.path.join(target_dir, d))]

        if not build_dirs:
            return []

        first_build_dir = os.path.join(target_dir, build_dirs[0])

        # get movie's name
        movie_names = set()
        for file in os.listdir(first_build_dir):
            if file.endswith('.png'):
                movie_name = file.rsplit('-', 1)[0]
                movie_names.add(movie_name)

        return sorted(list(movie_names))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取movies失败: {str(e)}")


@app.get("/api/frames", response_model=List[str])
async def get_frames(
    target: str = Query(..., description="Target名称"),
    movie: str = Query(..., description="Movie名称")
):
    """TODO: Get movies from selected bundle and movie"""
    target_dir = os.path.join(SCREENSHOTS_DIR, target)
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail=f"Target '{target}' 不存在")

    try:
        build_dirs = [d for d in os.listdir(target_dir)
                     if os.path.isdir(os.path.join(target_dir, d))]

        if not build_dirs:
            return []

        first_build_dir = os.path.join(target_dir, build_dirs[0])

        frame_numbers = []
        for file in os.listdir(first_build_dir):
            if file.startswith(f"{movie}-") and file.endswith('.png'):
                frame_number = file.rsplit('-', 1)[1].replace('.png', '')
                frame_numbers.append(frame_number)

        frame_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
        return frame_numbers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取frames失败: {str(e)}")


@app.get("/api/image")
async def get_image(
    target: str = Query(..., description="Target名称"),
    build: str = Query(..., description="Build编号"),
    movie: str = Query(..., description="Movie名称"),
    frame: str = Query(..., description="Frame编号")
):
    """get selected pic"""
    image_path = os.path.join(SCREENSHOTS_DIR, target, build, f"{movie}-{frame}.png")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"图片不存在: {image_path}")

    return FileResponse(image_path)


@app.post("/api/diff", response_model=Dict[str, Any])
async def generate_diff(request: DiffRequest):
    """TODO: generate diff pic"""
    try:
        # pic path
        image_path_a = os.path.join(SCREENSHOTS_DIR, request.targetA)
        image_path_b = os.path.join(SCREENSHOTS_DIR, request.targetB)

        # check if exists
        if not os.path.exists(image_path_a):
            raise HTTPException(status_code=404, detail=f"图片A不存在: {image_path_a}")
        if not os.path.exists(image_path_b):
            raise HTTPException(status_code=404, detail=f"图片B不存在: {image_path_b}")

        # open pic
        image_a = Image.open(image_path_a).convert('RGB')
        image_b = Image.open(image_path_b).convert('RGB')

        # resize pic to same size
        if image_a.size != image_b.size:
            width = min(image_a.width, image_b.width)
            height = min(image_a.height, image_b.height)
            image_a = image_a.resize((width, height))
            image_b = image_b.resize((width, height))

        # calc diff
        diff_image = ImageChops.difference(image_a, image_b)

        # turn into numpy array
        diff_array = np.array(diff_image)

        # calc pixel
        threshold = int(255 * request.threshold / 100)
        diff_mask = np.sum(diff_array, axis=2) > threshold
        different_pixels = np.sum(diff_mask)
        total_pixels = diff_array.shape[0] * diff_array.shape[1]
        diff_percentage = (different_pixels / total_pixels) * 100

        # create diff pic
        highlight = np.zeros_like(diff_array)
        highlight[diff_mask] = [255, 0, 0]

        alpha = np.zeros_like(diff_array[..., 0])
        alpha[diff_mask] = 200

        final_diff = image_b.copy()
        final_diff_array = np.array(final_diff)
        for i in range(3):
            channel = final_diff_array[..., i]
            channel[diff_mask] = int(0.7 * channel[diff_mask] + 0.3 * highlight[diff_mask][..., i])

        # turn array to pic
        final_diff = Image.fromarray(final_diff_array)

        timestamp = int(time.time())
        diff_filename = f"diff_{timestamp}.png"
        diff_path = os.path.join(DIFF_OUTPUT_DIR, diff_filename)

        # save
        final_diff.save(diff_path)

        # return results
        return {
            "diffImageUrl": f"/diff_images/{diff_filename}",
            "differentPixels": int(different_pixels),
            "percentage": float(diff_percentage),
            "width": width,
            "height": height
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成差异图失败: {str(e)}")

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