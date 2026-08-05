<template>
  <div class="sim-workbench">
    <!-- 左侧：参数控制 -->
    <div class="control-panel">
      <div class="panel-section">
        <h3 class="section-title">🎯 质量维度</h3>
        <div class="param-row" v-for="p in qualityParams" :key="p.key">
          <label>{{ p.label }}</label>
          <input type="range" v-model.number="params[p.key]" :min="p.min" :max="p.max" :step="p.step" @input="update" />
          <span class="param-val">{{ p.fmt(params[p.key]) }}</span>
        </div>
      </div>
      <div class="panel-section">
        <h3 class="section-title">💰 成本维度</h3>
        <div class="param-row" v-for="p in costParams" :key="p.key">
          <label>{{ p.label }}</label>
          <input type="range" v-model.number="params[p.key]" :min="p.min" :max="p.max" :step="p.step" @input="update" />
          <span class="param-val">{{ p.fmt(params[p.key]) }}</span>
        </div>
      </div>
      <div class="panel-section">
        <h3 class="section-title">⚡ 效率维度</h3>
        <div class="param-row" v-for="p in efficiencyParams" :key="p.key">
          <label>{{ p.label }}</label>
          <input type="range" v-model.number="params[p.key]" :min="p.min" :max="p.max" :step="p.step" @input="update" />
          <span class="param-val">{{ p.fmt(params[p.key]) }}</span>
        </div>
      </div>
      <button class="reset-btn" @click="reset">↺ 重置参数</button>
    </div>

    <!-- 右侧：结果对比 -->
    <div class="result-panel">
      <div class="result-hero">
        <div class="rh-card" :class="deltaClass(result.delta_pct?.total)">
          <div class="rh-label">综合成本变化</div>
          <div class="rh-value">{{ fmt(result.delta?.total) }} 元</div>
          <div class="rh-pct">{{ result.delta_pct?.total }}%</div>
        </div>
        <div class="rh-card">
          <div class="rh-label">基准综合成本</div>
          <div class="rh-value primary">{{ fmt(result.base?.total) }} 元</div>
        </div>
        <div class="rh-card">
          <div class="rh-label">调参后综合成本</div>
          <div class="rh-value primary">{{ fmt(result.adjusted?.total) }} 元</div>
        </div>
      </div>

      <div class="chart-card">
        <h3 class="card-title">三块成本对比（基准 vs 调参后）</h3>
        <EChart :option="compareOption" theme="mes-light" height="320px" />
      </div>

      <div class="chart-card">
        <h3 class="card-title">变化明细</h3>
        <div class="dt-wrap">
          <div class="dt-row dt-head"><span>成本块</span><span>基准</span><span>调参后</span><span>变化</span><span>变化%</span></div>
          <div class="dt-row"><span>直接成本</span><span>{{ fmt(result.base?.direct) }}</span><span>{{ fmt(result.adjusted?.direct) }}</span><span :class="deltaClass(result.delta_pct?.direct)">{{ fmt(result.delta?.direct) }}</span><span>{{ result.delta_pct?.direct }}%</span></div>
          <div class="dt-row"><span>质量损失</span><span>{{ fmt(result.base?.quality) }}</span><span>{{ fmt(result.adjusted?.quality) }}</span><span :class="deltaClass(result.delta_pct?.quality)">{{ fmt(result.delta?.quality) }}</span><span>{{ result.delta_pct?.quality }}%</span></div>
          <div class="dt-row"><span>效率损失</span><span>{{ fmt(result.base?.efficiency) }}</span><span>{{ fmt(result.adjusted?.efficiency) }}</span><span :class="deltaClass(result.delta_pct?.efficiency)">{{ fmt(result.delta?.efficiency) }}</span><span>{{ result.delta_pct?.efficiency }}%</span></div>
          <div class="dt-row dt-total"><span>综合合计</span><span>{{ fmt(result.base?.total) }}</span><span>{{ fmt(result.adjusted?.total) }}</span><span :class="deltaClass(result.delta_pct?.total)">{{ fmt(result.delta?.total) }}</span><span>{{ result.delta_pct?.total }}%</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Icon from '@/components/common/Icon.vue'
import EChart from '@/components/charts/EChart.vue'
import { comprehensiveApi } from '@/api/modules'

const defaultParams = { yield_rate: 0.92, defect_rate: 0.01, reblow_count: 0, alloy_surplus_pct: 0.05, low_end_ratio: 0.15, scrap_price: 2800, alloy_substitution_rate: 0.10, refining_duration: 30, converter_duration: 25, waiting_time: 10, sequence_length: 20 }
const params = ref({ ...defaultParams })
const result = ref({ base: {}, adjusted: {}, delta: {}, delta_pct: {} })

