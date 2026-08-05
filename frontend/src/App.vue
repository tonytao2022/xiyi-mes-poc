<template>
  <!-- v2 新架构：独立渲染，不套暗色框架 -->
  <RouterView v-if="isV2" />
  <!-- 旧架构：暗色玻璃拟态框架 -->
  <template v-else>
    <ParticleBackground />
    <AppHeader title="MES · 工艺质量·成本·效率协同分析" :navs="navs" />
    <main class="main">
      <RouterView />
    </main>
  </template>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import ParticleBackground from '@/components/layout/ParticleBackground.vue'

const route = useRoute()
const isV2 = computed(() => route.path.startsWith('/v2'))

const navs = [
  { to: '/v2', label: '新架构' },
  { to: '/', label: '首页' },
  { to: '/quality', label: '质量' },
  { to: '/cost', label: '成本' },
  { to: '/efficiency', label: '效率' },
  { to: '/crossover', label: '双维度交叉' },
  { to: '/comprehensive', label: '综合成本' },
  { to: '/simulation', label: '模型模拟' },
  { to: '/overview', label: '综合' },
]
</script>
