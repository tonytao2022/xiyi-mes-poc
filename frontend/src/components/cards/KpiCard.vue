<template>
  <div class="kpi" :style="{ animationDelay: delay + 's' }">
    <div class="icon">{{ icon }}</div>
    <div class="val">{{ formatted }}</div>
    <div class="lbl">{{ label }}</div>
  </div>
</template>

<script setup>
import { computed, toRef } from 'vue'
import { useCountUp } from '@/composables/useCountUp'

const props = defineProps({
  icon: String,
  value: [Number, String],
  label: String,
  suffix: { type: String, default: '' },
  decimals: { type: Number, default: 0 },
  delay: { type: Number, default: 0 },
})

const num = toRef(props, 'value')
const { display } = useCountUp(num)
const formatted = computed(() => {
  const v = Number(display.value) || 0
  return v.toLocaleString('zh-CN', { maximumFractionDigits: props.decimals }) + props.suffix
})
</script>
