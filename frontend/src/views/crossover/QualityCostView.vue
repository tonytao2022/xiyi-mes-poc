<template>
  <SectionPanel title="质量 × 成本 交叉分析" icon="🔗">
    <p class="section-hint">
      分析思路：质量超标准/未命中如何转化为成本浪费，揭示质量与成本的冲突与权衡。
      核心问题--"质量不好值多少钱"、"为省成本牺牲质量是否值得"。
    </p>
    <InsightBlock :items="data.items || []" />
    <template v-for="(it, i) in (data.items || [])" :key="i">
      <div v-if="it.chart" class="charts">
        <ChartCard :title="it.chart.title" :full="it.chart.type === 'scatter'">
          <EChart :option="chartOption(it.chart)" :height="it.chart.type === 'scatter' ? '380px' : '320px'" />
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
  if (chart.type === 'bar') {
    return {
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: chart.labels, axisLabel: { rotate: 30, fontSize: 9 } },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: chart.values, itemStyle: { borderRadius: [4, 4, 0, 0] } }],
    }
  }
  if (chart.type === 'scatter') {
    const lbl = chart.labels || []
    return {
      tooltip: { formatter: (p) => `${lbl[p.dataIndex] ? lbl[p.dataIndex] + ': ' : ''}(${p.data[0]}, ${p.data[1]})` },
      xAxis: { type: 'value', name: chart.xName || '', scale: true },
      yAxis: { type: 'value', name: chart.yName || '', scale: true },
      series: [{ type: 'scatter', data: chart.points, symbolSize: 10, itemStyle: { color: 'rgba(96,165,250,0.7)' } }],
    }
  }
  return {}
}

onMounted(async () => {
  try { data.value = await crossoverApi.qualityCost() } catch (e) { console.error(e) }
})
</script>
