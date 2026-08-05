<template>
  <SectionPanel title="质量追溯一张图（借鉴兴澄⑧）" icon="🔍">
    <div class="trace-bar">
      <label>熔炼号：</label>
      <input v-model="input" class="trace-input" placeholder="输入熔炼号查询" @keyup.enter="query" />
      <button class="trace-btn" @click="query">查询</button>
      <span class="section-hint" style="margin-left:8px">炉号贯穿全流程，红色=有异常工序</span>
    </div>

    <template v-if="trace.heat_no">
      <div class="stats" style="margin: 1rem 0">
        <StatCard label="炉次信息" :rows="[
          { k: '钢种', v: trace.steel_grade || '-' },
          { k: '班组', v: (trace.team || '-') + '班' },
          { k: '设备', v: trace.equipment || '-' },
          { k: '出钢时刻', v: trace.tap_time ? trace.tap_time.slice(0, 16) : '-' },
        ]" />
      </div>
      <div class="charts">
        <ChartCard title="各工序符合率（红=异常工序）" :full="true">
          <EChart :option="procOption" />
        </ChartCard>
      </div>
      <h3 class="abn-title">异常指标明细（{{ (trace.abnormal || []).length }} 项）</h3>
      <DataTable :columns="abnCols" :rows="trace.abnormal || []" :scroll-x="true" />
    </template>
    <div v-else class="empty">加载中…</div>
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StatCard from '@/components/cards/StatCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const trace = ref({})
const input = ref('')

const procOption = computed(() => {
  const ps = trace.value.processes || []
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: ${p[0].value}%` },
    xAxis: { type: 'category', data: ps.map((x) => x.process) },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{
      type: 'bar',
      data: ps.map((x) => ({
        value: x.rate,
        itemStyle: { color: x.rate < 80 ? '#f87171' : x.rate < 95 ? '#fbbf24' : '#34d399' },
      })),
      itemStyle: { borderRadius: [4, 4, 0, 0] },
      label: { show: true, position: 'top', formatter: '{c}%', color: '#94a3b8', fontSize: 10 },
    }],
  }
})

const abnCols = [
  { key: 'process', title: '工序' },
  { key: 'indicator', title: '指标', mono: true },
  { key: 'std', title: '标准' },
  { key: 'actual', title: '实绩' },
]

async function query() {
  if (!input.value) return
  try { trace.value = await qualityApi.heatTrace(input.value) } catch (e) { console.error(e) }
}

onMounted(async () => {
  try {
    const t = await qualityApi.heatTrace()
    trace.value = t
    input.value = t.heat_no || ''
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.trace-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 0.5rem; }
.trace-input { background: var(--glass2); border: 1px solid var(--border); border-radius: 8px; color: var(--text); padding: 6px 10px; font-family: 'Cascadia Code', monospace; width: 220px; }
.trace-btn { background: var(--accent); color: var(--bg); border: none; border-radius: 8px; padding: 6px 16px; cursor: pointer; font-weight: 600; }
.trace-btn:hover { background: var(--accent2); }
.abn-title { margin: 1rem 0 0.5rem; color: var(--accent2); font-size: 1rem; }
</style>
