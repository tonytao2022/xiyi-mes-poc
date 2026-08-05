<template>
  <div class="kpi-grid">
    <KpiCard icon="🔩" :value="scrap.steel_grade_count" label="钢种数" :delay="0.1" />
    <KpiCard icon="♻️" :value="scrap.total_weight" label="废钢总量(吨)" :delay="0.2" />
    <KpiCard icon="🔥" :value="scrap.total_heats" label="总炉数" :delay="0.3" />
    <KpiCard icon="⚙️" :value="alloy.length" label="合金种类" :delay="0.4" />
  </div>

  <SectionPanel id="c-scrap" title="废钢料型结构" icon="♻️">
    <div class="charts">
      <ChartCard title="各料型用量(吨)">
        <EChart :option="scrapTypeOption" />
      </ChartCard>
      <ChartCard title="料型占比">
        <EChart :option="scrapPieOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="c-grade" title="钢种废钢用量 Top10" icon="📦">
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="gradeOption" height="380px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="c-matrix" title="钢种料型配比矩阵（对标 demo S3）" icon="🔲">
    <p class="section-hint">Top 钢种 × 料型 配比(%)对比。</p>
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="matrixOption" height="380px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="c-alloy" title="合金投入统计（炉次级）" icon="⚙️">
    <p class="section-hint">废钢为钢种级配比，合金为炉次级加入量；两者粒度不同，成本看板分层呈现。</p>
    <div class="charts">
      <ChartCard title="使用频率 Top10（对标 demo S4）">
        <EChart :option="alloyFreqOption" height="340px" />
      </ChartCard>
      <ChartCard title="加入量均值 Top10">
        <EChart :option="alloyAvgOption" height="340px" />
      </ChartCard>
    </div>
    <DataTable :columns="alloyCols" :rows="alloy" :scroll-x="true" />
  </SectionPanel>

  <SectionPanel id="c-insights" title="成本智能洞察（问题识别）" icon="💡">
    <p class="section-hint">系统自动识别料型集中度、高价合金、富裕损失、零用料型等成本问题。</p>
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
import { costApi } from '@/api/modules'

const scrap = ref({ steel_grade_count: 0, total_weight: 0, total_heats: 0, types: [] })
const scrapByGrade = ref([])
const alloy = ref([])
const matrix = ref({ grades: [], types: [], matrix: {} })
const insights = ref({})

const fmtTon = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })

const scrapTypeOption = computed(() => {
  const t = (scrap.value.types || []).slice().reverse()
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>${fmtTon(p[0].value)} 吨` },
    grid: { left: '22%' },
    xAxis: { type: 'value', axisLabel: { formatter: (v) => (v / 1000).toFixed(0) + 'k' } },
    yAxis: { type: 'category', data: t.map((x) => x.scrap_type) },
    series: [{ type: 'bar', data: t.map((x) => x.weight), itemStyle: { borderRadius: [0, 4, 4, 0] } }],
  }
})

const scrapPieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
  legend: { bottom: 0, type: 'scroll' },
  series: [{ type: 'pie', radius: ['40%', '65%'], data: (scrap.value.types || []).map((x) => ({ name: x.scrap_type, value: x.weight })), label: { formatter: '{b}\n{d}%', color: '#94a3b8' } }],
}))

const gradeOption = computed(() => {
  const d = scrapByGrade.value.slice().reverse()
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>${fmtTon(p[0].value)} 吨` },
    grid: { left: '20%' },
    xAxis: { type: 'value', axisLabel: { formatter: (v) => (v / 1000).toFixed(0) + 'k' } },
    yAxis: { type: 'category', data: d.map((x) => x.steel_grade) },
    series: [{ type: 'bar', data: d.map((x) => x.total_weight), itemStyle: { borderRadius: [0, 4, 4, 0] } }],
  }
})

const matrixOption = computed(() => {
  const m = matrix.value
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: m.types, bottom: 0, type: 'scroll' },
    xAxis: { type: 'category', data: m.grades },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: m.types.map((t) => ({ name: t, type: 'bar', data: m.grades.map((g) => m.matrix[g]?.[t] || 0) })),
  }
})

const alloyCols = [
  { key: 'alloy', title: '合金', mono: true },
  { key: 'used_count', title: '使用炉数' },
  { key: 'usage_rate', title: '使用率(%)', rate: true },
  { key: 'avg_amount', title: '均值', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'min_amount', title: '最小', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'max_amount', title: '最大', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'rate', title: '符合率(%)', rate: true },
]

const alloyFreqOption = computed(() => {
  const d = alloy.value.slice().sort((a, b) => (b.used_count || 0) - (a.used_count || 0)).slice(0, 10).reverse()
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: ${p[0].value} 炉` },
    grid: { left: '22%' },
    xAxis: { type: 'value', name: '炉数' },
    yAxis: { type: 'category', data: d.map((a) => a.alloy) },
    series: [{ type: 'bar', data: d.map((a) => a.used_count), itemStyle: { borderRadius: [0, 4, 4, 0] } }],
  }
})

const alloyAvgOption = computed(() => {
  const d = alloy.value.slice(0, 10).reverse()
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '22%' },
    xAxis: { type: 'value', name: '均值' },
    yAxis: { type: 'category', data: d.map((a) => a.alloy) },
    series: [{ type: 'bar', data: d.map((a) => a.avg_amount), itemStyle: { color: '#a78bfa', borderRadius: [0, 4, 4, 0] } }],
  }
})

onMounted(async () => {
  try {
    const [s, g, mx, a, ins] = await Promise.all([
      costApi.scrapOverview(),
      costApi.scrapByGrade(10),
      costApi.scrapMatrix(8),
      costApi.alloyOverview(),
      costApi.insights(),
    ])
    scrap.value = s
    scrapByGrade.value = g
    matrix.value = mx
    alloy.value = a
    insights.value = ins
  } catch (e) { console.error(e) }
})
</script>