const qualityParams = [
  { key: 'yield_rate', label: '钢水收得率', min: 0.85, max: 0.98, step: 0.01, fmt: (v) => (v * 100).toFixed(0) + '%' },
  { key: 'defect_rate', label: '废品率', min: 0.001, max: 0.05, step: 0.001, fmt: (v) => (v * 100).toFixed(1) + '%' },
  { key: 'reblow_count', label: '补吹炉次', min: 0, max: 200, step: 1, fmt: (v) => v + '炉' },
  { key: 'alloy_surplus_pct', label: '合金富裕比例', min: 0, max: 0.20, step: 0.01, fmt: (v) => (v * 100).toFixed(0) + '%' },
]
const costParams = [
  { key: 'low_end_ratio', label: '低端料配比', min: 0, max: 0.40, step: 0.01, fmt: (v) => (v * 100).toFixed(0) + '%' },
  { key: 'scrap_price', label: '废钢采购均价', min: 2000, max: 3500, step: 50, fmt: (v) => v + '元/吨' },
  { key: 'alloy_substitution_rate', label: '合金替代率', min: 0, max: 0.30, step: 0.01, fmt: (v) => (v * 100).toFixed(0) + '%' },
]
const efficiencyParams = [
  { key: 'refining_duration', label: '精炼时长', min: 15, max: 60, step: 1, fmt: (v) => v + 'min' },
  { key: 'converter_duration', label: '转炉吹炼时长', min: 15, max: 40, step: 1, fmt: (v) => v + 'min' },
  { key: 'waiting_time', label: '工序等待时间', min: 0, max: 30, step: 1, fmt: (v) => v + 'min' },
  { key: 'sequence_length', label: '连浇炉数', min: 10, max: 40, step: 1, fmt: (v) => v + '炉' },
]

const fmt = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
function deltaClass(pct) { return pct < 0 ? 'good' : pct > 0 ? 'bad' : '' }

const compareOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['基准', '调参后'], bottom: 0 },
  xAxis: { type: 'category', data: ['直接成本', '质量损失', '效率损失', '综合合计'] },
  yAxis: { type: 'value', axisLabel: { formatter: (v) => (v / 10000).toFixed(0) + '万' } },
  series: [
    { name: '基准', type: 'bar', data: [result.value.base?.direct, result.value.base?.quality, result.value.base?.efficiency, result.value.base?.total], itemStyle: { color: '#94A3B8', borderRadius: [4, 4, 0, 0] } },
    { name: '调参后', type: 'bar', data: [result.value.adjusted?.direct, result.value.adjusted?.quality, result.value.adjusted?.efficiency, result.value.adjusted?.total], itemStyle: { color: '#0284C7', borderRadius: [4, 4, 0, 0] } },
  ],
}))

let timer = null
function update() {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    try { result.value = await comprehensiveApi.interactive(params.value) } catch (e) { console.error(e) }
  }, 300)
}
function reset() { params.value = { ...defaultParams }; update() }

onMounted(async () => {
  try {
    result.value = await comprehensiveApi.interactive({})
    if (result.value.params) params.value = { ...result.value.params }
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.sim-workbench { display: flex; gap: 20px; }
.control-panel { width: 320px; flex-shrink: 0; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); height: fit-content; }
.panel-section { margin-bottom: 20px; }
.section-title { font-size: 0.95rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; }
.param-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.param-row label { font-size: 0.8rem; color: #475569; width: 80px; flex-shrink: 0; }
.param-row input[type=range] { flex: 1; accent-color: #0284C7; }
.param-val { font-size: 0.78rem; font-weight: 700; color: #0284C7; font-family: ui-monospace, monospace; width: 45px; text-align: right; }
.reset-btn { width: 100%; padding: 10px; background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 8px; color: #475569; font-weight: 700; cursor: pointer; transition: all 0.2s; }
.reset-btn:hover { background: #E2E8F0; color: #0F172A; }
.result-panel { flex: 1; display: flex; flex-direction: column; gap: 16px; }
.result-hero { display: flex; gap: 12px; }
.rh-card { flex: 1; background: #fff; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.rh-card.good { border-color: #10B981; background: #ECFDF5; }
.rh-card.bad { border-color: #EF4444; background: #FEF2F2; }
.rh-label { font-size: 0.72rem; color: #94A3B8; font-weight: 600; }
.rh-value { font-size: 1.3rem; font-weight: 900; font-family: ui-monospace, monospace; color: #0284C7; margin: 4px 0; }
.rh-value.primary { color: #0284C7; }
.rh-card.good .rh-value { color: #047857; }
.rh-card.bad .rh-value { color: #B91C1C; }
.rh-pct { font-size: 0.85rem; font-weight: 700; }
.rh-card.good .rh-pct { color: #047857; }
.rh-card.bad .rh-pct { color: #B91C1C; }
.chart-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 0.95rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; }
.dt-wrap { border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; }
.dt-row { display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr 0.8fr; padding: 8px 12px; font-size: 0.82rem; border-bottom: 1px solid #F1F5F9; }
.dt-row:last-child { border-bottom: none; }
.dt-head { background: #F0F9FF; color: #0369A1; font-weight: 700; }
.dt-total { background: #F8FAFC; font-weight: 800; color: #0F172A; }
.dt-row span { text-align: right; }
.dt-row span:first-child { text-align: left; }
.good { color: #047857; }
.bad { color: #B91C1C; }
</style>
