<template>
  <SectionPanel title="三维度综合炉次成本模型（创举核心）" icon="🎯">
    <p class="section-hint">
      综合炉次成本 = 直接成本 + 质量损失成本 + 效率损失成本。质量、效率都折算为成本，形成标量优化目标。
      {{ data.note }}
    </p>
    <div class="stats">
      <StatCard label="直接成本合计(元)" :rows="[{ k: '合计', v: fmt(data.structure?.direct), cls: 'v big' }, { k: '占比', v: (data.structure?.direct_pct || 0) + '%' }]" />
      <StatCard label="质量损失合计(元)" :rows="[{ k: '合计', v: fmt(data.structure?.quality), cls: 'v big' }, { k: '占比', v: (data.structure?.quality_pct || 0) + '%' }]" />
      <StatCard label="效率损失合计(元)" :rows="[{ k: '合计', v: fmt(data.structure?.efficiency), cls: 'v big' }, { k: '占比', v: (data.structure?.efficiency_pct || 0) + '%' }]" />
      <StatCard label="综合成本合计(元)" :rows="[{ k: '合计', v: fmt(data.structure?.total), cls: 'v big' }]" />
    </div>
    <div class="charts">
      <ChartCard title="损失结构（三块占比）" :full="true">
        <EChart :option="structureOption" height="320px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="钢种综合成本对标（平均综合成本排名）" icon="📊">
    <DataTable :columns="gradeCols" :rows="data.grade_benchmark || []" :scroll-x="true" />
  </SectionPanel>

  <SectionPanel title="班组综合成本对标" icon="👥">
    <div class="charts">
      <ChartCard title="班组平均综合成本(元/炉)" :full="true">
        <EChart :option="teamOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="炉次综合成本明细（Top 高成本炉次）" icon="🔥">
    <DataTable :columns="heatCols" :rows="data.heats || []" :scroll-x="true" />
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StatCard from '@/components/cards/StatCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import EChart from '@/components/charts/EChart.vue'
import { comprehensiveApi } from '@/api/modules'

const data = ref({ structure: {}, heats: [], grade_benchmark: [], team_benchmark: [] })

const fmt = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })

const structureOption = computed(() => {
  const s = data.value.structure || {}
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}元 ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '65%'],
      data: [
        { name: '直接成本', value: s.direct || 0 },
        { name: '质量损失', value: s.quality || 0 },
        { name: '效率损失', value: s.efficiency || 0 },
      ],
      label: { formatter: '{b}\n{d}%', color: '#94a3b8' },
    }],
  }
})

const teamOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: ${fmt(p[0].value)} 元/炉` },
  xAxis: { type: 'category', data: (data.value.team_benchmark || []).map((t) => t.team + '班') },
  yAxis: { type: 'value', axisLabel: { formatter: (v) => (v / 10000).toFixed(0) + '万' } },
  series: [{ type: 'bar', data: (data.value.team_benchmark || []).map((t) => t.avg_total), itemStyle: { borderRadius: [4, 4, 0, 0], color: '#a78bfa' } }],
}))

const gradeCols = [
  { key: 'steel_grade', title: '钢种', mono: true },
  { key: 'n', title: '炉数' },
  { key: 'avg_direct', title: '平均直接成本', format: (v) => fmt(v) },
  { key: 'avg_quality', title: '平均质量损失', format: (v) => fmt(v) },
  { key: 'avg_efficiency', title: '平均效率损失', format: (v) => fmt(v) },
  { key: 'avg_total', title: '平均综合成本', format: (v) => fmt(v) },
]
const heatCols = [
  { key: 'heat_no', title: '熔炼号', mono: true },
  { key: 'steel_grade', title: '钢种' },
  { key: 'team', title: '班组' },
  { key: 'compliance_rate', title: '符合率(%)', rate: true },
  { key: 'direct', title: '直接成本', format: (v) => fmt(v) },
  { key: 'quality_loss', title: '质量损失', format: (v) => fmt(v) },
  { key: 'efficiency_loss', title: '效率损失', format: (v) => fmt(v) },
  { key: 'total', title: '综合成本', format: (v) => fmt(v) },
]

onMounted(async () => {
  try { data.value = await comprehensiveApi.model(50) } catch (e) { console.error(e) }
})
</script>
