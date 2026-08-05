<template>
  <div class="kpi-grid">
    <KpiCard icon="🔥" :value="heating.record_count" label="加热记录" :delay="0.1" />
    <KpiCard icon="⚙️" :value="rollTotal" label="轧制记录" :delay="0.2" />
    <KpiCard icon="👥" :value="team.length" label="班组数" :delay="0.3" />
    <KpiCard icon="📅" :value="shift.length" label="轧制班次" :delay="0.4" />
  </div>

  <SectionPanel id="e-duration" title="各工序时长分布" icon="⏱️">
    <p class="section-hint">时长类工艺指标均值（分钟），覆盖吹氩/精炼/镇静/真空循环等。</p>
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="durationOption" height="440px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="e-team" title="班组炉数与符合率" icon="👥">
    <div class="charts">
      <ChartCard title="炼钢班组产能与质量">
        <EChart :option="teamOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="e-shift" title="轧钢班次产量与温度" icon="🌡️">
    <div class="charts">
      <ChartCard title="班次产量与开轧温度（SWRCH22A）" :full="true">
        <EChart :option="shiftOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="e-heating" title="加热工艺统计（SWRCH22A）" icon="🔥">
    <div class="stats">
      <StatCard label="总加热时间(min)" :rows="[
        { k: '均值', v: heating.total_heat_time?.avg },
        { k: '范围', v: `${heating.total_heat_time?.min}~${heating.total_heat_time?.max}` },
      ]" />
      <StatCard label="预热段温度(℃)" :rows="[{ k: '均值', v: heating.preheat_temp?.avg }]" />
      <StatCard label="加热段温度(℃)" :rows="[{ k: '均值', v: heating.heat_section_temp?.avg }]" />
      <StatCard label="均热温度(℃)" :rows="[{ k: '均值', v: heating.soak_temp?.avg }]" />
      <StatCard label="出炉温度(℃)" :rows="[{ k: '均值', v: heating.out_temp?.avg }]" />
    </div>
  </SectionPanel>

  <SectionPanel id="e-casting" title="连铸关键参数（对标 demo S2/S3）" icon="📦">
    <div class="cast-ctrl">
      <label>工序：
        <select v-model="castProcess" @change="loadCasting">
          <option value="板坯">板坯</option>
          <option value="方坯">方坯</option>
        </select>
      </label>
    </div>
    <DataTable :columns="castCols" :rows="casting" :scroll-x="true" />
  </SectionPanel>

  <SectionPanel id="e-equipment" title="设备产量占比（对标 demo S7）" icon="🏭">
    <div class="charts">
      <ChartCard title="各设备炉数占比">
        <EChart :option="equipOption" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="e-trend" title="工艺趋势时序（对标 demo S8）" icon="📈">
    <div class="cast-ctrl">
      <label>参数：
        <select v-model="trendIndicator" @change="loadTrend">
          <option>中包过热度</option>
          <option>中包温度极差</option>
          <option>浇余</option>
          <option>总吹氩时长</option>
        </select>
      </label>
    </div>
    <div class="charts">
      <ChartCard :full="true">
        <EChart :option="trendOption" height="320px" />
      </ChartCard>
    </div>
  </SectionPanel>

  <SectionPanel id="e-insights" title="效率智能洞察（问题识别）" icon="💡">
    <p class="section-hint">系统自动识别瓶颈工序、时长异常波动、班组产能与质量差距等效率问题。</p>
    <InsightBlock :items="insights.items || []" />
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import KpiCard from '@/components/cards/KpiCard.vue'
import StatCard from '@/components/cards/StatCard.vue'
import ChartCard from '@/components/cards/ChartCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import EChart from '@/components/charts/EChart.vue'
import InsightBlock from '@/components/cards/InsightBlock.vue'
import { efficiencyApi } from '@/api/modules'

const duration = ref([])
const team = ref([])
const shift = ref([])
const heating = ref({ record_count: 0, total_heat_time: {}, preheat_temp: {}, heat_section_temp: {}, soak_temp: {}, out_temp: {} })
const insights = ref({})
const casting = ref([])
const castProcess = ref('板坯')
const equipment = ref([])
const trend = ref({ times: [], values: [] })
const trendIndicator = ref('中包过热度')

