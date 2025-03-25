<template>
  <header>
    <h1>ImageDiff</h1>
    <p>This is an screenshots comparison website</p>
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
          <select v-model="selectedBuild" @change="loadImages">
            <option v-for="build in builds" :key="build" :value="build">{{ build }}</option>
          </select>
        </div>

        <div class="selector">
          <label>Movie:</label>
          <select v-model="selectedMovie" @change="loadFrames">
            <option v-for="movie in movies" :key="movie" :value="movie">{{ movie }}</option>
          </select>
        </div>

        <div class="selector">
          <label>Frame:</label>
          <select v-model="selectedFrame" @change="loadImages">
            <option v-for="frame in frames" :key="frame" :value="frame">{{ frame }}</option>
          </select>
        </div>
      </div>

      <div class="diff-controls">
        <label>差异阈值:</label>
        <input type="range" v-model="diffThreshold" min="0" max="100" step="1" />
        <span>{{ diffThreshold }}%</span>
        <button @click="generateDiff" class="diff-button">ReGenerate</button>
      </div>
    </div>

    <div class="three-column-comparison">
      <div class="column">
        <div class="column-header">
          <h3>Build {{ selectedBuild }}</h3>
        </div>
        <div class="image-wrapper">
          <img v-if="imageA" :src="imageA" alt="Build A Screenshot" class="comparison-image" />
          <div v-else class="placeholder">choosing image A</div>
        </div>
      </div>

      <div class="column diff-column">
        <div class="column-header">
          <h3>Diff</h3>
          <div v-if="diffStats" class="diff-stats">
            <span>差异像素: {{ diffStats.differentPixels }}</span>
            <span>差异比例: {{ diffStats.percentage.toFixed(2) }}%</span>
          </div>
        </div>
        <div class="image-wrapper">
          <img v-if="diffImage" :src="diffImage" alt="Difference Image" class="comparison-image" />
          <div v-else class="placeholder">Waiting for diff..</div>
        </div>
      </div>

      <!-- 右侧对比图 -->
      <div class="column">
        <div class="column-header">
          <h3>Build {{ selectedBuild }}</h3>
        </div>
        <div class="image-wrapper">
          <img v-if="imageB" :src="imageB" alt="Build B Screenshot" class="comparison-image" />
          <div v-else class="placeholder">请选择要比较的图片</div>
        </div>
      </div>
    </div>

    <!-- 帧导航器 -->
    <div class="frame-navigator">
      <button @click="prevFrame" :disabled="!hasPrevFrame">上一帧</button>
      <div class="frame-thumbnails">
        <div
            v-for="frame in frames"
            :key="frame"
            :class="['frame-thumbnail', { active: frame === selectedFrame }]"
            @click="selectedFrame = frame; loadImages()"
        >
          {{ frame }}
        </div>
      </div>
      <button @click="nextFrame" :disabled="!hasNextFrame">下一帧</button>
    </div>
  </section>
</template>
<script setup lang="ts">
import {computed, onMounted, ref} from 'vue';

// 状态变量
const targets = ref([]);
const builds = ref([]);
const movies = ref([]);
const frames = ref([]);

const selectedTarget = ref('');
const selectedBuild = ref('');
const selectedMovie = ref('');
const selectedFrame = ref('');

const imageA = ref(null);
const imageB = ref(null);
const diffImage = ref(null);
const diffStats = ref(null);
const diffThreshold = ref(5); // 默认差异阈值5%

// 计算属性
const hasPrevFrame = computed(() => {
  const currentIndex = frames.value.indexOf(selectedFrame.value);
  return currentIndex > 0;
});

const hasNextFrame = computed(() => {
  const currentIndex = frames.value.indexOf(selectedFrame.value);
  return currentIndex < frames.value.length - 1 && currentIndex !== -1;
});

// 方法
const loadBuilds = async () => {
  try {
    const response = await fetch(`/api/builds?target=${selectedTarget.value}`);
    builds.value = await response.json();
    selectedBuild.value = builds.value[0] || '';
    loadMovies();
  } catch (error) {
    console.error('加载build失败:', error);
  }
};

