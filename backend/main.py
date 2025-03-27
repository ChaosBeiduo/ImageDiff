from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from typing import List
from config import SCREENSHOTS_DIR, DIFF_OUTPUT_DIR
# Import the diff generator function
from diff_generator import generate_diff, DiffRequest

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


@app.post("/api/diff")
async def diff_endpoint(request: DiffRequest):
    return await generate_diff(request)

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