<template>
  <div class="domain">
    <div class="domain-tabs">
      <button v-for="t in tabs" :key="t.key" :class="{ active: active === t.key }" @click="active = t.key">{{ t.label }}</button>
    </div>
    <div class="domain-content" :key="active">
      <!-- Tab 1: 综合总账 -->
      <div v-if="active === 'overview'">
        <AnalysisCard :data="ai.overview || {}" />
        <ComprehensiveV2 />
      </div>

      <!-- Tab 2: 质量损失折算 -->
      <div v-else-if="active === 'quality_loss'">
        <AnalysisCard :data="ai.quality_loss || {}" />
        <div class="card">
          <h3 class="card-title">质量损失明细（按损失项，含来源标注）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>损失项</th><th>来源</th><th>炉数</th><th>损失金额(元)</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in qLoss.by_loss_name" :key="i">
                  <td class="mono">{{ r.loss_name }}</td>
                  <td :class="r.source === 'formula' ? 'good' : 'warn'">{{ r.source === 'formula' ? '精确口径' : '估算' }}</td>
                  <td>{{ r.n }}</td><td class="primary">{{ r.total.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">合金富裕损失（精确口径：actual 超 std 上限 × 单价）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>合金</th><th>超出量</th><th>单价</th><th>损失(元)</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in qLoss.alloy_surplus_detail" :key="i">
                  <td class="mono">{{ r.alloy }}</td><td>{{ r.excess }}</td><td>{{ r.price }}</td>
                  <td class="bad">{{ r.cost.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">钢种质量损失 Top15</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>钢种</th><th>炉数</th><th>质量损失(元)</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in qLoss.by_steel_grade" :key="i">
                  <td class="mono">{{ r.steel_grade }}</td><td>{{ r.heats }}</td><td class="primary">{{ r.total.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 3: 效率损失折算 -->
      <div v-else-if="active === 'efficiency_loss'">
        <AnalysisCard :data="ai.efficiency_loss || {}" />
        <div class="card">
          <h3 class="card-title">效率损失明细（按损失项，含来源标注）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>损失项</th><th>来源</th><th>炉数</th><th>损失金额(元)</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in eLoss.by_loss_name" :key="i">
                  <td class="mono">{{ r.loss_name }}</td>
                  <td class="warn">{{ r.source === 'formula' ? '精确' : '估算' }}</td>
                  <td>{{ r.n }}</td><td class="primary">{{ r.total.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">各工序时长-成本（时间=能耗）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>工序</th><th>总时长(min)</th><th>能耗成本(元)</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in eLoss.by_process_cost" :key="i">
                  <td class="mono">{{ r.process }}</td><td>{{ r.total_min.toLocaleString() }}</td>
                  <td class="primary">{{ r.cost.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title">班组效率损失对标</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>班组</th><th>炉数</th><th>效率损失(元)</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in eLoss.by_team" :key="i">
                  <td class="mono">{{ r.team }}班</td><td>{{ r.heats }}</td><td class="primary">{{ r.total.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="hint">P95超时阈值：{{ eLoss.summary.overdue_p95 }}min，超时{{ eLoss.summary.overdue_heats }}炉，超时损失约{{ (eLoss.summary.overdue_cost||0).toLocaleString() }}元</p>
        </div>
      </div>

      <!-- Tab 4: 交叉杠杆 -->
      <div v-else-if="active === 'cross_leverage'">
        <AnalysisCard :data="ai.cross_leverage || {}" />
        <div class="card">
          <h3 class="card-title">敏感度对比（变量弹性，找最大杠杆点）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>变量</th><th>弹性系数</th><th>含义</th><th>说明</th></tr></thead>
              <tbody>
                <tr v-for="(s, i) in sensitivityList" :key="i" :class="{ 'hl-row': i === 0 }">
                  <td class="mono">{{ s.label }}</td>
                  <td :class="i === 0 ? 'bad' : 'primary'">{{ s.elasticity }}</td>
                  <td>{{ s.note }}</td><td>±10%时综合成本变化最大</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="hint">弹性系数越高，该变量对综合成本影响越大，是优化投入产出比最高的杠杆点。</p>
        </div>
        <div class="card">
          <h3 class="card-title">配料-合格率权衡（低端料占比 vs 合金符合率）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>钢种</th><th>低端料占比%</th><th>合金符合率%</th></tr></thead>
              <tbody>
                <tr v-for="(t, i) in tradeoffList" :key="i">
                  <td class="mono">{{ t.steel_grade }}</td>
                  <td :class="t.low_pct > 30 ? 'bad' : ''">{{ t.low_pct }}</td>
                  <td :class="t.alloy_rate < 90 ? 'warn' : 'good'">{{ t.alloy_rate }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="hint">低端料占比高(>30%)会推高杂质波动->合金符合率降->COQ损失升，是成本×质量权衡点。</p>
        </div>
      </div>

      <!-- Tab 5: 优化仿真 -->
      <div v-else-if="active === 'optimization'">
        <AnalysisCard :data="ai.optimization || {}" />
        <SimulationV2 />
        <div class="card">
          <h3 class="card-title">配料优化方案（LP：min 综合成本 = 采购+质量惩罚+效率惩罚）</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>料型</th><th>用量(吨)</th><th>采购成本</th><th>质量惩罚</th><th>效率惩罚</th><th>综合成本</th><th>占比%</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in recipe.recipe" :key="i">
                  <td class="mono">{{ r.name }}{{ r.low_end ? '(低端)' : '' }}</td>
                  <td>{{ r.amount }}</td><td>{{ r.cost.toLocaleString() }}</td>
                  <td :class="r.quality_penalty > 0 ? 'warn' : ''">{{ r.quality_penalty.toLocaleString() }}</td>
                  <td :class="r.efficiency_penalty > 0 ? 'warn' : ''">{{ r.efficiency_penalty.toLocaleString() }}</td>
                  <td class="primary">{{ r.comprehensive.toLocaleString() }}</td><td>{{ r.pct }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="recipe-summary">
            <span>综合成本：<b class="primary">{{ recipe.cost_breakdown?.comprehensive?.toLocaleString() }}元</b></span>
            <span>vs 基准(全一类废钢)：<b>{{ recipe.baseline?.comprehensive?.toLocaleString() }}元</b></span>
            <span>节省：<b class="good">{{ recipe.saving?.toLocaleString() }}元 ({{ recipe.saving_pct }}%)</b></span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import AnalysisCard from '@/components/common/AnalysisCard.vue'
import ComprehensiveV2 from '@/views/v2/ComprehensiveV2.vue'
import SimulationV2 from '@/views/v2/SimulationV2.vue'
import { comprehensiveApi } from '@/api/modules'

const active = ref('overview')
const tabs = [
  { key: 'overview', label: '综合总账' },
  { key: 'quality_loss', label: '质量损失折算' },
  { key: 'efficiency_loss', label: '效率损失折算' },
  { key: 'cross_leverage', label: '交叉杠杆' },
  { key: 'optimization', label: '优化仿真' },
]
const ai = ref({})
const qLoss = ref({ by_loss_name: [], alloy_surplus_detail: [], by_steel_grade: [], summary: {} })
const eLoss = ref({ by_loss_name: [], by_process_cost: [], by_team: [], summary: {} })
const sensitivityList = ref([])
const tradeoffList = ref([])
const recipe = ref({ recipe: [], cost_breakdown: {}, baseline: {} })
let sensLoaded = false

onMounted(async () => {
  try {
    const [aiData, q, e, to] = await Promise.all([
      comprehensiveApi.aiAnalysis(),
      comprehensiveApi.qualityLossDetail(),
      comprehensiveApi.efficiencyLossDetail(),
      comprehensiveApi.tradeoff(),
    ])
    ai.value = aiData
    qLoss.value = q || {}
    eLoss.value = e || {}
    tradeoffList.value = (to?.scrap_quality_tradeoff) || []
  } catch (e) { console.error(e) }
})

// Tab 4 敏感度懒加载（4变量）
watch(active, async (v) => {
  if (v === 'cross_leverage' && !sensLoaded) {
    sensLoaded = true
    try {
      const vars = ['quality', 'efficiency', 'yield_rate', 'energy_price']
      const results = await Promise.all(vars.map(va => comprehensiveApi.sensitivity(va)))
      sensitivityList.value = results
        .map(r => ({ label: r.label, elasticity: r.elasticity, note: r.note }))
        .sort((a, b) => b.elasticity - a.elasticity)
    } catch (e) { console.error(e) }
  }
  if (v === 'optimization' && !recipe.value.recipe.length) {
    try { recipe.value = await comprehensiveApi.recipe() } catch (e) { console.error(e) }
  }
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
.data-table tr.hl-row td { background: #FEF3C7; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
.primary { color: #0284C7; font-weight: 700; }
.good { color: #10B981; font-weight: 700; }
.warn { color: #F59E0B; font-weight: 700; }
.bad { color: #DC2626; font-weight: 700; }
.hint { margin: 10px 0 0; color: #64748B; font-size: 0.8rem; }
.recipe-summary { display: flex; gap: 24px; margin-top: 14px; padding: 12px 16px; background: #F0F9FF; border-radius: 8px; font-size: 0.85rem; color: #475569; }
</style>
