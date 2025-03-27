<template>
  <header>
    <h1>ImageDiff</h1>
  </header>

  <section class="image-comparison-container">
    <div class="control-panel">
      <div class="selectors">
        <div class="selector">
          <label>Target:</label>
          <select v-model="selectedTarget" @change="loadAllMovies">
            <option v-for="target in targets" :key="target" :value="target">{{ target }}</option>
          </select>
        </div>

        <div class="selector">
          <label>Movie:</label>
          <select v-model="selectedMovie" @change="loadBuildsByMovie">
            <option v-for="movie in movies" :key="movie" :value="movie">{{ movie }}</option>
          </select>
        </div>

        <div class="selector">
          <label>Build A:</label>
          <select v-model="buildA" @change="updateComparison">
            <option v-for="build in builds" :key="build" :value="build">{{ build }}</option>
          </select>
        </div>

        <div class="selector">
          <label>Build B:</label>
          <select v-model="buildB" @change="updateComparison">
            <option v-for="build in builds" :key="build" :value="build">{{ build }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Comparison Results Section -->
    <div v-if="selectedMovie && buildA && buildB" class="comparison-container">
      <h2>Comparing {{ selectedMovie }} between builds {{ buildA }} and {{ buildB }}</h2>

      <!-- Summary of differences -->
      <div class="comparison-summary">
        <div v-if="isLoading" class="loading-indicator">
          <p>Loading comparison data...</p>
        </div>
        <div v-else-if="frames.length === 0" class="no-frames">
          <p>No frames available for comparison</p>
        </div>
        <div v-else class="diff-summary">
          <div class="summary-item">
            <span class="summary-label">Total Frames:</span>
            <span class="summary-value">{{ frames.length }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Frames with Differences:</span>
            <span class="summary-value">{{ diffFrameCount }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Average Difference:</span>
            <span class="summary-value">{{ avgDiffPercentage.toFixed(2) }}%</span>
          </div>
        </div>
      </div>

      <!-- Three column grid layout -->
      <div class="column-headers">
        <div class="column-header build-a">Build A: {{ buildA }}</div>
        <div class="column-header diff">Difference</div>
        <div class="column-header build-b">Build B: {{ buildB }}</div>
      </div>

      <div class="frames-grid">
        <template v-for="(frame, index) in frames" :key="frame">
          <!-- Build A Column -->
          <div class="grid-cell">
            <div class="frame-title">{{ selectedMovie }}-{{ frame }}</div>
            <img
                :src="getFrameImageUrl(buildA, frame)"
                :alt="`${selectedMovie}-${frame} in ${buildA}`"
                class="comparison-image"
            />
          </div>

          <!-- Diff Column -->
          <div class="grid-cell diff-cell"
               :class="{ 'has-diff': frameDiffs[frame] && frameDiffs[frame].percentage > 0 }">
            <div class="frame-title">
              <span v-if="frameDiffs[frame]" class="diff-percentage"
                    :class="{ 'no-diff': frameDiffs[frame].percentage === 0 }">
                {{
                  frameDiffs[frame].percentage > 0 ?
                      `${frameDiffs[frame].percentage.toFixed(2)}%` :
                      'No Diff'
                }}
              </span>
              <span v-else>Loading...</span>
            </div>
            <img
                :src="getFrameDiffUrl(frame)"
                :alt="`Diff of ${frame}`"
                class="comparison-image"
                @click="regenerateDiff(frame)"
            />
          </div>

          <!-- Build B Column -->
          <div class="grid-cell">
            <div class="frame-title">{{ selectedMovie }}-{{ frame }}</div>
            <img
                :src="getFrameImageUrl(buildB, frame)"
                :alt="`${selectedMovie}-${frame} in ${buildB}`"
                class="comparison-image"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- Instruction message when movie or builds not selected -->
    <div v-else class="instruction-container">
      <h2>Please select a movie and two builds to compare</h2>
      <p>Use the control panel above to select:</p>
      <ol>
        <li>Target environment</li>
        <li>Movie</li>
        <li>Two different builds to compare (Build A and Build B)</li>
      </ol>
      <p>Once selected, the application will display frame-by-frame comparisons between the two builds.</p>
    </div>
  </section>
</template>

<script setup>
import {ref, onMounted, computed, watch} from 'vue';

const targets = ref([]);
const movies = ref([]);
const builds = ref([]);
const frames = ref([]);
const commonFrames = ref([]);

const selectedTarget = ref('');
const selectedMovie = ref('');
const buildA = ref('');
const buildB = ref('');

const isLoading = ref(false);

// For storing frame difference data
const frameDiffs = ref({});
// For caching image URLs
const frameImageUrls = ref({});
const frameDiffUrls = ref({});

// Computed properties for difference statistics
const diffFrameCount = computed(() => {
  return Object.values(frameDiffs.value).filter(diff => diff.percentage > 0).length;
});

const avgDiffPercentage = computed(() => {
  const diffs = Object.values(frameDiffs.value);
  if (diffs.length === 0) return 0;

  const sum = diffs.reduce((acc, curr) => acc + curr.percentage, 0);
  return sum / diffs.length;
});

// Get image URL for a specific frame (with caching)
const getFrameImageUrl = (build, frame) => {
  const cacheKey = `${selectedTarget.value}-${build}-${selectedMovie.value}-${frame}`;

  // If URL is already cached, return it
  if (frameImageUrls.value[cacheKey]) {
    return frameImageUrls.value[cacheKey];
  }

  // Otherwise, construct a URL
  return `/screenshots/${selectedTarget.value}/${build}/${selectedMovie.value}-${frame}.png`;
};

// Get URL for difference image between builds
const getFrameDiffUrl = (frame) => {
  const cacheKey = `${selectedTarget.value}-${buildA.value}-${buildB.value}-${selectedMovie.value}-${frame}`;

  // If URL is already cached, return it
  if (frameDiffUrls.value[cacheKey]) {
    return frameDiffUrls.value[cacheKey];
  }

  return 'https://placehold.co/600x400?text=Generating+diff...';
};

// Load target list
const loadTargets = async () => {
  try {
    const response = await fetch('/api/targets', {
      method: 'POST'
    });
    targets.value = await response.json();

    if (targets.value.length > 0) {
      selectedTarget.value = targets.value[0];
      await loadAllMovies();
    }
  } catch (error) {
    console.error('Failed to load targets:', error);
  }
};

// Load all movies across all builds for selected target
const loadAllMovies = async () => {
  try {
    // Reset selections
    selectedMovie.value = '';
    buildA.value = '';
    buildB.value = '';
    builds.value = [];
    frames.value = [];

    // Use the new API endpoint to get all movies across all builds
    const response = await fetch('/api/all-movies', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value
      })
    });

    movies.value = await response.json();

  } catch (error) {
    console.error('Failed to load all movies:', error);
  }
};

