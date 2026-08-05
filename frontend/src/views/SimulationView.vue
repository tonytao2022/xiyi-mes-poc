<template>
  <SectionPanel title="参数仿真与情景对比" icon="🎛️">
    <p class="section-hint">
      调参看三块成本此消彼长，找全局最优方案。负 delta = 成本下降（优化）。
      分析思路：每个方案展示"如果调整某参数，综合成本怎么变"，揭示质量/效率/直接的权衡。
    </p>
    <div class="charts">
      <ChartCard title="各方案综合成本对比（三块堆叠）" :full="true">
        <EChart :option="simOption" height="360px" />
      </ChartCard>
    </div>
    <DataTable :columns="simCols" :rows="sim.scenarios || []" :scroll-x="true" />
  </SectionPanel>

  <SectionPanel title="敏感度分析（找优化杠杆点）" icon="📈">
    <div class="sens-ctrl">
      <label>变量：
        <select v-model="variable" @change="loadSensitivity">
          <option value="efficiency">效率损失</option>
          <option value="quality">质量损失</option>
          <option value="energy_price">能耗单价</option>
          <option value="yield_rate">收得率</option>
        </select>
      </label>
      <span class="section-hint">{{ sens.note }}</span>
    </div>
    <div class="charts">
      <ChartCard title="变量波动 ±20% vs 综合成本" :full="true">
        <EChart :option="sensOption" height="320px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel title="配料优化（线性规划求最低综合成本）" icon="🧮">
    <p class="section-hint">
      min Σ 价格×投料量，约束：总投料量/金属量需求/低端料上限(质量)。求最低成本配料方案。
    </p>
    <div class="recipe-ctrl">
      <label>总投料量(吨)：<input type="number" v-model.number="rp.totalWeight" /></label>
      <label>低端料上限(%)：<input type="number" v-model.number="rp.lowEndLimit" /></label>
      <label>金属需求(%)：<input type="number" v-model.number="rp.metalReq" step="0.01" /></label>
      <button class="recipe-btn" @click="loadRecipe">求解最优配料</button>
    </div>
    <div v-if="recipe.recipe" class="stats">
      <StatCard label="优化成本(元)" :rows="[{ k: '合计', v: fmt(recipe.total_cost), cls: 'v big' }]" />
      <StatCard label="基准(全一类废钢)" :rows="[{ k: '合计', v: fmt(recipe.baseline_cost) }]" />
      <StatCard label="节省" :rows="[{ k: '金额', v: fmt(recipe.saving), cls: 'pass-good' }, { k: '比例', v: recipe.saving_pct + '%' }]" />
      <StatCard label="求解状态" :rows="[{ k: 'status', v: recipe.status }]" />
    </div>
    <DataTable v-if="recipe.recipe" :columns="recipeCols" :rows="recipe.recipe" :scroll-x="true" />
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import StatCard from '@/components/cards/StatCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import EChart from '@/components/charts/EChart.vue'
import { comprehensiveApi } from '@/api/modules'

const sim = ref({ base: {}, scenarios: [] })
const sens = ref({ points: [], note: '' })
const variable = ref('efficiency')

const recipe = ref({})
const rp = ref({ totalWeight: 100, lowEndLimit: 20, metalReq: 0.9 })
const recipeCols = [
  { key: 'name', title: '料型' },
  { key: 'amount', title: '投料量(吨)', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'pct', title: '占比(%)', format: (v) => (v == null ? '-' : v + '%') },
  { key: 'price', title: '单价(元/吨)' },
  { key: 'cost', title: '成本(元)', format: (v) => fmt(v) },
]
async function loadRecipe() {
  try { recipe.value = await comprehensiveApi.recipe(rp.value.totalWeight, rp.value.lowEndLimit, rp.value.metalReq) } catch (e) { console.error(e) }
}

const fmt = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })

const simOption = computed(() => {
  const s = sim.value.scenarios || []
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['直接成本', '质量损失', '效率损失'] },
    xAxis: { type: 'category', data: s.map((x) => x.scenario), axisLabel: { rotate: 20, fontSize: 9 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v) => (v / 10000).toFixed(0) + '万' } },
    series: [
      { name: '直接成本', type: 'bar', stack: 'a', data: s.map((x) => x.direct), itemStyle: { color: '#60a5fa' } },
      { name: '质量损失', type: 'bar', stack: 'a', data: s.map((x) => x.quality), itemStyle: { color: '#f87171' } },
      { name: '效率损失', type: 'bar', stack: 'a', data: s.map((x) => x.efficiency), itemStyle: { color: '#fbbf24' } },
    ],
  }
})

const simCols = [
  { key: 'scenario', title: '方案' },
  { key: 'desc', title: '说明' },
  { key: 'direct', title: '直接成本', format: (v) => fmt(v) },
  { key: 'quality', title: '质量损失', format: (v) => fmt(v) },
  { key: 'efficiency', title: '效率损失', format: (v) => fmt(v) },
  { key: 'total', title: '综合成本', format: (v) => fmt(v) },
  { key: 'delta', title: '变化', format: (v) => (v >= 0 ? '+' : '') + fmt(v) },
  { key: 'delta_pct', title: '变化%', format: (v) => v + '%' },
]

const sensOption = computed(() => {
  const base = sens.value.base_total || 0
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: 综合 ${fmt(p[0].value)}（变化 ${fmt(p[0].value - base)}）` },
    xAxis: { type: 'category', data: (sens.value.points || []).map((p) => p.pct + '%') },
    yAxis: { type: 'value', axisLabel: { formatter: (v) => (v / 10000).toFixed(0) + '万' } },
    series: [{
      type: 'line', data: (sens.value.points || []).map((p) => p.total), smooth: true,
      itemStyle: { color: '#60a5fa' }, areaStyle: { opacity: 0.1 },
      markLine: { data: [{ yAxis: base, name: '基准' }], lineStyle: { color: '#34d399', type: 'dashed' } },
    }],
  }
})

async function loadSensitivity() {
  try { sens.value = await comprehensiveApi.sensitivity(variable.value) } catch (e) { console.error(e) }
}

onMounted(async () => {
  try {
    sim.value = await comprehensiveApi.simulation()
    await loadSensitivity()
    await loadRecipe()
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.sens-ctrl { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
.sens-ctrl label { color: var(--dim); font-size: 0.85rem; }
.sens-ctrl select { background: var(--glass2); border: 1px solid var(--border); border-radius: 6px; color: var(--text); padding: 4px 8px; }
</style>
