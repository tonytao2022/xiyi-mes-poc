<template>
  <div class="stat">
    <div class="lbl">{{ label }}</div>
    <div class="row" v-for="r in rows" :key="r.k">
      <span>{{ r.k }}</span>
      <span class="v" :class="r.cls">{{ r.v }}</span>
    </div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  label: String,
  rows: { type: Array, default: () => [] },
})
</script>
