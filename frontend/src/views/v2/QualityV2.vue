<template>
  <!-- Hero 概况条 -->
  <div class="hero">
    <div class="hero-left">
      <div <div class="hero-icon"><Icon name="target" :size="32" /></div>
      <div>
        <h1 class="hero-title">质量总览</h1>
        <p class="hero-sub">符合率 · 多维视角 · 卡片下钻</p>
      </div>
    </div>
    <div class="hero-stats">
      <div class="stat-pill"><span class="stat-val" :class="rateClass(overallRate)">{{ overallRate }}%</span><span class="stat-lbl">总符合率</span></div>
      <div class="stat-pill"><span class="stat-val danger">{{ severe }}</span><span class="stat-lbl">严重</span></div>
      <div class="stat-pill"><span class="stat-val warning">{{ warning }}</span><span class="stat-lbl">警告</span></div>
      <div class="stat-pill"><span class="stat-val primary">{{ totalHeats }}</span><span class="stat-lbl">总炉数</span></div>
    </div>
  </div>

  <!-- 视角切换 -->
  <div class="toolbar">
    <div class="view-switch">
      <button v-for="v in views" :key="v.key" :class="{ active: view === v.key }" @click="view = v.key">
        <Icon :name="v.icon" :size="16" /> {{ v.label }}
      </button>
    </div>
    <span class="hint">点击卡片下钻详情</span>
  </div>

  <!-- 卡片网格 -->
  <div class="card-grid">
    <div v-for="c in cards" :key="c.key" class="q-card" @click="openDetail(c)">
      <div class="q-card-head">
        <span class="q-card-name">{{ c.key }}</span>
        <span class="q-card-badge" :class="rateClass(c.rate)">{{ c.rate >= 95 ? '优' : c.rate >= 80 ? '良' : '差' }}</span>
      </div>
      <div class="q-card-rate" :class="rateClass(c.rate)">{{ c.rate }}%</div>
      <div class="q-card-meta">{{ c.heats }} 炉 · 判定 {{ c.judged }}</div>
      <div class="q-card-bar"><div class="bar-fill" :class="rateClass(c.rate)" :style="{ width: c.rate + '%' }"></div></div>
    </div>
  </div>

  <!-- 下钻 Modal -->
  <div v-if="modal.open" class="modal-mask" @click.self="modal.open = false">
    <div class="modal-box">
      <div class="modal-head">
        <span class="modal-title">{{ modal.title }}</span>
        <button class="modal-close" @click="modal.open = false">✕</button>
      </div>
      <div class="modal-tabs">
        <button v-for="t in ['概览', '短板指标', '趋势']" :key="t" :class="{ active: modal.tab === t }" @click="modal.tab = t">{{ t }}</button>
      </div>
      <div class="modal-body">
        <div v-if="modal.tab === '概览'" class="modal-stats">
          <div class="m-stat"><div class="m-stat-val" :class="rateClass(modal.card.rate)">{{ modal.card.rate }}%</div><div class="m-stat-lbl">符合率</div></div>
          <div class="m-stat"><div class="m-stat-val primary">{{ modal.card.hit }}/{{ modal.card.judged }}</div><div class="m-stat-lbl">命中/判定</div></div>
          <div class="m-stat"><div class="m-stat-val primary">{{ modal.card.heats }}</div><div class="m-stat-lbl">炉数</div></div>
        </div>
        <div v-if="modal.tab === '短板指标'">
          <p class="hint">{{ modal.title }} 最差指标 Top10</p>
          <div class="tbl-wrap">
            <table class="v2-table">
              <thead><tr><th>指标</th><th>工序</th><th>判定</th><th>命中</th><th>符合率</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in modal.indicators" :key="i">
                  <td class="mono">{{ r.name }}</td><td>{{ r.process }}</td><td>{{ r.judged }}</td><td>{{ r.hit }}</td>
                  <td :class="rateClass(r.rate)">{{ r.rate }}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-if="modal.tab === '趋势'">
          <EChart v-if="modal.trend.length" :option="trendOption" theme="mes-light" height="300px" />
          <div v-else class="empty">该维度暂无趋势数据（工序视角可查看）</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Icon from '@/components/common/Icon.vue'
