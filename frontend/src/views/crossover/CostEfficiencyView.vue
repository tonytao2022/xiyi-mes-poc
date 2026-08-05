<template>
  <SectionPanel title="成本 × 效率 交叉分析" icon="💰">
    <p class="section-hint">
      分析思路：效率低导致的成本增加，时间就是成本。
      核心问题--"慢一分钟值多少钱"、"超时和等待的代价"。
    </p>
    <InsightBlock :items="data.items || []" />
    <template v-for="(it, i) in (data.items || [])" :key="i">
      <div v-if="it.chart" class="charts">
        <ChartCard :title="it.chart.title" :full="true">
          <EChart :option="chartOption(it.chart)" height="320px" />
        </ChartCard>
      </div>
    </template>
  </SectionPanel>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import InsightBlock from '@/components/cards/InsightBlock.vue'
import EChart from '@/components/charts/EChart.vue'
import { crossoverApi } from '@/api/modules'

const data = ref({})

function chartOption(chart) {
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: chart.labels, axisLabel: { rotate: 30, fontSize: 9 } },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: chart.values, itemStyle: { borderRadius: [4, 4, 0, 0], color: '#a78bfa' } }],
  }
}

onMounted(async () => {
  try { data.value = await crossoverApi.costEfficiency() } catch (e) { console.error(e) }
})
</script>
