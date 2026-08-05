<template>
  <div class="indicators-page">
    <!-- 短板指标 -->
    <div class="card">
      <h3 class="card-title">指标短板 Top15</h3>
      <p class="hint">点击柱状图或下拉选择指标，下钻查看异常炉次明细</p>
      <div class="chart-box">
        <EChart :option="shortboardOption" height="440px" @chart-click="onChartClick" />
      </div>
      <div class="indicator-select">
        <label>或选择指标：</label>
        <select v-model="selectedIndicator" @change="onSelectChange">
          <option v-for="s in shortboard" :key="s.name" :value="s.name">{{ s.name }}（{{ s.process }}）{{ s.rate }}%</option>
        </select>
      </div>
    </div>

    <!-- 根因下钻 -->
    <div v-if="detail.indicator" class="card">
      <h3 class="card-title">根因下钻：异常炉次与参数偏离</h3>
      <p class="hint">
        选中指标：<span class="mono">{{ detail.process }} · {{ detail.indicator }}</span>
        （符合率 {{ detail.rate }}%，异常 {{ detail.abnormal_count }} 炉）
      </p>
      <div class="stat-row">
        <div class="stat-item">
          <div class="stat-label">符合率</div>
          <div class="stat-value" :class="detail.rate < 60 ? 'bad' : detail.rate < 80 ? 'warn' : 'good'">{{ detail.rate }}%</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">命中/判定</div>
          <div class="stat-value primary">{{ detail.hit }}/{{ detail.judged }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">异常炉次</div>
          <div class="stat-value bad">{{ detail.abnormal_count }}炉</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">实绩均值</div>
          <div class="stat-value primary">{{ detail.distribution?.avg ?? '-' }}</div>
        </div>
        <div class="stat-item">
          <div class="stat-label">实绩范围</div>
          <div class="stat-value">{{ detail.distribution?.min ?? '-' }}~{{ detail.distribution?.max ?? '-' }}</div>
        </div>
      </div>
      <div v-if="detail.trend && detail.trend.values && detail.trend.values.length" class="chart-box">
        <h4 class="sub-title">实绩趋势时序</h4>
        <EChart :option="trendOption" height="300px" />
      </div>
      <div class="table-wrap">
        <h4 class="sub-title">异常炉次明细（{{ detail.abnormal_count }} 炉，judge=0）</h4>
        <table class="data-table">
          <thead>
            <tr><th>熔炼号</th><th>钢种</th><th>班组</th><th>标准</th><th>实绩</th><th>出钢时刻</th></tr>
          </thead>
          <tbody>
            <tr v-for="(r, i) in (detail.abnormal || [])" :key="i">
              <td class="mono">{{ r.heat_no }}</td><td>{{ r.steel_grade }}</td><td>{{ r.team }}</td>
              <td>{{ r.std }}</td><td class="bad-text">{{ r.actual }}</td><td>{{ r.tap_time }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="loading">加载中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import EChart from '@/components/charts/EChart.vue'
import { qualityApi } from '@/api/modules'

const shortboard = ref([])
const detail = ref({})
const selectedIndicator = ref('')

const shortboardOption = computed(() => {
  const d = shortboard.value.slice().reverse()
  return {
    tooltip: { trigger: 'axis', formatter: (p) => { const i = p[0].dataIndex; return `${d[i].name}<br/>${d[i].rate}% (${d[i].process}·判定${d[i].judged})<br/>点击查看根因` } },
    grid: { left: '24%' },
    xAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: d.map((s) => s.name) },
    series: [{ type: 'bar', data: d.map((s) => ({ value: s.rate, itemStyle: { color: s.rate >= 95 ? '#34d399' : s.rate >= 80 ? '#fbbf24' : '#f87171' } })), itemStyle: { borderRadius: [0, 4, 4, 0] } }],
  }
})

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: detail.value.trend?.times || [], axisLabel: { rotate: 45, fontSize: 9 } },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: detail.value.trend?.values || [], smooth: true, areaStyle: { opacity: 0.1 } }],
}))

async function loadDetail(process, name) {
  try {
    detail.value = await qualityApi.indicatorDetail(process, name)
    selectedIndicator.value = name
  } catch (e) { console.error('loadDetail error:', e) }
}

function onChartClick(params) {
  if (!params || !params.name) return
  const item = shortboard.value.find((s) => s.name === params.name)
  if (item) loadDetail(item.process, item.name)
}

function onSelectChange() {
  const item = shortboard.value.find((s) => s.name === selectedIndicator.value)
  if (item) loadDetail(item.process, item.name)
}

onMounted(async () => {
  try {
    const s = await qualityApi.indicatorRanking(null, 'asc')
    shortboard.value = s
    if (s.length) loadDetail(s[0].process, s[0].name)
  } catch (e) { console.error('loadDefault error:', e) }
})
</script>

<style scoped>
.indicators-page { display: flex; flex-direction: column; gap: 20px; }
.card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 1rem; font-weight: 800; color: #0F172A; margin: 0 0 8px; }
.hint { font-size: 0.82rem; color: #64748B; margin: 0 0 12px; }
.chart-box { margin-bottom: 12px; }
.indicator-select { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.indicator-select label { font-size: 0.85rem; color: #475569; }
.indicator-select select { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; color: #0F172A; padding: 6px 12px; font-size: 0.85rem; min-width: 300px; }
.stat-row { display: flex; gap: 24px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-item { text-align: center; }
.stat-label { font-size: 0.75rem; color: #94A3B8; font-weight: 600; }
.stat-value { font-size: 1.4rem; font-weight: 900; font-family: ui-monospace, monospace; color: #0284C7; }
.stat-value.good { color: #10B981; } .stat-value.warn { color: #F59E0B; } .stat-value.bad { color: #DC2626; }
.stat-value.primary { color: #0284C7; }
.sub-title { font-size: 0.9rem; font-weight: 700; color: #0F172A; margin: 16px 0 8px; }
.table-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid #E2E8F0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #fff; }
.data-table th { background: #F0F9FF; color: #0369A1; padding: 10px 12px; text-align: left; font-weight: 700; white-space: nowrap; }
.data-table td { padding: 8px 12px; border-bottom: 1px solid #F1F5F9; color: #475569; }
.data-table tr:hover td { background: #F8FAFC; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
.bad-text { color: #DC2626; font-weight: 600; }
.loading { text-align: center; padding: 40px; color: #94A3B8; }
</style>
