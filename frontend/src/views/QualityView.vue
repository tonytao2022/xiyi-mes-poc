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
    <DataTable :columns="complianceCols" :rows="complianceRows" :scroll-x="true" />
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

  <SectionPanel id="q-mech" title="力学性能分布（SWRCH22A）" icon="💪">
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

  <SectionPanel id="q-chem" title="化学成分分析（SWRCH22A）" icon="🧪">
    <div class="charts">
      <ChartCard title="各元素含量均值（质量分数）" :full="true">
        <EChart :option="chemOption" height="360px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="q-deviation" title="单件物料偏差 z-score（对应 PDF 单块报告）" icon="🎯">
    <p class="section-hint">
      以 SWRCH22A 整体为基线，计算单件物料各指标 z-score。评级：|z|≥3 严重，≥2 偏离，&lt;2 正常。
      试批号：<span class="mono">{{ deviation.sample_lot_no || '-' }}</span>
    </p>
    <div class="stats" style="margin-bottom: 1rem">
      <StatCard label="严重" :rows="[{ k: '数量', v: deviation.summary?.严重 || 0, cls: 'pass-bad' }]" />
      <StatCard label="偏离" :rows="[{ k: '数量', v: deviation.summary?.偏离 || 0, cls: 'pass-warn' }]" />
      <StatCard label="正常" :rows="[{ k: '数量', v: deviation.summary?.正常 || 0, cls: 'pass-good' }]" />
    </div>
    <DataTable :columns="deviationCols" :rows="deviation.items || []" :scroll-x="true" />
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import KpiCard from '@/components/cards/KpiCard.vue'
import StatCard from '@/components/cards/StatCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const compliance = ref([])
const team = ref([])
const shortboard = ref([])
const mechDist = ref({ labels: [], series: { min: [], avg: [], max: [] }, std: {} })
const chemRadar = ref({ labels: [], values: [] })
const deviation = ref({ sample_lot_no: null, items: [], summary: {} })

const overallRate = computed(() => (compliance.value.find((x) => x.process === '合计') || {}).rate || 0)
const processKpis = computed(() => compliance.value.filter((x) => x.process !== '合计'))
const complianceRows = computed(() => compliance.value)

const complianceCols = [
  { key: 'process', title: '工序' },
  { key: 'judged', title: '判定数' },
  { key: 'hit', title: '命中数' },
  { key: 'rate', title: '符合率(%)', rate: true },
  { key: 'heats', title: '炉数' },
  { key: 'indicators', title: '指标数' },
]
const iconFor = (p) => ({ 转炉: '🔥', 精炼: '⚗️', 真空: '🌀', 板坯: '📦', 方坯: '📦', 合金: '🔩' }[p] || '📊')

// 力学分布柱状图：取数量级相近的指标（屈服/抗拉/伸长率/断面收缩率），跳过屈强比
const mechIdx = [0, 1, 2, 4]
const mechStats = computed(() => {
  const names = ['屈服强度', '抗拉强度', '断后伸长率', '屈强比']
  return names.map((n) => ({ name: n, avg: mechDist.value.series?.avg?.[mechDist.value.labels?.indexOf(n)] ?? '-', std: mechDist.value.std?.[n] ?? '-' }))
})
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

const chemOption = computed(() => {
  const labels = chemRadar.value.labels || []
  const values = chemRadar.value.values || []
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: ${(p[0].value * 100).toFixed(3)}%` },
    grid: { left: '12%' },
    xAxis: { type: 'value', axisLabel: { formatter: (v) => (v * 100).toFixed(1) + '%' } },
    yAxis: { type: 'category', data: labels },
    series: [{ type: 'bar', data: values, itemStyle: { color: '#a78bfa', borderRadius: [0, 4, 4, 0] } }],
  }
})

const deviationCols = [
  { key: 'name', title: '指标' },
  { key: 'actual', title: '实测', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'avg', title: '基线均值', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'std', title: '标准差', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'z', title: 'z-score', format: (v) => (v == null ? '-' : (v >= 0 ? '+' : '') + Number(v).toFixed(2)) },
  { key: 'grade', title: '评级', format: (v) => v || '-' },
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
    const [c, t, s, md, cr, dv] = await Promise.all([
      qualityApi.complianceOverview(),
      qualityApi.complianceByDimension('team'),
      qualityApi.indicatorRanking(null, 'asc'),
      qualityApi.mechanicalDistribution(),
      qualityApi.chemicalRadar(),
      qualityApi.singleDeviation(),
    ])
    compliance.value = c
    team.value = t
    shortboard.value = s
    mechDist.value = md
    chemRadar.value = cr
    deviation.value = dv
  } catch (e) {
    console.error(e)
  }
})
</script>
