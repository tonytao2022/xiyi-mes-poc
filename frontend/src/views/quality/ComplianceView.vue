<template>
  <div class="kpi-grid">
    <KpiCard icon="✅" :value="overallRate" label="总符合率" suffix="%" :decimals="2" :delay="0.1" />
    <KpiCard
      v-for="(p, i) in processKpis"
      :key="p.process"
      :icon="iconFor(p.process)"
      :value="p.rate"
      :label="p.process"
      suffix="%"
      :decimals="2"
      :delay="0.15 + i * 0.05"
    />
  </div>

  <SectionPanel id="q-compliance" title="各工序工艺符合率" icon="📊">
    <p class="section-hint">
      口径：judge 非空为判定，judge=1 为命中。板坯/方坯与客户汇总完全吻合；转炉/精炼/真空因汇总按试样级展开，口径待客户确认。
    </p>
    <DataTable :columns="complianceCols" :rows="compliance" :scroll-x="true" />
  </SectionPanel>

  <SectionPanel id="q-team" title="班组符合率对比" icon="👥">
    <div class="charts">
      <ChartCard title="班组炉数与符合率（双轴）">
        <EChart :option="teamOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="q-shortboard" title="指标合格率短板 Top15" icon="⚠️">
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="shortboardOption" height="460px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="q-grade-matrix" title="钢种合格率矩阵（对标 demo S6）" icon="🔲">
    <div class="m-ctrl">
      <label>工序：
        <select v-model="matrixProcess" @change="loadMatrix">
          <option v-for="p in ['转炉','精炼','真空','板坯','方坯','合金']" :key="p">{{ p }}</option>
        </select>
      </label>
    </div>
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="gradeMatrixOption" height="400px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="q-route" title="工艺路径符合率（对标 demo S5）" icon="🛤️">
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="routeOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="q-insights" title="质量智能洞察（问题识别）" icon="💡">
    <p class="section-hint">系统自动识别质量短板、合金超标准、低分炉次、力学离群等问题。</p>
    <InsightBlock :items="insights.items || []" />
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import KpiCard from '@/components/cards/KpiCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import InsightBlock from '@/components/cards/InsightBlock.vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const compliance = ref([])
const team = ref([])
const shortboard = ref([])
const insights = ref({})
const gradeMatrix = ref({ grades: [], indicators: [], matrix: {} })
const matrixProcess = ref('板坯')
const routeData = ref([])

const gradeMatrixOption = computed(() => {
  const m = gradeMatrix.value
  const data = []
  m.grades.forEach((g, gi) => {
    m.indicators.forEach((ind, ii) => { data.push([ii, gi, m.matrix[g]?.[ind] ?? 0]) })
  })
  return {
    tooltip: { position: 'top', formatter: (p) => `${m.grades[p.value[1]]} · ${m.indicators[p.value[0]]}: ${p.value[2]}%` },
    grid: { left: '12%', right: '5%', bottom: '25%' },
    xAxis: { type: 'category', data: m.indicators, axisLabel: { rotate: 45, fontSize: 9 } },
    yAxis: { type: 'category', data: m.grades },
    visualMap: { min: 0, max: 100, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#f87171', '#fbbf24', '#34d399'] } },
    series: [{ type: 'heatmap', data, label: { show: true, formatter: (p) => p.value[2] } }],
  }
})
const routeOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: ${p[0].value}%` },
  xAxis: { type: 'category', data: routeData.value.map((r) => r.key) },
  yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
  series: [{ type: 'bar', data: routeData.value.map((r) => r.rate), itemStyle: { borderRadius: [4, 4, 0, 0] } }],
}))
async function loadMatrix() { try { gradeMatrix.value = await qualityApi.complianceByGrade(matrixProcess.value) } catch (e) { console.error(e) } }

const overallRate = computed(() => (compliance.value.find((x) => x.process === '合计') || {}).rate || 0)
const processKpis = computed(() => compliance.value.filter((x) => x.process !== '合计'))
const iconFor = (p) => ({ 转炉: '🔥', 精炼: '⚗️', 真空: '🌀', 板坯: '📦', 方坯: '📦', 合金: '🔩' }[p] || '📊')

const complianceCols = [
  { key: 'process', title: '工序' },
  { key: 'judged', title: '判定数' },
  { key: 'hit', title: '命中数' },
  { key: 'rate', title: '符合率(%)', rate: true },
  { key: 'heats', title: '炉数' },
  { key: 'indicators', title: '指标数' },
]

const teamOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['炉数', '符合率'] },
  xAxis: { type: 'category', data: team.value.map((t) => t.team + '班') },
  yAxis: [
    { type: 'value', name: '炉数' },
    { type: 'value', name: '符合率%', max: 100, axisLabel: { formatter: '{value}%' } },
  ],
  series: [
    { name: '炉数', type: 'bar', data: team.value.map((t) => t.heats), itemStyle: { borderRadius: [4, 4, 0, 0] } },
    { name: '符合率', type: 'line', yAxisIndex: 1, data: team.value.map((t) => t.rate), itemStyle: { color: '#fbbf24' } },
  ],
}))

const shortboardOption = computed(() => {
  const d = shortboard.value.slice().reverse()
  return {
    tooltip: { trigger: 'axis', formatter: (p) => { const i = p[0].dataIndex; return `${d[i].name}<br/>${d[i].rate}% (${d[i].process} · 判定${d[i].judged})` } },
    grid: { left: '24%' },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: d.map((s) => s.name) },
    series: [{ type: 'bar', data: d.map((s) => ({ value: s.rate, itemStyle: { color: s.rate >= 95 ? '#34d399' : s.rate >= 80 ? '#fbbf24' : '#f87171' } })), itemStyle: { borderRadius: [0, 4, 4, 0] } }],
  }
})

onMounted(async () => {
  try {
    const [c, t, s, ins, rt] = await Promise.all([
      qualityApi.complianceOverview(),
      qualityApi.complianceByDimension('team'),
      qualityApi.indicatorRanking(null, 'asc'),
      qualityApi.insights(),
      qualityApi.complianceByDimension('process_route'),
    ])
    compliance.value = c
    team.value = t
    shortboard.value = s
    insights.value = ins
    routeData.value = rt
    await loadMatrix()
  } catch (e) { console.error(e) }
})
</script>