const loadMovies = async () => {
  try {
    const response = await fetch(`/api/movies?target=${selectedTarget.value}`);
    movies.value = await response.json();
    selectedMovie.value = movies.value[0] || '';
    loadFrames();
  } catch (error) {
    console.error('加载movie失败:', error);
  }
};

const loadFrames = async () => {
  try {
    const response = await fetch(`/api/frames?target=${selectedTarget.value}&movie=${selectedMovie.value}`);
    frames.value = await response.json();
    selectedFrame.value = frames.value[0] || '';
    loadImages();
  } catch (error) {
    console.error('加载frame失败:', error);
  }
};

const loadImages = async () => {
  if (!selectedTarget.value || !selectedBuild.value ||
      !selectedMovie.value || !selectedFrame.value) {
    return;
  }

  try {
    // 加载图片A
    imageA.value = `/api/image?target=${selectedTarget.value}&build=${selectedBuild.value}&movie=${selectedMovie.value}&frame=${selectedFrame.value}`;

    // 加载图片B
    imageB.value = `/api/image?target=${selectedTarget.value}&build=${selectedBuild.value}&movie=${selectedMovie.value}&frame=${selectedFrame.value + 1}`;

    // 自动生成差异图
    generateDiff();
  } catch (error) {
    console.error('加载图片失败:', error);
  }
};

const generateDiff = async () => {
  try {
    const response = await fetch('/api/diff', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        targetA: `${selectedTarget.value}/${selectedBuild.value}/${selectedMovie.value}-${selectedFrame.value}.png`,
        targetB: `${selectedTarget.value}/${selectedBuild.value}/${selectedMovie.value}-${selectedFrame.value + 1}.png`,
        threshold: diffThreshold.value
      })
    });

    const result = await response.json();
    diffImage.value = result.diffImageUrl;
    diffStats.value = {
      differentPixels: result.differentPixels,
      percentage: result.percentage
    };
  } catch (error) {
    console.error('生成差异图失败:', error);
  }
};

const prevFrame = () => {
  if (!hasPrevFrame.value) return;

  const currentIndex = frames.value.indexOf(selectedFrame.value);
  selectedFrame.value = frames.value[currentIndex - 1];
  loadImages();
};

const nextFrame = () => {
  if (!hasNextFrame.value) return;

  const currentIndex = frames.value.indexOf(selectedFrame.value);
  selectedFrame.value = frames.value[currentIndex + 1];
  loadImages();
};

// 初始化
onMounted(async () => {
  console.log('开始获取target')
  try {
    targets.value = await $fetch("/api/targets");
    if (targets.value.length > 0) {
      selectedTarget.value = targets.value[0];
      await loadBuilds();
    }
  } catch (error) {
    console.error('初始化失败:', error);
  }
});
</script>

<style>
header{
  text-align: center;
  background: white;
}

.image-comparison-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  max-width: 100%;
}

.control-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 8px;
}

.selectors {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  flex: 1;
}

.selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector select {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
}

.diff-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.diff-button {
  padding: 8px 12px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.diff-button:hover {
  background-color: #357ab8;
}

.three-column-comparison {
  display: flex;
  gap: 10px;
  height: 70vh;
}

.column {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
}

.column-header {
  padding: 10px;
  background-color: #f0f0f0;
  border-bottom: 1px solid #ddd;
}

.column-header h3 {
  margin: 0;
  font-size: 16px;
}

.diff-stats {
  display: flex;
  gap: 15px;
  font-size: 12px;
  margin-top: 5px;
}

.image-wrapper {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  background-color: #f8f8f8;
}

.comparison-image {
  max-width: 100%;
  object-fit: contain;
}

.placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #888;
}

.frame-navigator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.frame-thumbnails {
  display: flex;
  overflow-x: auto;
  gap: 5px;
  flex: 1;
  padding: 5px 0;
}

.frame-thumbnail {
  padding: 5px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  min-width: 30px;
  text-align: center;
}

.frame-thumbnail.active {
  background-color: #4a90e2;
  color: white;
  border-color: #4a90e2;
}
</style>