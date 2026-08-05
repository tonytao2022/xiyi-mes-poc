<template>
  <SectionPanel v-if="data.quality_cost" title="质量 × 成本 交汇" icon="🔗">
    <p class="section-hint">质量超标准/未命中导致的成本浪费，揭示质量与成本的冲突与权衡。</p>
    <InsightBlock :items="data.quality_cost.items" />
    <template v-for="(it, i) in data.quality_cost.items" :key="i">
      <div v-if="it.chart" class="charts">
        <ChartCard :title="it.chart.title" :full="it.chart.type === 'scatter'">
          <EChart :option="chartOption(it.chart)" :height="it.chart.type === 'scatter' ? '360px' : '300px'" />
        </ChartCard>
      </div>
    </template>
  </SectionPanel>

  <SectionPanel v-if="data.quality_efficiency" title="质量 × 效率 交汇" icon="⏱️">
    <p class="section-hint">效率与质量的关联：一次成功率、工艺时长-质量关系，找质量不降的最短时长。</p>
    <InsightBlock :items="data.quality_efficiency.items" />
    <template v-for="(it, i) in data.quality_efficiency.items" :key="i">
      <div v-if="it.chart" class="charts">
        <ChartCard :title="it.chart.title" :full="true">
          <EChart :option="chartOption(it.chart)" height="300px" />
        </ChartCard>
      </div>
    </template>
  </SectionPanel>

  <SectionPanel v-if="data.cost_efficiency" title="成本 × 效率 交汇" icon="💰">
    <p class="section-hint">效率低导致的成本增加：时长-能耗、超时损失，时间就是成本。</p>
    <InsightBlock :items="data.cost_efficiency.items" />
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
    return {
      tooltip: { formatter: (p) => `低端料占比 ${p.data[0]}% / 合金符合率 ${p.data[1]}%` },
      xAxis: { type: 'value', name: '低端料占比%', scale: true },
      yAxis: { type: 'value', name: '合金符合率%', max: 100, scale: true },
      series: [{ type: 'scatter', data: chart.points, symbolSize: 8, itemStyle: { color: 'rgba(96,165,250,0.7)' } }],
    }
  }
  return {}
}

onMounted(async () => {
  try { data.value = await crossoverApi.all() } catch (e) { console.error(e) }
})
</script>
