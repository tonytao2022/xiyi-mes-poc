<template>
  <section :id="id" class="sec" :class="{ visible }" ref="elRef">
    <h2 class="sec-title">
      <span v-if="icon" class="ic">{{ icon }}</span>
      <slot name="title">{{ title }}</slot>
    </h2>
    <slot />
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { useIntersectionObserver } from '@vueuse/core'

const props = defineProps({
  id: String,
  title: String,
  icon: String,
})

const visible = ref(false)
const elRef = ref(null)
useIntersectionObserver(elRef, ([e]) => {
  if (e.isIntersecting) visible.value = true
}, { threshold: 0.05 })
</script>
