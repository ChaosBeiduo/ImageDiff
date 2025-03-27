<template>
  <header>
    <h1>ImageDiff</h1>
  </header>

  <section class="image-comparison-container">
    <div class="control-panel">
      <div class="selectors">
        <div class="selector">
          <label>Target:</label>
          <select v-model="selectedTarget" @change="loadBuilds">
            <option v-for="target in targets" :key="target" :value="target">{{ target }}</option>
          </select>
        </div>

        <div class="selector">
          <label>Build:</label>
          <select v-model="selectedBuild" @change="loadMovies">
            <option v-for="build in builds" :key="build" :value="build">{{ build }}</option>
          </select>
        </div>

        <div class="selector">
          <label>Movie:</label>
          <select v-model="selectedMovie" @change="loadFrames">
            <option v-for="movie in movies" :key="movie" :value="movie">{{ movie }}</option>
          </select>
        </div>
      </div>

      <div class="diff-controls" style="display: none">
        <label>Diff Threshold:</label>
        <input type="range" v-model="diffThreshold" min="0" max="100" step="1" />
        <span>{{ diffThreshold }}%</span>
      </div>
    </div>

    <!-- Display all frames in multiple rows -->
    <div class="all-frames-grid">
      <div
          v-for="(frame, index) in frames"
          :key="frame"
          class="frame-comparison-row"
      >
        <!-- Current frame image -->
        <div class="column">
          <div class="column-header">
            <h3>{{ selectedBuild }}-{{ selectedMovie }}-{{ frame }}</h3>
          </div>
          <div class="image-wrapper">
            <img
                :src="getFrameImageUrl(frame)"
                :alt="`${selectedMovie}-${frame}`"
                class="comparison-image"
            />
          </div>
        </div>

        <!-- Difference between current and next frame -->
        <div class="column diff-column">
          <div class="column-header">
            <h3>Diff</h3>
          </div>
          <div class="image-wrapper">
            <div v-if="index < frames.length - 1">
              <div class="diff-stats" v-if="frameDiffs[frame]">
                <template v-if="frameDiffs[frame].differentPixels > 0">
                  <span>Diff: {{ frameDiffs[frame].percentage.toFixed(2) }}%</span>
                </template>
                <template v-else>
                  <span>No Diff</span>
                </template>
              </div>
              <img
                  :src="getFrameDiffUrl(frame, frames[index + 1])"
                  :alt="`Diff ${frame}-${frames[index + 1]}`"
                  class="comparison-image"
                  @click="regenerateDiff(frame, frames[index + 1])"
              />
            </div>
            <div v-else class="no-diff-placeholder">
              <div class="diff-stats">
                <span>No comparison frame</span>
              </div>
              <div class="placeholder-image">
                <p>This is the last frame</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Next frame image -->
        <div class="column">
          <div class="column-header">
            <h3 v-if="index < frames.length - 1">{{ selectedBuild }}-{{ selectedMovie }}-{{ frames[index + 1] }}</h3>
            <h3 v-else>Next Frame</h3>
          </div>
          <div class="image-wrapper">
            <img
                v-if="index < frames.length - 1"
                :src="getFrameImageUrl(frames[index + 1])"
                :alt="`${selectedMovie}-${frames[index + 1]}`"
                class="comparison-image"
            />
            <div v-else class="placeholder-image">
              <p>No next frame</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';

const targets = ref([]);
const builds = ref([]);
const movies = ref([]);
const frames = ref([]);

const selectedTarget = ref('');
const selectedBuild = ref('');
const selectedMovie = ref('');

const diffThreshold = ref(5);

// For storing frame difference data
const frameDiffs = ref({});
// For caching image URLs
const frameImageUrls = ref({});
const frameDiffUrls = ref({});

// Get image URL for a specific frame (with caching)
const getFrameImageUrl = (frame) => {
  const cacheKey = `${selectedTarget.value}-${selectedBuild.value}-${selectedMovie.value}-${frame}`;

  // If URL is already cached, return it
  if (frameImageUrls.value[cacheKey]) {
    return frameImageUrls.value[cacheKey];
  }

  // Otherwise, construct a temporary URL (will be replaced with async loaded one)
  return `/screenshots/${selectedTarget.value}/${selectedBuild.value}/${selectedMovie.value}-${frame}.png`;
};

// Get URL for difference image between two frames (with caching)
const getFrameDiffUrl = (frame1, frame2) => {
  const cacheKey = `${selectedTarget.value}-${selectedBuild.value}-${selectedMovie.value}-${frame1}-${frame2}`;

  // If URL is already cached, return it
  if (frameDiffUrls.value[cacheKey]) {
    return frameDiffUrls.value[cacheKey];
  }

  // Return a placeholder URL, actual image will be replaced after async loading
  return '/placeholder-diff.png';  // You need to provide a placeholder image
};

// Load build list
const loadBuilds = async () => {
  try {
    const response = await fetch('/api/builds', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value
      })
    });
    builds.value = await response.json();
    selectedBuild.value = builds.value[0] || '';
    loadMovies();
  } catch (error) {
    console.error('Failed Loading Build:', error);
  }
};

