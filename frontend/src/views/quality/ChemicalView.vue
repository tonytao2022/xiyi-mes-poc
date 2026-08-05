<template>
  <SectionPanel title="化学成分分析（SWRCH22A）" icon="🧪">
    <div class="charts">
      <ChartCard title="各元素含量均值（质量分数）">
        <EChart :option="chemBarOption" height="340px" />
      </ChartCard>
      <ChartCard title="各元素雷达（归一化）">
        <EChart :option="chemRadarOption" height="340px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="元素统计卡（均值/标准差/范围，对标 demo S2）" icon="📊">
    <DataTable :columns="chemCols" :rows="chemStats" />
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const chem = ref({ labels: [], values: [] })
const chemStats = ref([])

const chemBarOption = computed(() => {
  const labels = chem.value.labels || []
  const values = chem.value.values || []
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: ${(p[0].value * 100).toFixed(3)}%` },
    grid: { left: '12%' },
    xAxis: { type: 'value', axisLabel: { formatter: (v) => (v * 100).toFixed(1) + '%' } },
    yAxis: { type: 'category', data: labels },
    series: [{ type: 'bar', data: values, itemStyle: { color: '#a78bfa', borderRadius: [0, 4, 4, 0] } }],
  }
})

const chemRadarOption = computed(() => {
  const labels = chem.value.labels || []
  const values = chem.value.values || []
  const maxV = Math.max(...values, 0.001)
  return {
    tooltip: {},
    radar: { indicator: labels.map((l) => ({ name: l, max: maxV * 1.2 })) },
    series: [{ type: 'radar', data: [{ value: values, name: '均值' }], areaStyle: { opacity: 0.2 } }],
  }
})

const chemCols = [
  { key: 'element', title: '元素', mono: true },
  { key: 'avg', title: '均值(%)', format: (v) => (v * 100).toFixed(3) },
  { key: 'std', title: '标准差', format: (v) => (v * 100).toFixed(4) },
  { key: 'min', title: '最小', format: (v) => (v * 100).toFixed(3) },
  { key: 'max', title: '最大', format: (v) => (v * 100).toFixed(3) },
]

onMounted(async () => {
  try {
    const [c, s] = await Promise.all([qualityApi.chemicalRadar(), qualityApi.chemicalStats()])
    chem.value = c
    chemStats.value = s
  } catch (e) { console.error(e) }
})
</script>
