<template>
  <SubTabs :tabs="tabs" />
  <RouterView />
</template>

<script setup>
import SubTabs from '@/components/layout/SubTabs.vue'

const tabs = [
  { to: '/crossover/quality-cost', label: '质量 × 成本' },
  { to: '/crossover/quality-efficiency', label: '质量 × 效率' },
  { to: '/crossover/cost-efficiency', label: '成本 × 效率' },
]
</script>
