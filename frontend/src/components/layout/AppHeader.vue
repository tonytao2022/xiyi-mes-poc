<template>
  <header class="nav">
    <div class="logo">{{ title }}</div>
    <nav>
      <RouterLink v-for="n in navs" :key="n.to" :to="n.to">{{ n.label }}</RouterLink>
    </nav>
  </header>
</template>

<script setup>
defineProps({
  title: { type: String, default: 'MES · 协同分析' },
  navs: { type: Array, default: () => [] },
})
</script>