import EChart from '@/components/charts/EChart.vue'
import { overviewApi, qualityApi } from '@/api/modules'

const overview = ref([])
const byGrade = ref([])
const byTeam = ref([])
const insights = ref({ summary: {} })
const totalHeats = ref(0)
const view = ref('process')
const views = [
  { key: 'process', icon: 'building', label: '按工序' },
  { key: 'steel_grade', icon: 'layers', label: '按钢种' },
  { key: 'team', icon: 'users', label: '按班组' },
]

const overallRate = computed(() => (overview.value.find((x) => x.process === '合计') || {}).rate || 0)
const severe = computed(() => insights.value.summary?.严重 || 0)
const warning = computed(() => insights.value.summary?.警告 || 0)
const cards = computed(() => {
  if (view.value === 'process') return overview.value.filter((x) => x.process !== '合计')
  if (view.value === 'steel_grade') return byGrade.value
  return byTeam.value
})

const modal = ref({ open: false, title: '', card: {}, indicators: [], trend: [], tab: '概览' })
const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: modal.value.trend.map((t) => t.time), axisLabel: { rotate: 45, fontSize: 9 } },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: modal.value.trend.map((t) => t.value), smooth: true, areaStyle: { opacity: 0.1 } }],
}))

function rateClass(r) { return r >= 95 ? 'good' : r >= 80 ? 'warn' : 'bad' }

async function openDetail(c) {
  modal.value = { open: true, title: c.key, card: c, indicators: [], trend: [], tab: '概览' }
  if (view.value === 'process') {
    try {
      const [inds, trend] = await Promise.all([
        qualityApi.indicatorRanking(c.key, 'asc'),
        qualityApi.rollingTemperatureSeries(60),
      ])
      modal.value.indicators = inds
      modal.value.trend = trend.times.map((t, i) => ({ time: t, value: trend.values[i] }))
    } catch (e) { console.error(e) }
  } else {
    try { modal.value.indicators = await qualityApi.indicatorRanking(null, 'asc') } catch (e) { console.error(e) }
  }
}

