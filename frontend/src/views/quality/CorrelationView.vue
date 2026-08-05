<template>
  <SectionPanel title="成分-性能相关性（对标 demo S5）" icon="🔗">
    <p class="section-hint">Pearson 相关系数 r，按 |r| 排序。绿=正相关，红=负相关。|r|≥0.5 为强相关。</p>
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="corrOption" height="380px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="成分-性能散点（对标 demo S6）" icon="📍">
    <div class="scatter-ctrl">
      <label>X（成分）：
        <select v-model="x">
          <option v-for="e in ['C','Si','Mn','P','S']" :key="e" :value="e">{{ e }}</option>
        </select>
      </label>
      <label>Y（性能）：
        <select v-model="y">
          <option value="yield_strength">屈服强度</option>
          <option value="tensile_strength">抗拉强度</option>
          <option value="elongation">断后伸长率</option>
        </select>
      </label>
      <span class="section-hint">样本 {{ sc.n }} 个</span>
    </div>
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="scatterOption" height="380px" />
      </ChartCard>
    </div>
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const corr = ref([])
const sc = ref({ points: [], x: 'C', y: 'yield_strength', n: 0 })
const x = ref('C')
const y = ref('yield_strength')

const yLabel = { yield_strength: '屈服强度', tensile_strength: '抗拉强度', elongation: '断后伸长率' }

const corrOption = computed(() => {
  const d = corr.value.slice().reverse()
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>r = ${p[0].value}` },
    grid: { left: '28%' },
    xAxis: { type: 'value', min: -1, max: 1, axisLabel: { formatter: '{value}' } },
    yAxis: { type: 'category', data: d.map((p) => p.pair) },
    series: [{
      type: 'bar',
      data: d.map((p) => ({ value: p.r, itemStyle: { color: p.r >= 0 ? '#34d399' : '#f87171' } })),
      itemStyle: { borderRadius: [0, 4, 4, 0] },
    }],
  }
})

const scatterOption = computed(() => ({
  tooltip: { formatter: (p) => `${x.value}: ${p.data[0]}<br/>${yLabel[y.value] || y.value}: ${p.data[1]}` },
  xAxis: { type: 'value', name: x.value, scale: true },
  yAxis: { type: 'value', name: yLabel[y.value] || y.value, scale: true },
  series: [{ type: 'scatter', data: sc.value.points, symbolSize: 6, itemStyle: { color: 'rgba(96,165,250,0.6)' } }],
}))

async function loadScatter() {
  try { sc.value = await qualityApi.scatter(x.value, y.value) } catch (e) { console.error(e) }
}

onMounted(async () => {
  try {
    corr.value = await qualityApi.correlation()
    await loadScatter()
  } catch (e) { console.error(e) }
})
watch([x, y], loadScatter)
</script>

<style scoped>
.scatter-ctrl { display: flex; align-items: center; gap: 1.2rem; margin-bottom: 1rem; flex-wrap: wrap; }
.scatter-ctrl label { color: var(--dim); font-size: 0.85rem; }
.scatter-ctrl select {
  background: var(--glass2); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); padding: 4px 8px; margin-left: 4px;
}
</style>
