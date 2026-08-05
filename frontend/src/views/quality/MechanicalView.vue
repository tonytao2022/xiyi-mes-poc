<template>
  <SectionPanel title="力学性能分布（SWRCH22A）" icon="💪">
    <div class="stats">
      <StatCard v-for="(s, i) in mechStats" :key="i" :label="s.name" :rows="[
        { k: '均值', v: s.avg },
        { k: '标准差', v: s.std },
      ]" />
    </div>
    <div class="charts">
      <ChartCard title="Min / Mean / Max 对比" :full="true">
        <EChart :option="mechDistOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="分布直方图（对标 demo S1）" icon="📈">
    <div class="hist-ctrl">
      <label>指标：
        <select v-model="sel">
          <option v-for="k in Object.keys(hist)" :key="k">{{ k }}</option>
        </select>
      </label>
      <span class="section-hint">范围 {{ cur.min }}~{{ cur.max }}，样本 {{ cur.n }}</span>
    </div>
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="histOption" />
      </ChartCard>
    </div>
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StatCard from '@/components/cards/StatCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const mechDist = ref({ labels: [], series: { min: [], avg: [], max: [] }, std: {} })
const mechIdx = [0, 1, 2, 4]
const hist = ref({})
const sel = ref('')

const mechStats = computed(() => {
  const names = ['屈服强度', '抗拉强度', '断后伸长率', '屈强比']
  return names.map((n) => ({
    name: n,
    avg: mechDist.value.series?.avg?.[mechDist.value.labels?.indexOf(n)] ?? '-',
    std: mechDist.value.std?.[n] ?? '-',
  }))
})

const cur = computed(() => hist.value[sel.value] || { bins: [], min: 0, max: 0, n: 0 })

const mechDistOption = computed(() => {
  const labels = mechIdx.map((i) => mechDist.value.labels[i]).filter(Boolean)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['Min', 'Mean', 'Max'] },
    xAxis: { type: 'category', data: labels },
    yAxis: { type: 'value' },
    series: [
      { name: 'Min', type: 'bar', data: mechIdx.map((i) => mechDist.value.series.min?.[i] || 0), itemStyle: { color: '#f87171', borderRadius: [4, 4, 0, 0] } },
      { name: 'Mean', type: 'bar', data: mechIdx.map((i) => mechDist.value.series.avg?.[i] || 0), itemStyle: { color: '#60a5fa', borderRadius: [4, 4, 0, 0] } },
      { name: 'Max', type: 'bar', data: mechIdx.map((i) => mechDist.value.series.max?.[i] || 0), itemStyle: { color: '#34d399', borderRadius: [4, 4, 0, 0] } },
    ],
  }
})

const histOption = computed(() => {
  const h = cur.value
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${h.bins[p[0].dataIndex].start}~${h.bins[p[0].dataIndex].end}: ${p[0].value} 个` },
    grid: { left: '8%' },
    xAxis: { type: 'category', data: h.bins.map((b) => String(b.start)) },
    yAxis: { type: 'value', name: '频次' },
    series: [{ type: 'bar', data: h.bins.map((b) => b.count), itemStyle: { color: '#60a5fa', borderRadius: [4, 4, 0, 0] } }],
  }
})

onMounted(async () => {
  try {
    const [d, h] = await Promise.all([qualityApi.mechanicalDistribution(), qualityApi.mechanicalHistogram()])
    mechDist.value = d
    hist.value = h
    sel.value = Object.keys(h)[0] || ''
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.hist-ctrl { margin-bottom: 0.5rem; display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.hist-ctrl label { color: var(--dim); font-size: 0.85rem; }
.hist-ctrl select { background: var(--glass2); border: 1px solid var(--border); border-radius: 6px; color: var(--text); padding: 4px 8px; }
</style>