onMounted(async () => {
  try {
    const [ov, ig, it, ins, kpi] = await Promise.all([
      qualityApi.complianceOverview(),
      qualityApi.complianceByDimension('steel_grade'),
      qualityApi.complianceByDimension('team'),
      qualityApi.insights(),
      overviewApi.kpi(),
    ])
    overview.value = ov
    byGrade.value = ig
    byTeam.value = it
    insights.value = ins
    totalHeats.value = kpi.total_heats
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
/* === Hero === */
.hero { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.hero-left { display: flex; align-items: center; gap: 14px; }
.hero-icon { font-size: 2rem; }
.hero-title { font-size: 1.3rem; font-weight: 900; color: #0F172A; letter-spacing: 0.3px; margin: 0; }
.hero-sub { font-size: 0.78rem; color: #475569; margin: 0; }
.hero-stats { display: flex; gap: 12px; }
.stat-pill { display: flex; flex-direction: column; align-items: center; gap: 2px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 18px; min-width: 80px; transition: all 0.15s; }
.stat-pill:hover { background: #F1F5F9; border-color: #CBD5E1; }
.stat-val { font-size: 1.4rem; font-weight: 900; font-family: ui-monospace, monospace; color: #0284C7; }
.stat-val.good { color: #047857; }
.stat-val.warn { color: #D97706; }
.stat-val.bad { color: #B91C1C; }
.stat-val.danger { color: #B91C1C; }
.stat-val.warning { color: #D97706; }
.stat-val.primary { color: #0284C7; }
.stat-lbl { font-size: 0.68rem; color: #475569; font-weight: 600; }

/* === Toolbar === */
.toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.view-switch { display: flex; gap: 4px; background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 24px; padding: 4px; }
.view-switch button { background: none; border: none; color: #475569; padding: 8px 20px; border-radius: 20px; cursor: pointer; font-size: 0.82rem; font-weight: 700; transition: all 0.2s; }
.view-switch button.active { background: #fff; color: #0284C7; font-weight: 900; box-shadow: 0 2px 8px rgba(2,132,199,0.12); border: 1px solid #BAE6FD; }
.hint { color: #94A3B8; font-size: 0.8rem; }

/* === Card Grid === */
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.q-card { position: relative; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px; cursor: pointer; transition: all 0.25s; box-shadow: 0 1px 3px rgba(0,0,0,0.04); overflow: hidden; }
.q-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: #475569; transition: all 0.25s; }
.q-card:hover { transform: translateY(-4px); box-shadow: 0 16px 24px rgba(15,23,42,0.06), 0 4px 8px rgba(0,0,0,0.02); border-color: #CBD5E1; }
.q-card:hover::before { height: 4px; background: #0284C7; }
.q-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.q-card-name { font-size: 0.95rem; font-weight: 800; color: #0F172A; }
.q-card-badge { font-size: 0.65rem; padding: 2px 10px; border-radius: 12px; font-weight: 700; }
.q-card-badge.good { background: #ECFDF5; color: #047857; }
.q-card-badge.warn { background: #FFFBEB; color: #D97706; }
.q-card-badge.bad { background: #FEF2F2; color: #B91C1C; }
.q-card-rate { font-size: 2rem; font-weight: 900; font-family: ui-monospace, monospace; }
.q-card-rate.good { color: #10B981; }
.q-card-rate.warn { color: #F59E0B; }
.q-card-rate.bad { color: #DC2626; }
.q-card-meta { font-size: 0.75rem; color: #94A3B8; margin: 4px 0 10px; }
.q-card-bar { height: 5px; background: #F1F5F9; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s; }
.bar-fill.good { background: #10B981; }
.bar-fill.warn { background: #F59E0B; }
.bar-fill.bad { background: #DC2626; }

/* === Modal === */
.modal-mask { position: fixed; inset: 0; background: rgba(15,23,42,0.65); z-index: 500; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(8px); }
.modal-box { background: #fff; border: 1px solid #E2E8F0; border-radius: 18px; width: 80%; max-width: 900px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 20px 40px -12px rgba(15,23,42,0.12); }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 18px 28px; background: linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #0369A1 100%); color: #fff; border-bottom: 1px solid rgba(255,255,255,0.08); border-radius: 18px 18px 0 0; }
.modal-title { font-size: 1.1rem; font-weight: 800; letter-spacing: 0.3px; }
.modal-close { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); color: #94A3B8; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1rem; transition: all 0.2s; }
.modal-close:hover { background: #EF4444; border-color: #EF4444; color: #fff; transform: rotate(90deg); }
.modal-tabs { display: flex; gap: 4px; padding: 12px 24px; border-bottom: 1px solid #E2E8F0; background: #fff; }
.modal-tabs button { background: none; border: none; color: #475569; padding: 10px 20px; cursor: pointer; font-size: 0.85rem; font-weight: 600; border-bottom: 2px solid transparent; transition: all 0.2s; }
.modal-tabs button.active { color: #0284C7; font-weight: 800; border-bottom: 2px solid #0284C7; }
.modal-body { padding: 24px; overflow-y: auto; background: #F8FAFC; flex: 1; }
.modal-stats { display: flex; gap: 32px; justify-content: center; padding: 20px; }
.m-stat { text-align: center; }
.m-stat-val { font-size: 1.8rem; font-weight: 900; font-family: ui-monospace, monospace; color: #0284C7; }
.m-stat-val.good { color: #10B981; }
.m-stat-val.warn { color: #F59E0B; }
.m-stat-val.bad { color: #DC2626; }
.m-stat-val.primary { color: #0284C7; }
.m-stat-lbl { font-size: 0.75rem; color: #94A3B8; margin-top: 4px; font-weight: 600; }
.empty { color: #94A3B8; text-align: center; padding: 2rem; }

/* === v2 Table === */
.tbl-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid #E2E8F0; }
.v2-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #fff; }
.v2-table th { background: #F0F9FF; color: #0369A1; padding: 10px 12px; text-align: left; font-weight: 700; white-space: nowrap; border-bottom: 1px solid #E2E8F0; }
.v2-table td { padding: 8px 12px; border-bottom: 1px solid #F1F5F9; color: #475569; }
.v2-table tr:hover td { background: #F8FAFC; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
.good { color: #047857; }
.warn { color: #D97706; }
.bad { color: #B91C1C; }
</style>
