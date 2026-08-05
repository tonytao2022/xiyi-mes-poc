<template>
  <SectionPanel title="单件物料偏差 z-score（对应 PDF 单块报告）" icon="🎯">
    <p class="section-hint">
      以 SWRCH22A 整体为基线，计算单件物料各指标 z-score。评级：|z|≥3 严重，≥2 偏离，&lt;2 正常。
      试批号：<span class="mono">{{ deviation.sample_lot_no || '-' }}</span>
    </p>
    <div class="stats" style="margin-bottom: 1rem">
      <StatCard label="严重" :rows="[{ k: '数量', v: deviation.summary?.严重 || 0, cls: 'pass-bad' }]" />
      <StatCard label="偏离" :rows="[{ k: '数量', v: deviation.summary?.偏离 || 0, cls: 'pass-warn' }]" />
      <StatCard label="正常" :rows="[{ k: '数量', v: deviation.summary?.正常 || 0, cls: 'pass-good' }]" />
      <StatCard label="无基线" :rows="[{ k: '数量', v: deviation.summary?.无基线 || 0 }]" />
      <StatCard label="无数据" :rows="[{ k: '数量', v: deviation.summary?.无数据 || 0 }]" />
    </div>
    <DataTable :columns="deviationCols" :rows="deviation.items || []" :scroll-x="true" />
  </SectionPanel>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import StatCard from '@/components/cards/StatCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import { qualityApi } from '@/api/modules'

const deviation = ref({ sample_lot_no: null, items: [], summary: {} })
const deviationCols = [
  { key: 'source', title: '源' },
  { key: 'name', title: '指标' },
  { key: 'actual', title: '实测', format: (v) => (v == null ? '-' : Number(v).toFixed(2)) },
  { key: 'avg', title: '基线均值', format: (v) => (v == null ? '-' : Number(v).toFixed(2)) },
  { key: 'std', title: '标准差', format: (v) => (v == null ? '-' : Number(v).toFixed(3)) },
  { key: 'p05', title: 'p05', format: (v) => (v == null ? '-' : Number(v).toFixed(2)) },
  { key: 'p95', title: 'p95', format: (v) => (v == null ? '-' : Number(v).toFixed(2)) },
  { key: 'z', title: 'z-score', format: (v) => (v == null ? '-' : (v >= 0 ? '+' : '') + Number(v).toFixed(2)) },
  { key: 'grade', title: '评级', format: (v) => v || '-' },
]

onMounted(async () => {
  try { deviation.value = await qualityApi.singleDeviation() } catch (e) { console.error(e) }
})
</script>
