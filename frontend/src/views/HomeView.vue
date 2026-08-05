<template>
  <div class="kpi-grid">
    <KpiCard icon="🔥" :value="kpi.total_heats" label="总炉数" :delay="0.1" />
    <KpiCard icon="🔩" :value="kpi.steel_grade_count" label="钢种数" :delay="0.2" />
    <KpiCard icon="📅" :value="kpi.coverage_days" label="覆盖天数" suffix="天" :delay="0.3" />
    <KpiCard icon="✅" :value="kpi.overall_compliance_rate" label="总符合率" suffix="%" :decimals="2" :delay="0.4" />
    <KpiCard icon="♻️" :value="kpi.scrap_total_weight" label="废钢总量(吨)" :delay="0.5" />
    <KpiCard icon="🔬" :value="kpi.mech_samples" label="力学样本" :delay="0.6" />
  </div>

  <SectionPanel id="home-summary" title="三主线速览" icon="📊">
    <div class="charts">
      <ChartCard title="质量 · 各工序符合率">
        <EChart :option="complianceOption" />
      </ChartCard>
      <ChartCard title="成本 · 直接成本结构">
        <EChart :option="costOption" />
      </ChartCard>
      <ChartCard title="效率 · 班组炉数">
        <EChart :option="teamOption" />
      </ChartCard>
    </div>
    <p class="section-hint">点击顶部导航进入各主线看板查看完整分析。</p>
  </SectionPanel>

  <SectionPanel id="home-data" title="数据来源与口径" icon="📚">
    <div class="stats">
      <StatCard label="数据来源" :rows="[
        { k: '炼钢工艺执行', v: '7 sheet · 8055炉' },
        { k: '废钢料型', v: '138钢种 · 4582炉' },
        { k: 'SWRCH22A', v: '轧钢段全流程' },
        { k: '价格', v: 'SMM 5种 + 估算' },
      ]" />
      <StatCard label="关键确认点" :rows="[
        { k: '符合率口径', v: 'judge非null为判定', cls: 'v' },
        { k: '废钢总炉数', v: '4582炉(修正demo)', cls: 'v' },
        { k: '板坯/方坯', v: '与汇总吻合✓', cls: 'pass-good' },
        { k: '转炉口径', v: '待确认', cls: 'pass-warn' },
      ]" />
      <StatCard label="生产时间范围" :rows="[
        { k: '炼钢', v: kpi.date_from ? kpi.date_from.slice(0, 10) : '-' },
        { k: '至', v: kpi.date_to ? kpi.date_to.slice(0, 10) : '-' },
      ]" />
    </div>
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import KpiCard from '@/components/cards/KpiCard.vue'
import StatCard from '@/components/cards/StatCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import EChart from '@/components/charts/EChart.vue'
import { efficiencyApi, overviewApi, qualityApi } from '@/api/modules'

const kpi = ref({})
const compliance = ref([])
const cost = ref({ total_scrap_cost: 0, total_alloy_cost: 0 })
const team = ref([])

const complianceOption = computed(() => {
  const d = compliance.value.filter((x) => x.process !== '合计')
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}: ${p[0].value}%` },
    xAxis: { type: 'category', data: d.map((x) => x.process), axisLabel: { interval: 0 } },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      {
        type: 'bar',
        data: d.map((x) => ({
          value: x.rate,
          itemStyle: { color: x.rate >= 95 ? '#34d399' : x.rate >= 80 ? '#fbbf24' : '#f87171' },
        })),
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      },
    ],
  }
})

const costOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie', radius: ['40%', '65%'],
      data: [
        { name: '废钢成本', value: cost.value.total_scrap_cost },
        { name: '合金成本', value: cost.value.total_alloy_cost },
      ],
      label: { formatter: '{b}\n{d}%', color: '#94a3b8' },
    },
  ],
}))

const teamOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: team.value.map((t) => t.team + '班') },
  yAxis: { type: 'value', name: '炉数' },
  series: [{ type: 'bar', data: team.value.map((t) => t.heats), itemStyle: { borderRadius: [4, 4, 0, 0] } }],
}))

onMounted(async () => {
  try {
    const [k, c, co, t] = await Promise.all([
      overviewApi.kpi(),
      qualityApi.complianceOverview(),
      overviewApi.directCost(),
      efficiencyApi.heatCountByTeam(),
    ])
    kpi.value = k
    compliance.value = c
    cost.value = co
    team.value = t
  } catch (e) {
    console.error(e)
  }
})
</script>
