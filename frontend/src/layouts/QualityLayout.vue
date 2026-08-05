<template>
  <SubTabs :tabs="tabs" />
  <RouterView />
</template>

<script setup>
import SubTabs from '@/components/layout/SubTabs.vue'

const tabs = [
  { to: '/quality/compliance', label: '工艺符合率' },
  { to: '/quality/indicators', label: '指标分析' },
  { to: '/quality/mechanical', label: '力学性能' },
  { to: '/quality/chemical', label: '化学成分' },
  { to: '/quality/deviation', label: '单件偏差' },
  { to: '/quality/dimension', label: '尺寸检验' },
  { to: '/quality/correlation', label: '相关性' },
  { to: '/quality/rolling', label: '轧钢工艺', badge: '新' },
  { to: '/quality/evaluate', label: '质量评价', badge: '新' },
  { to: '/quality/trace', label: '质量追溯', badge: '新' },
]
</script>