// Load movie list
const loadMovies = async () => {
  try {
    const response = await fetch('/api/movies', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value,
        build: selectedBuild.value
      })
    });
    movies.value = await response.json();
    selectedMovie.value = movies.value[0] || '';
    loadFrames();
  } catch (error) {
    console.error('Failed Loading Movie:', error);
  }
};

// Load frame list and preload images for each frame
const loadFrames = async () => {
  try {
    // Clear cache
    frameImageUrls.value = {};
    frameDiffUrls.value = {};
    frameDiffs.value = {};

    const response = await fetch('/api/frames', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value,
        build: selectedBuild.value,
        movie: selectedMovie.value
      })
    });
    frames.value = await response.json();

    if (frames.value.length > 0) {
      // Preload all frame images and diff images
      preloadFrameImages();
      generateAllDiffs();
    }
  } catch (error) {
    console.error('Failed Loading Frames:', error);
  }
};

// Preload images for all frames
const preloadFrameImages = async () => {
  for (const frame of frames.value) {
    loadFrameImage(frame);
  }
};

// Load image for a single frame
const loadFrameImage = async (frame) => {
  try {
    const response = await fetch('/api/image', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value,
        build: selectedBuild.value,
        movie: selectedMovie.value,
        frame: frame
      })
    });

    if (response.ok) {
      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);

      // Cache image URL
      const cacheKey = `${selectedTarget.value}-${selectedBuild.value}-${selectedMovie.value}-${frame}`;
      frameImageUrls.value[cacheKey] = imageUrl;
    }
  } catch (error) {
    console.error(`Failed loading image for frame ${frame}:`, error);
  }
};

// Generate difference images for all consecutive frames
const generateAllDiffs = async () => {
  for (let i = 0; i < frames.value.length - 1; i++) {
    const currentFrame = frames.value[i];
    const nextFrame = frames.value[i + 1];
    generateDiff(currentFrame, nextFrame);
  }
};

// Generate difference image between two frames
const generateDiff = async (frame1, frame2) => {
  try {
    const imagePathA = `../screenshots/${selectedTarget.value}/${selectedBuild.value}/${selectedMovie.value}-${frame1}.png`;
    const imagePathB = `../screenshots/${selectedTarget.value}/${selectedBuild.value}/${selectedMovie.value}-${frame2}.png`;

    const response = await fetch('/api/diff', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        imageA: imagePathA,
        imageB: imagePathB,
        threshold: diffThreshold.value
      })
    });

    if (response.ok) {
      // Get difference statistics from response headers
      const differentPixels = parseInt(response.headers.get('X-Different-Pixels') || '0');
      const percentage = parseFloat(response.headers.get('X-Difference-Percentage') || '0');

      // Store difference statistics
      frameDiffs.value[frame1] = {
        differentPixels,
        percentage
      };

      // Get difference image and store URL
      const blob = await response.blob();
      const diffUrl = URL.createObjectURL(blob);

      const cacheKey = `${selectedTarget.value}-${selectedBuild.value}-${selectedMovie.value}-${frame1}-${frame2}`;
      frameDiffUrls.value[cacheKey] = diffUrl;
    }
  } catch (error) {
    console.error(`Failed generating diff between frames ${frame1} and ${frame2}:`, error);
  }
};

onMounted(async () => {
  console.log('Starting to fetch targets');
  try {
    const response = await fetch('/api/targets', {
      method: 'POST'
    });
    targets.value = await response.json();

    if (targets.value.length > 0) {
      selectedTarget.value = targets.value[0];
      await loadBuilds();
    }
  } catch (error) {
    console.error('Failed initialize:', error);
  }
});
</script>

<style>
header{
  text-align: center;
  background: white;
}

.image-comparison-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}

.control-panel {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.selectors {
  display: flex;
  gap: 15px;
}

.selector {
  display: flex;
  flex-direction: column;
}

.selector label {
  margin-bottom: 5px;
  font-weight: bold;
}

.diff-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.all-frames-grid {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.frame-comparison-row {
  display: flex;
  gap: 10px;
  border: 1px solid #ddd;
  padding: 15px;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.column {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.column-header {
  width: 100%;
  text-align: center;
  margin-bottom: 10px;
  height: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.column-header h3 {
  margin: 0;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.diff-column {
  position: relative;
}

.diff-stats {
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  position: absolute;
  top: 10px;
  z-index: 1;
}

.image-wrapper {
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
}

.comparison-image {
  width: 100%;
  height: 300px;
  object-fit: contain;
  border: 1px solid #ccc;
  background-color: white;
}

.placeholder-image {
  width: 100%;
  height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  color: #666;
  font-size: 16px;
  font-weight: bold;
}

.no-diff-placeholder {
  width: 100%;
  position: relative;
}

button {
  margin-top: 10px;
  padding: 5px 10px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background-color: #45a049;
}
</style>