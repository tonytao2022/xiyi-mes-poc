<template>
  <SectionPanel title="加热工艺温度对比（对标 demo S3）" icon="🔥">
    <div class="stats">
      <StatCard v-for="(l, i) in (heating.labels || [])" :key="i" :label="l + '(℃)'" :rows="[
        { k: '均值', v: heating.avg?.[i] ?? '-' },
        { k: '范围', v: (heating.min?.[i] ?? '-') + '~' + (heating.max?.[i] ?? '-') },
      ]" />
    </div>
    <div class="charts">
      <ChartCard title="各段温度 Min/Mean/Max" :full="true">
        <EChart :option="heatingOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="轧制温度时序（对标 demo S4）" icon="📈">
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="rollingOption" height="340px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="命中率分布（对标 demo S7）" icon="🎯">
    <div class="charts">
      <ChartCard title="A/B/C 命中率">
        <EChart :option="hitOption" />
      </ChartCard>
    </div>
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import StatCard from '@/components/cards/StatCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const heating = ref({ labels: [], min: [], avg: [], max: [] })
const rolling = ref({ times: [], start: [], finish: [], laying: [] })
const hit = ref({ labels: [], full: [], miss: [] })

const heatingOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['Min', 'Mean', 'Max'] },
  xAxis: { type: 'category', data: heating.value.labels },
  yAxis: { type: 'value', name: '℃' },
  series: [
    { name: 'Min', type: 'bar', data: heating.value.min, itemStyle: { color: '#f87171', borderRadius: [4, 4, 0, 0] } },
    { name: 'Mean', type: 'bar', data: heating.value.avg, itemStyle: { color: '#60a5fa', borderRadius: [4, 4, 0, 0] } },
    { name: 'Max', type: 'bar', data: heating.value.max, itemStyle: { color: '#34d399', borderRadius: [4, 4, 0, 0] } },
  ],
}))

const rollingOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['开轧温度', '终轧温度', '吐丝温度'] },
  xAxis: { type: 'category', data: rolling.value.times, axisLabel: { rotate: 45, fontSize: 9 } },
  yAxis: { type: 'value', name: '℃' },
  series: [
    { name: '开轧温度', type: 'line', data: rolling.value.start, itemStyle: { color: '#f87171' }, smooth: true },
    { name: '终轧温度', type: 'line', data: rolling.value.finish, itemStyle: { color: '#fbbf24' }, smooth: true },
    { name: '吐丝温度', type: 'line', data: rolling.value.laying, itemStyle: { color: '#34d399' }, smooth: true },
  ],
}))

const hitOption = computed(() => {
  const full = hit.value.full || []
  const miss = hit.value.miss || []
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '65%'],
      data: [
        { name: 'A级100%命中', value: full[0] }, { name: 'A级<100%', value: miss[0] },
        { name: 'B级100%命中', value: full[1] }, { name: 'B级<100%', value: miss[1] },
        { name: 'C级100%命中', value: full[2] }, { name: 'C级<100%', value: miss[2] },
      ].filter((d) => d.value > 0),
    }],
  }
})

onMounted(async () => {
  try {
    const [h, r, hd] = await Promise.all([
      qualityApi.heatingTemperature(),
      qualityApi.rollingTemperatureSeries(),
      qualityApi.hitRateDistribution(),
    ])
    heating.value = h
    rolling.value = r
    hit.value = hd
  } catch (e) { console.error(e) }
})
</script>
