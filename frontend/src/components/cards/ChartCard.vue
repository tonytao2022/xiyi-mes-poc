<template>
  <div class="chart" :class="[{ visible, full }]" ref="elRef">
    <h3 v-if="title">{{ title }}</h3>
    <slot />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'

const props = defineProps({
  title: String,
  full: Boolean,
})

const visible = ref(false)
const elRef = ref(null)
useIntersectionObserver(elRef, ([e]) => {
  if (e.isIntersecting) visible.value = true
}, { threshold: 0.1 })
</script>
