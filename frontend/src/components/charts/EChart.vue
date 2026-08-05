<template>
  <div ref="elRef" class="echart" :style="{ height }"></div>
</template>

<script setup>
import { inject, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import echarts from '@/utils/echarts'
import { useLazyChart } from '@/composables/useLazyChart'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' },
  theme: { type: String, default: '' },
})

const emit = defineEmits(['chartClick'])
const injectTheme = inject('echartTheme', 'mes-dark')
const actualTheme = props.theme || injectTheme

const elRef = ref(null)
const chartRef = shallowRef(null)

const init = () => {
  if (chartRef.value || !elRef.value) return
  chartRef.value = echarts.init(elRef.value, actualTheme)
  chartRef.value.setOption(props.option)
  chartRef.value.on('click', (params) => emit('chartClick', params))
}

useLazyChart(elRef, init)

watch(
  () => props.option,
  (o) => {
    if (chartRef.value) chartRef.value.setOption(o, true)
    else init()
  },
  { deep: true },
)

const onResize = () => chartRef.value?.resize()
window.addEventListener('resize', onResize)

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chartRef.value?.dispose()
})
</script>

<style scoped>
.echart {
  width: 100%;
}
</style>