const castCols = [
  { key: 'indicator', title: '参数', mono: true },
  { key: 'judged', title: '判定' },
  { key: 'hit', title: '命中' },
  { key: 'rate', title: '符合率(%)', rate: true },
  { key: 'avg', title: '均值', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'min', title: '最小', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
  { key: 'max', title: '最大', format: (v) => (v == null ? '-' : Number(v).toFixed(1)) },
]
const equipOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}炉 ({d}%)' },
  legend: { bottom: 0 },
  series: [{ type: 'pie', radius: ['40%', '65%'], data: equipment.value.map((e) => ({ name: e.equipment, value: e.heats })) }],
}))
const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: trend.value.times, axisLabel: { rotate: 45, fontSize: 9 } },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: trend.value.values, smooth: true, itemStyle: { color: '#60a5fa' }, areaStyle: { opacity: 0.1 } }],
}))
async function loadCasting() { try { casting.value = await efficiencyApi.castingParams(castProcess.value) } catch (e) { console.error(e) } }
async function loadTrend() { try { trend.value = await efficiencyApi.trendSeries(trendIndicator.value) } catch (e) { console.error(e) } }

const rollTotal = computed(() => shift.value.reduce((s, x) => s + (x.records || 0), 0))

const PROC_COLOR = { 转炉: '#60a5fa', 精炼: '#a78bfa', 真空: '#22d3ee', 板坯: '#34d399', 方坯: '#fbbf24', 合金: '#f87171' }

const durationOption = computed(() => {
  const d = duration.value.slice().reverse()
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p) => {
        const i = p[0].dataIndex
        return `${d[i].process} · ${d[i].indicator}<br/>均值 ${d[i].avg}${d[i].unit} (n=${d[i].n})<br/>范围 ${d[i].min}~${d[i].max}`
      },
    },
    grid: { left: '28%' },
    xAxis: { type: 'value', name: '分钟' },
    yAxis: { type: 'category', data: d.map((s) => `${s.process}·${s.indicator}`) },
    series: [
      {
        type: 'bar',
        data: d.map((s) => ({ value: s.avg, itemStyle: { color: PROC_COLOR[s.process] || '#60a5fa' } })),
        itemStyle: { borderRadius: [0, 4, 4, 0] },
      },
    ],
  }
})

const teamOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['炉数', '符合率'] },
  xAxis: { type: 'category', data: team.value.map((t) => t.team + '班') },
  yAxis: [
    { type: 'value', name: '炉数' },
    { type: 'value', name: '符合率%', max: 100, axisLabel: { formatter: '{value}%' } },
  ],
  series: [
    { name: '炉数', type: 'bar', data: team.value.map((t) => t.heats), itemStyle: { borderRadius: [4, 4, 0, 0] } },
    { name: '符合率', type: 'line', yAxisIndex: 1, data: team.value.map((t) => t.rate), itemStyle: { color: '#fbbf24' } },
  ],
}))

const shiftOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['产量(吨)', '开轧温度', '吐丝温度'] },
  xAxis: { type: 'category', data: shift.value.map((s) => s.shift + '班') },
  yAxis: [
    { type: 'value', name: '产量(吨)' },
    { type: 'value', name: '温度(℃)', min: 800, max: 1000 },
  ],
  series: [
    { name: '产量(吨)', type: 'bar', data: shift.value.map((s) => s.total_weight), itemStyle: { borderRadius: [4, 4, 0, 0] } },
    { name: '开轧温度', type: 'line', yAxisIndex: 1, data: shift.value.map((s) => s.avg_start_temp), itemStyle: { color: '#f87171' } },
    { name: '吐丝温度', type: 'line', yAxisIndex: 1, data: shift.value.map((s) => s.avg_laying_temp), itemStyle: { color: '#34d399' } },
  ],
}))

onMounted(async () => {
  try {
    const [d, t, s, h, ins, eq] = await Promise.all([
      efficiencyApi.durationStats(),
      efficiencyApi.heatCountByTeam(),
      efficiencyApi.rollingShiftOutput(),
      efficiencyApi.heatingStats(),
      efficiencyApi.insights(),
      efficiencyApi.equipmentOutput(),
    ])
    duration.value = d
    team.value = t
    shift.value = s
    heating.value = h
    insights.value = ins
    equipment.value = eq
    await loadCasting()
    await loadTrend()
  } catch (e) {
    console.error(e)
  }
})
</script>