// Load builds that contain the selected movie
const loadBuildsByMovie = async () => {
  if (!selectedMovie.value) return;

  try {
    // Reset build selections and frames
    buildA.value = '';
    buildB.value = '';
    builds.value = [];
    frames.value = [];
    frameDiffs.value = {};

    // Use the new API endpoint to get builds that contain the selected movie
    const response = await fetch('/api/builds-by-movie', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value,
        movie: selectedMovie.value
      })
    });

    builds.value = await response.json();

    // Set default builds if available
    if (builds.value.length >= 2) {
      buildA.value = builds.value[0];
      buildB.value = builds.value[1];
      updateComparison();
    } else if (builds.value.length === 1) {
      buildA.value = builds.value[0];
    }

  } catch (error) {
    console.error('Failed to load builds for movie:', error);
  }
};

// Update the comparison when builds are selected
const updateComparison = async () => {
  if (!selectedMovie.value || !buildA.value || !buildB.value) return;

  // Clear frame data
  frames.value = [];
  frameDiffs.value = {};
  frameImageUrls.value = {};
  frameDiffUrls.value = {};

  isLoading.value = true;

  try {
    // Load frames for build A
    const framesAResponse = await fetch('/api/frames', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value,
        build: buildA.value,
        movie: selectedMovie.value
      })
    });
    const framesA = await framesAResponse.json();

    // Load frames for build B
    const framesBResponse = await fetch('/api/frames', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value,
        build: buildB.value,
        movie: selectedMovie.value
      })
    });
    const framesB = await framesBResponse.json();

    // Find common frames between both builds
    const commonFrameSet = new Set();

    framesA.forEach(frame => {
      if (framesB.includes(frame)) {
        commonFrameSet.add(frame);
      }
    });

    // Sort frames naturally (numerically if possible)
    frames.value = Array.from(commonFrameSet).sort((a, b) => {
      const numA = parseInt(a);
      const numB = parseInt(b);
      if (!isNaN(numA) && !isNaN(numB)) {
        return numA - numB;
      }
      return a.localeCompare(b);
    });

    // Load images and generate diffs
    if (frames.value.length > 0) {
      // Preload images for both builds
      await Promise.all([
        ...frames.value.map(frame => loadFrameImage(buildA.value, frame)),
        ...frames.value.map(frame => loadFrameImage(buildB.value, frame))
      ]);

      // Generate diffs for all frames
      await generateAllDiffs();
    }

  } catch (error) {
    console.error('Failed to update comparison:', error);
  } finally {
    isLoading.value = false;
  }
};

