<template>
  <SectionPanel title="质量 × 效率 交叉分析" icon="⏱️">
    <p class="section-hint">
      分析思路：效率与质量的关联，找"质量不降的最短时长"，一次成功省时省质。
      核心问题--"快会不会伤质量"、"多长时间够用"。
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
    xAxis: { type: 'category', data: chart.labels },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{ type: 'bar', data: chart.values, itemStyle: { borderRadius: [4, 4, 0, 0], color: '#60a5fa' } }],
  }
}

onMounted(async () => {
  try { data.value = await crossoverApi.qualityEfficiency() } catch (e) { console.error(e) }
})
</script>
