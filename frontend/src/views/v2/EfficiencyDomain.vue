<template>
  <div class="domain">
    <div class="domain-tabs">
      <button v-for="t in tabs" :key="t.key" :class="{ active: active === t.key }" @click="active = t.key">{{ t.label }}</button>
    </div>
    <div class="domain-content" :key="active">
      <!-- Tab 1: 总览 -->
      <div v-if="active === 'overview'">
        <AnalysisCard :data="ai.overview || {}" />
        <EfficiencyV2 />
      </div>

      <!-- Tab 2: 冶炼周期 -->
      <div v-else-if="active === 'cycle'">
        <AnalysisCard :data="ai.cycle || {}" />
        <div class="card">
          <h3 class="card-title">各工序时长统计</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>工序</th><th>指标</th><th>均值(min)</th><th>最小</th><th>P99</th><th>标准差</th><th>样本</th></tr></thead>
              <tbody>
                <tr v-for="(d, i) in durationData" :key="i">
                  <td>{{ d.process }}</td><td class="mono">{{ d.indicator }}</td>
                  <td class="primary">{{ d.avg }}</td><td>{{ d.min }}</td><td class="warn">{{ d.p99 }}</td>
                  <td>{{ d.std }}</td><td>{{ d.n }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 3: 班组产能 -->
      <div v-else-if="active === 'team'">
        <AnalysisCard :data="ai.team || {}" />
        <div class="card">
          <h3 class="card-title">班组产能对标</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>班组</th><th>炉数</th><th>判定数</th><th>命中</th><th>符合率</th></tr></thead>
              <tbody>
                <tr v-for="(t, i) in teamData" :key="i">
                  <td class="mono">{{ t.team }}班</td><td>{{ t.heats }}</td><td>{{ t.judged }}</td>
                  <td>{{ t.hit }}</td>
                  <td :class="t.rate >= 90 ? 'good' : t.rate >= 80 ? 'warn' : 'bad'">{{ t.rate }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 4: 设备分析 -->
      <div v-else-if="active === 'equipment'">
        <AnalysisCard :data="ai.equipment || {}" />
        <div class="card">
          <h3 class="card-title">设备产量与符合率（按工序）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>工序</th><th>设备</th><th>炉数</th><th>工序内占比</th><th>符合率</th></tr></thead>
              <tbody>
                <tr v-for="(e, i) in equipmentData" :key="i">
                  <td>{{ e.process }}</td><td class="mono">{{ e.equipment }}</td><td>{{ e.heats }}</td>
                  <td>{{ e.pct }}%</td>
                  <td :class="e.rate >= 90 ? 'good' : e.rate >= 80 ? 'warn' : 'bad'">{{ e.rate }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 5: 工艺趋势 -->
      <div v-else-if="active === 'trend'">
        <AnalysisCard :data="ai.trend || {}" />
        <div class="card">
          <h3 class="card-title">关键参数趋势</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>参数</th><th>均值</th><th>标准差</th><th>变异系数</th><th>稳定性</th></tr></thead>
              <tbody>
                <tr v-for="(t, i) in trendData" :key="i">
                  <td class="mono">{{ t.indicator }}</td><td class="primary">{{ t.avg }}{{ t.unit }}</td>
                  <td>{{ t.std }}{{ t.unit }}</td><td>{{ t.cv }}%</td>
                  <td :class="t.cv > 30 ? 'bad' : 'good'">{{ t.cv > 30 ? '不稳定' : '稳定' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import EfficiencyV2 from '@/views/v2/EfficiencyV2.vue'
import AnalysisCard from '@/components/common/AnalysisCard.vue'
import { efficiencyApi } from '@/api/modules'

const active = ref('overview')
const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'cycle', label: '冶炼周期' },
  { key: 'team', label: '班组产能' },
  { key: 'equipment', label: '设备分析' },
  { key: 'trend', label: '工艺趋势' },
]
const ai = ref({})
const durationData = ref([])
const teamData = ref([])
const equipmentData = ref([])
const trendData = ref([])

onMounted(async () => {
  try {
    const [aiData, durations, teams, equip] = await Promise.all([
      efficiencyApi.aiAnalysis(),
      efficiencyApi.durationStats(),
      efficiencyApi.heatCountByTeam(),
      efficiencyApi.equipmentOutput ? efficiencyApi.equipmentOutput() : Promise.resolve([]),
    ])
    ai.value = aiData
    durationData.value = (durations || []).map(d => ({
      process: d.process, indicator: d.indicator, avg: d.avg, min: d.min, p99: d.p99, std: d.std, n: d.n
    }))
    teamData.value = (teams || []).map(t => ({
      team: t.team, heats: t.heats, judged: t.judged, hit: t.hit, rate: t.rate
    }))
    equipmentData.value = (equip || []).map(e => ({
      process: e.process || '', equipment: e.equipment, heats: e.heats, pct: 0, rate: e.rate || 0
    }))
    // 工序内占比
    const procTotal = {}
    equipmentData.value.forEach(e => procTotal[e.process] = (procTotal[e.process] || 0) + e.heats)
    equipmentData.value.forEach(e => e.pct = procTotal[e.process] ? Math.round(100 * e.heats / procTotal[e.process]) : 0)
    // 趋势数据从AI返回的结构化数据
    trendData.value = (aiData.trend?.data || []).map(t => ({
      indicator: t.indicator, avg: t.avg, std: t.std, cv: t.cv, unit: t.unit || ''
    }))
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.domain-tabs { display: flex; gap: 0; border-bottom: 2px solid #E2E8F0; margin-bottom: 20px; background: #fff; border-radius: 14px 14px 0 0; padding: 0 8px; overflow-x: auto; }
.domain-tabs button { background: none; border: none; color: #475569; padding: 14px 20px; cursor: pointer; font-size: 0.88rem; font-weight: 600; border-bottom: 3px solid transparent; transition: all 0.2s; margin-bottom: -2px; white-space: nowrap; }
.domain-tabs button:hover { color: #0284C7; }
.domain-tabs button.active { color: #0284C7; font-weight: 800; border-bottom-color: #0284C7; }
.domain-content { color: #0F172A; }
.card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 1rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; }
.tbl-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid #E2E8F0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #fff; }
.data-table th { background: #F0F9FF; color: #0369A1; padding: 10px 12px; text-align: left; font-weight: 700; white-space: nowrap; }
.data-table td { padding: 8px 12px; border-bottom: 1px solid #F1F5F9; color: #475569; }
.data-table tr:hover td { background: #F8FAFC; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
.primary { color: #0284C7; font-weight: 700; }
.good { color: #10B981; font-weight: 700; }
.warn { color: #F59E0B; font-weight: 700; }
.bad { color: #DC2626; font-weight: 700; }
</style>
