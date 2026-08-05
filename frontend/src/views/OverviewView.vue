<template>
  <div class="kpi-grid">
    <KpiCard icon="🔥" :value="kpi.total_heats" label="总炉数" :delay="0.1" />
    <KpiCard icon="🔩" :value="kpi.steel_grade_count" label="钢种数" :delay="0.2" />
    <KpiCard icon="📅" :value="kpi.coverage_days" label="覆盖天数" suffix="天" :delay="0.3" />
    <KpiCard icon="✅" :value="kpi.overall_compliance_rate" label="总符合率" suffix="%" :decimals="2" :delay="0.4" />
    <KpiCard icon="♻️" :value="kpi.scrap_total_weight" label="废钢总量(吨)" :delay="0.5" />
    <KpiCard icon="🔬" :value="kpi.mech_samples" label="力学样本" :delay="0.6" />
  </div>

  <SectionPanel id="overview-cost" title="直接成本估算（价格=估算值）" icon="💰">
    <div class="stats">
      <StatCard label="废钢成本" :rows="[{ k: '合计(元)', v: fmtMoney(cost.total_scrap_cost), cls: 'v big' }]" />
      <StatCard label="合金成本" :rows="[{ k: '合计(元)', v: fmtMoney(cost.total_alloy_cost), cls: 'v big' }]" />
      <StatCard label="直接成本合计" :rows="[{ k: '合计(元)', v: fmtMoney(cost.total_direct_cost), cls: 'v big' }]" />
      <StatCard label="成本结构" :rows="[
        { k: '废钢占比', v: scrapPct + '%' },
        { k: '合金占比', v: alloyPct + '%' },
      ]" />
    </div>
    <p class="section-hint">{{ cost.price_source }}</p>
    <div class="charts">
      <ChartCard title="合金成本 Top10" :full="true">
        <EChart :option="alloyChartOption" height="360px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="overview-insights" title="智能洞察与问题识别" icon="💡">
    <div class="stats" style="margin-bottom: 1rem">
      <StatCard label="问题识别汇总" :rows="[
        { k: '严重', v: insights.summary?.severe || 0, cls: 'pass-bad' },
        { k: '警告', v: insights.summary?.warning || 0, cls: 'pass-warn' },
        { k: '合计', v: insights.summary?.total || 0, cls: 'v' },
      ]" />
    </div>

    <h3 class="sub-title" v-if="insights.quality">🎯 质量</h3>
    <InsightBlock v-if="insights.quality" :items="insights.quality.items" />

    <h3 class="sub-title" v-if="insights.cost">💰 成本</h3>
    <InsightBlock v-if="insights.cost" :items="insights.cost.items" />

    <h3 class="sub-title" v-if="insights.efficiency">⚡ 效率</h3>
    <InsightBlock v-if="insights.efficiency" :items="insights.efficiency.items" />

    <h3 class="sub-title">🧭 优化优先级</h3>
    <div class="priority-list">
      <div v-for="(p, i) in insights.priority || []" :key="i" class="priority-item">
        <span class="p-num">{{ i + 1 }}</span>{{ p }}
      </div>
    </div>
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import KpiCard from '@/components/cards/KpiCard.vue'
import StatCard from '@/components/cards/StatCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import InsightBlock from '@/components/cards/InsightBlock.vue'
import EChart from '@/components/charts/EChart.vue'
import { overviewApi } from '@/api/modules'

const kpi = ref({})
const cost = ref({ scrap_cost: [], alloy_cost: [], total_scrap_cost: 0, total_alloy_cost: 0, total_direct_cost: 0, price_source: '' })
const insights = ref({})

const fmtMoney = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
const scrapPct = computed(() => {
  const t = cost.value.total_direct_cost || 1
  return ((cost.value.total_scrap_cost / t) * 100).toFixed(1)
})
const alloyPct = computed(() => {
  const t = cost.value.total_direct_cost || 1
  return ((cost.value.total_alloy_cost / t) * 100).toFixed(1)
})

const alloyChartOption = computed(() => {
  const top = (cost.value.alloy_cost || []).slice(0, 10).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p) => `${p[0].name}<br/>${fmtMoney(p[0].value)} 元` },
    grid: { left: '18%', right: '6%' },
    xAxis: { type: 'value', axisLabel: { formatter: (v) => (v / 1e6).toFixed(0) + 'M' } },
    yAxis: { type: 'category', data: top.map((a) => a.alloy) },
    series: [{ type: 'bar', data: top.map((a) => a.cost), itemStyle: { borderRadius: [0, 4, 4, 0] } }],
  }
})

onMounted(async () => {
  try {
    const [k, c, ins] = await Promise.all([
      overviewApi.kpi(),
      overviewApi.directCost(),
      overviewApi.insights(),
    ])
    kpi.value = k
    cost.value = c
    insights.value = ins
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.sub-title {
  margin: 1.2rem 0 0.6rem;
  font-size: 1rem;
  color: var(--accent2);
  font-weight: 600;
}
.priority-list { margin-top: 0.5rem; }
.priority-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--glass2);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--accent2);
  margin-bottom: 8px;
  font-size: 0.88rem;
  color: var(--text);
}
.p-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: var(--accent2);
  color: var(--bg);
  border-radius: 50%;
  font-size: 0.78rem;
  font-weight: 700;
  flex-shrink: 0;
}
</style>