// Load image for a single frame
const loadFrameImage = async (build, frame) => {
  try {
    const response = await fetch('/api/image', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        target: selectedTarget.value,
        build: build,
        movie: selectedMovie.value,
        frame: frame
      })
    });

    if (response.ok) {
      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);

      // Cache image URL
      const cacheKey = `${selectedTarget.value}-${build}-${selectedMovie.value}-${frame}`;
      frameImageUrls.value[cacheKey] = imageUrl;
    }
  } catch (error) {
    console.error(`Failed loading image for ${build}-${frame}:`, error);
  }
};

// Generate difference images for all frames
const generateAllDiffs = async () => {
  if (!selectedMovie.value || !buildA.value || !buildB.value) return;

  const diffPromises = frames.value.map(frame => generateDiff(frame));
  await Promise.all(diffPromises);
};

// Generate difference image for a single frame
const generateDiff = async (frame) => {
  if (!selectedMovie.value || !buildA.value || !buildB.value) return;

  try {
    const imagePathA = `../screenshots/${selectedTarget.value}/${buildA.value}/${selectedMovie.value}-${frame}.png`;
    const imagePathB = `../screenshots/${selectedTarget.value}/${buildB.value}/${selectedMovie.value}-${frame}.png`;

    const response = await fetch('/api/diff', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        imageA: imagePathA,
        imageB: imagePathB,
        threshold: 5
      })
    });

    if (response.ok) {
      // Get difference statistics from response headers
      const differentPixels = parseInt(response.headers.get('X-Different-Pixels') || '0');
      const percentage = parseFloat(response.headers.get('X-Difference-Percentage') || '0');

      // Store difference statistics
      frameDiffs.value[frame] = {
        differentPixels,
        percentage
      };

      // Get difference image and store URL
      const blob = await response.blob();
      const diffUrl = URL.createObjectURL(blob);

      const cacheKey = `${selectedTarget.value}-${buildA.value}-${buildB.value}-${selectedMovie.value}-${frame}`;
      frameDiffUrls.value[cacheKey] = diffUrl;
    }
  } catch (error) {
    console.error(`Failed generating diff for frame ${frame}:`, error);
  }
};

// Manually regenerate a diff for a specific frame
const regenerateDiff = (frame) => {
  if (!selectedMovie.value || !buildA.value || !buildB.value) return;

  // Clear diff cache for this frame
  const cacheKey = `${selectedTarget.value}-${buildA.value}-${buildB.value}-${selectedMovie.value}-${frame}`;
  delete frameDiffUrls.value[cacheKey];
  delete frameDiffs.value[frame];

  // Regenerate diff
  generateDiff(frame);
};

onMounted(async () => {
  console.log('Starting to fetch targets');
  await loadTargets();
});
</script>

<style>
header {
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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.selectors {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.selector {
  display: flex;
  flex-direction: column;
  min-width: 150px;
}

.selector label {
  margin-bottom: 5px;
  font-weight: bold;
}

select {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.diff-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Comparison Container */
.comparison-container, .instruction-container {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.comparison-container h2, .instruction-container h2 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.5rem;
  color: #333;
}

.instruction-container ol {
  margin-left: 20px;
  margin-bottom: 20px;
}

.instruction-container li {
  margin-bottom: 8px;
}

/* Comparison Summary */
.comparison-summary {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.loading-indicator, .no-frames {
  width: 100%;
  text-align: center;
  padding: 20px;
  font-weight: bold;
  color: #666;
}

.diff-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  width: 100%;
}

.summary-item {
  display: flex;
  flex-direction: column;
  min-width: 150px;
}

.summary-label {
  font-weight: bold;
  font-size: 14px;
  color: #666;
}

.summary-value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}

/* Three Column Grid Layout */
.column-headers {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
  font-weight: bold;
  text-align: center;
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 10px;
}

.column-header {
  padding: 8px;
}

.frames-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}

.grid-cell {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background-color: #fff;
  margin-bottom: 10px;
  padding-bottom: 10px;
}

.grid-cell.has-diff {
  border-color: #f44336;
}

.frame-title {
  padding: 8px;
  text-align: center;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ddd;
  font-size: 14px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.diff-percentage {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: #f44336;
  color: white;
  font-size: 12px;
}

.diff-percentage.no-diff {
  background-color: #4caf50;
}

.comparison-image {
  width: 100%;
  height: 300px;
  object-fit: contain;
  display: block;
  margin: 0 auto;
  padding: 5px;
}

.diff-cell .comparison-image {
  cursor: pointer;
}

.diff-cell .comparison-image:hover {
  opacity: 0.9;
}
</style>