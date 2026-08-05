<template>
  <div class="hero">
    <div class="hero-left"><div <div class="hero-icon"><Icon name="target" :size="32" /></div><div><h1 class="hero-title">综合炉次成本模型</h1><p class="hero-sub">直接成本 + 质量损失 + 效率损失 = 综合成本</p></div></div>
    <div class="hero-stats">
      <div class="stat-pill"><span class="stat-val primary">{{ fmt(s.direct) }}</span><span class="stat-lbl">直接({{ s.direct_pct }}%)</span></div>
      <div class="stat-pill"><span class="stat-val bad">{{ fmt(s.quality) }}</span><span class="stat-lbl">质量损失({{ s.quality_pct }}%)</span></div>
      <div class="stat-pill"><span class="stat-val warn">{{ fmt(s.efficiency) }}</span><span class="stat-lbl">效率损失({{ s.efficiency_pct }}%)</span></div>
      <div class="stat-pill"><span class="stat-val primary">{{ fmt(s.total) }}</span><span class="stat-lbl">综合合计</span></div>
    </div>
  </div>
  <div class="content-grid">
    <div class="card"><h3 class="card-title">损失结构</h3><EChart :option="pieOption" theme="mes-light" height="300px" /></div>
    <div class="card"><h3 class="card-title">钢种综合成本对标 Top10</h3>
      <div class="tbl-wrap"><table class="v2-table">
        <thead><tr><th>钢种</th><th>炉数</th><th>直接</th><th>质量</th><th>效率</th><th>综合</th></tr></thead>
        <tbody><tr v-for="g in data.grade_benchmark" :key="g.steel_grade"><td class="mono">{{ g.steel_grade }}</td><td>{{ g.n }}</td><td>{{ fmt(g.avg_direct) }}</td><td>{{ fmt(g.avg_quality) }}</td><td>{{ fmt(g.avg_efficiency) }}</td><td class="primary">{{ fmt(g.avg_total) }}</td></tr></tbody>
      </table></div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Icon from '@/components/common/Icon.vue'
import EChart from '@/components/charts/EChart.vue'
import { comprehensiveApi } from '@/api/modules'

const data = ref({ structure: {}, grade_benchmark: [] })
const s = computed(() => data.value.structure || {})
const fmt = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
const pieOption = computed(() => ({ tooltip: { trigger: 'item', formatter: '{b}: {c}元 ({d}%)' }, legend: { bottom: 0 }, series: [{ type: 'pie', radius: ['40%', '65%'], data: [{ name: '直接成本', value: s.value.direct }, { name: '质量损失', value: s.value.quality }, { name: '效率损失', value: s.value.efficiency }], label: { formatter: '{b}\n{d}%', color: '#475569' } }] }))
onMounted(async () => { try { data.value = await comprehensiveApi.model(50) } catch (e) { console.error(e) } })
</script>

<style scoped>
.hero { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.hero-left { display: flex; align-items: center; gap: 14px; }
.hero-icon { font-size: 2rem; }
.hero-title { font-size: 1.3rem; font-weight: 900; color: #0F172A; margin: 0; }
.hero-sub { font-size: 0.78rem; color: #475569; margin: 0; }
.hero-stats { display: flex; gap: 12px; }
.stat-pill { display: flex; flex-direction: column; align-items: center; gap: 2px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 16px; min-width: 90px; }
.stat-val { font-size: 1.2rem; font-weight: 900; font-family: ui-monospace, monospace; }
.stat-val.primary { color: #0284C7; }
.stat-val.bad { color: #B91C1C; }
.stat-val.warn { color: #D97706; }
.stat-lbl { font-size: 0.65rem; color: #475569; font-weight: 600; }
.content-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 0.95rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; }
.tbl-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid #E2E8F0; }
.v2-table { width: 100%; border-collapse: collapse; font-size: 0.78rem; background: #fff; }
.v2-table th { background: #F0F9FF; color: #0369A1; padding: 8px 10px; text-align: left; font-weight: 700; white-space: nowrap; }
.v2-table td { padding: 6px 10px; border-bottom: 1px solid #F1F5F9; color: #475569; }
.v2-table tr:hover td { background: #F8FAFC; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
.primary { color: #0284C7; font-weight: 700; }
</style>
