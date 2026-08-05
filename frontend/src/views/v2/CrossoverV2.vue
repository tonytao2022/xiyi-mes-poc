<template>
  <div class="hero">
    <div class="hero-left"><div <div class="hero-icon"><Icon name="link" :size="32" /></div><div><h1 class="hero-title">双维度交叉分析</h1><p class="hero-sub">质量×成本 · 质量×效率 · 成本×效率</p></div></div>
  </div>
  <div class="toolbar">
    <div class="view-switch">
      <button v-for="v in views" :key="v.key" :class="{ active: view === v.key }" @click="switchView(v.key)">{{ v.label }}</button>
    </div>
  </div>
  <div class="insight-list">
    <div v-for="(it, i) in items" :key="i" class="insight-card">
      <div class="insight-head">
        <span class="insight-badge" :class="levelClass(it.level)">{{ it.level }}</span>
        <span class="insight-title">{{ it.title }}</span>
      </div>
      <p class="insight-content">{{ it.content }}</p>
      <div v-if="it.chart" class="chart-box">
        <EChart :option="chartOption(it.chart)" theme="mes-light" :height="it.chart.type === 'scatter' ? '340px' : '280px'" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import Icon from '@/components/common/Icon.vue'
import EChart from '@/components/charts/EChart.vue'
import { crossoverApi } from '@/api/modules'

const view = ref('quality-cost')
const views = [
  { key: 'quality-cost', label: '质量 × 成本' },
  { key: 'quality-efficiency', label: '质量 × 效率' },
  { key: 'cost-efficiency', label: '成本 × 效率' },
]
const items = ref([])

function levelClass(l) { return l === '严重' ? 'bad' : l === '警告' ? 'warn' : l === '亮点' ? 'good' : 'info' }

function chartOption(c) {
  if (c.type === 'bar') return { tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: c.labels, axisLabel: { rotate: 25, fontSize: 9 } }, yAxis: { type: 'value' }, series: [{ type: 'bar', data: c.values, itemStyle: { borderRadius: [4, 4, 0, 0] } }] }
  if (c.type === 'scatter') return { tooltip: { formatter: (p) => `${(c.labels?.[p.dataIndex]) || ''}: (${p.data[0]}, ${p.data[1]})` }, xAxis: { type: 'value', name: c.xName || '', scale: true }, yAxis: { type: 'value', name: c.yName || '', scale: true }, series: [{ type: 'scatter', data: c.points, symbolSize: 10, itemStyle: { color: 'rgba(2,132,199,0.6)' } }] }
  return {}
}

async function switchView(k) {
  view.value = k
  const api = k === 'quality-cost' ? crossoverApi.qualityCost : k === 'quality-efficiency' ? crossoverApi.qualityEfficiency : crossoverApi.costEfficiency
  try { items.value = (await api()).items || [] } catch (e) { console.error(e) }
}

onMounted(() => switchView('quality-cost'))
</script>

<style scoped>
.hero { display: flex; align-items: center; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.hero-left { display: flex; align-items: center; gap: 14px; }
.hero-icon { font-size: 2rem; }
.hero-title { font-size: 1.3rem; font-weight: 900; color: #0F172A; margin: 0; }
.hero-sub { font-size: 0.78rem; color: #475569; margin: 0; }
.toolbar { margin-bottom: 16px; }
.view-switch { display: flex; gap: 4px; background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 24px; padding: 4px; display: inline-flex; }
.view-switch button { background: none; border: none; color: #475569; padding: 8px 24px; border-radius: 20px; cursor: pointer; font-size: 0.85rem; font-weight: 700; transition: all 0.2s; }
.view-switch button.active { background: #fff; color: #0284C7; font-weight: 900; box-shadow: 0 2px 8px rgba(2,132,199,0.12); border: 1px solid #BAE6FD; }
.insight-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 16px; }
.insight-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #0284C7; }
.insight-card:nth-child(2n) { border-left-color: #10B981; }
.insight-card:nth-child(3n) { border-left-color: #F59E0B; }
.insight-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.insight-badge { font-size: 0.65rem; padding: 2px 10px; border-radius: 12px; font-weight: 700; }
.insight-badge.bad { background: #FEF2F2; color: #B91C1C; }
.insight-badge.warn { background: #FFFBEB; color: #D97706; }
.insight-badge.good { background: #ECFDF5; color: #047857; }
.insight-badge.info { background: #F0F9FF; color: #0369A1; }
.insight-title { font-size: 0.92rem; font-weight: 800; color: #0F172A; }
.insight-content { font-size: 0.82rem; color: #475569; line-height: 1.6; margin: 0 0 12px; }
.chart-box { margin-top: 8px; }
</style>
