<template>
  <!-- Hero -->
  <div class="hero">
    <div class="hero-left">
      <div class="hero-icon"><Icon name="zap" :size="32" /></div>
      <div><h1 class="hero-title">效率总览</h1><p class="hero-sub">冶炼周期 · 班组产能 · 设备分析</p></div>
    </div>
    <div class="hero-stats">
      <div class="stat-pill"><span class="stat-val primary">{{ totalHeats }}</span><span class="stat-lbl">总炉数</span></div>
      <div class="stat-pill"><span class="stat-val primary">{{ teams.length }}</span><span class="stat-lbl">班组数</span></div>
      <div class="stat-pill"><span class="stat-val primary">{{ equipment.length }}</span><span class="stat-lbl">设备数</span></div>
      <div class="stat-pill"><span class="stat-val warn">{{ bottleneck }}</span><span class="stat-lbl">瓶颈工序(min)</span></div>
    </div>
  </div>

  <!-- 视角切换 -->
  <div class="toolbar">
    <div class="view-switch">
      <button v-for="v in views" :key="v.key" :class="{ active: view === v.key }" @click="view = v.key"><Icon :name="v.icon" :size="16" /> {{ v.label }}</button>
    </div>
    <span class="hint">点击卡片下钻详情</span>
  </div>

  <!-- 卡片网格 -->
  <div class="card-grid">
    <div v-for="c in cards" :key="c.key" class="q-card" @click="openDetail(c)">
      <div class="q-card-head">
        <span class="q-card-name">{{ c.key }}</span>
        <span class="q-card-badge" :class="c.badgeClass">{{ c.badge }}</span>
      </div>
      <div class="q-card-rate" :class="c.rateClass">{{ c.value }}</div>
      <div class="q-card-meta">{{ c.sub }}</div>
      <div class="q-card-bar"><div class="bar-fill" :class="c.barClass" :style="{ width: c.bar + '%' }"></div></div>
    </div>
  </div>

  <!-- Modal -->
  <div v-if="modal.open" class="modal-mask" @click.self="modal.open = false">
    <div class="modal-box">
      <div class="modal-head"><span class="modal-title">{{ modal.title }}</span><button class="modal-close" @click="modal.open = false">✕</button></div>
      <div class="modal-tabs"><button v-for="t in ['概览', '明细']" :key="t" :class="{ active: modal.tab === t }" @click="modal.tab = t">{{ t }}</button></div>
      <div class="modal-body">
        <div v-if="modal.tab === '概览'" class="modal-stats">
          <div class="m-stat" v-for="s in modal.stats" :key="s.lbl"><div class="m-stat-val" :class="s.cls">{{ s.val }}</div><div class="m-stat-lbl">{{ s.lbl }}</div></div>
        </div>
        <div v-if="modal.tab === '明细'">
          <div class="tbl-wrap">
            <table class="v2-table">
              <thead><tr><th v-for="h in modal.cols" :key="h">{{ h }}</th></tr></thead>
              <tbody><tr v-for="(r, i) in modal.rows" :key="i"><td v-for="(h, j) in modal.cols" :key="h" :class="{ mono: j === 0 }">{{ r[j] }}</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Icon from '@/components/common/Icon.vue'
import { efficiencyApi } from '@/api/modules'

const duration = ref([])
const teams = ref([])
const equipment = ref([])
const view = ref('process')
const views = [
  { key: 'process', icon: 'building', label: '按工序' },
  { key: 'team', icon: 'users', label: '按班组' },
  { key: 'equipment', icon: 'wrench', label: '按设备' },
]

const procMap = computed(() => {
  const map = {}
  for (const d of duration.value) {
    if (!map[d.process]) map[d.process] = { process: d.process, items: [], maxAvg: 0, maxInd: '' }
    map[d.process].items.push(d)
    if (d.avg > map[d.process].maxAvg) { map[d.process].maxAvg = d.avg; map[d.process].maxInd = d.indicator }
  }
  return Object.values(map)
})

const totalHeats = computed(() => teams.value.reduce((s, t) => s + t.heats, 0))
const bottleneck = computed(() => procMap.value.length ? Math.round(Math.max(...procMap.value.map((p) => p.maxAvg))) : 0)

const cards = computed(() => {
  if (view.value === 'process') return procMap.value.map((p) => ({
    key: p.process, value: Math.round(p.maxAvg) + 'min', badge: p.items.length + '指标',
    sub: `瓶颈: ${p.maxInd} (${Math.round(p.maxAvg)}min)`, bar: Math.min(100, p.maxAvg / 300 * 100),
    badgeClass: 'warn', rateClass: 'warn', barClass: 'warn', _proc: p,
  }))
  if (view.value === 'team') return teams.value.map((t) => ({
    key: t.team + '班', value: t.rate + '%', badge: t.heats + '炉', sub: `${t.heats}炉 · 符合率${t.rate}%`, bar: t.rate,
    badgeClass: t.rate >= 90 ? 'good' : t.rate >= 80 ? 'warn' : 'bad', rateClass: t.rate >= 90 ? 'good' : t.rate >= 80 ? 'warn' : 'bad',
    barClass: t.rate >= 90 ? 'good' : t.rate >= 80 ? 'warn' : 'bad', _team: t,
  }))
  return equipment.value.map((e) => ({
    key: `${e.process}·${e.equipment}`, value: e.heats + '炉', badge: e.rate + '%', sub: `${e.process} · ${e.heats}炉 · 符合率${e.rate}%`, bar: e.rate,
    badgeClass: e.rate >= 90 ? 'good' : e.rate >= 80 ? 'warn' : 'bad', rateClass: 'primary', barClass: e.rate >= 90 ? 'good' : 'warn', _equip: e,
  }))
})

const modal = ref({ open: false, title: '', stats: [], cols: [], rows: [], tab: '概览' })

function openDetail(c) {
  let stats = [], cols = [], rows = []
  if (view.value === 'process') {
    const p = c._proc
    stats = [{ val: Math.round(p.maxAvg) + 'min', lbl: '瓶颈时长', cls: 'warn' }, { val: p.items.length, lbl: '指标数', cls: 'primary' }]
    cols = ['指标', '均值(min)', '最小', 'P99', '样本']
    rows = p.items.map((d) => [d.indicator, d.avg, d.min, d.p99, d.n])
  } else if (view.value === 'team') {
    const t = c._team
    stats = [{ val: t.heats, lbl: '炉数', cls: 'primary' }, { val: t.rate + '%', lbl: '符合率', cls: t.rate >= 90 ? 'good' : 'warn' }]
    cols = ['班组', '炉数', '判定', '命中', '符合率']
    rows = [[t.team, t.heats, t.judged, t.hit, t.rate + '%']]
  } else {
    const e = c._equip
    stats = [{ val: e.heats, lbl: '炉数', cls: 'primary' }, { val: e.rate + '%', lbl: '符合率', cls: e.rate >= 90 ? 'good' : 'warn' }]
    cols = ['工序', '设备', '炉数', '符合率']
    rows = [[e.process, e.equipment, e.heats, e.rate + '%']]
  }
  modal.value = { open: true, title: c.key, stats, cols, rows, tab: '概览' }
}

onMounted(async () => {
  try {
    const [d, t, eq] = await Promise.all([efficiencyApi.durationStats(), efficiencyApi.heatCountByTeam(), efficiencyApi.equipmentOutput()])
    duration.value = d
    teams.value = t
    equipment.value = eq
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.hero { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.hero-left { display: flex; align-items: center; gap: 14px; }
.hero-icon { font-size: 2rem; }
.hero-title { font-size: 1.3rem; font-weight: 900; color: #0F172A; margin: 0; }
.hero-sub { font-size: 0.78rem; color: #475569; margin: 0; }
.hero-stats { display: flex; gap: 12px; }
.stat-pill { display: flex; flex-direction: column; align-items: center; gap: 2px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 18px; min-width: 80px; }
.stat-val { font-size: 1.4rem; font-weight: 900; font-family: ui-monospace, monospace; }
.stat-val.primary { color: #0284C7; }
.stat-val.warn { color: #D97706; }
.stat-lbl { font-size: 0.68rem; color: #475569; font-weight: 600; }
.toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.view-switch { display: flex; gap: 4px; background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 24px; padding: 4px; }
.view-switch button { background: none; border: none; color: #475569; padding: 8px 20px; border-radius: 20px; cursor: pointer; font-size: 0.82rem; font-weight: 700; transition: all 0.2s; }
.view-switch button.active { background: #fff; color: #0284C7; font-weight: 900; box-shadow: 0 2px 8px rgba(2,132,199,0.12); border: 1px solid #BAE6FD; }
.hint { color: #94A3B8; font-size: 0.8rem; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.q-card { position: relative; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px; cursor: pointer; transition: all 0.25s; box-shadow: 0 1px 3px rgba(0,0,0,0.04); overflow: hidden; }
.q-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: #475569; transition: all 0.25s; }
.q-card:hover { transform: translateY(-4px); box-shadow: 0 16px 24px rgba(15,23,42,0.06); border-color: #CBD5E1; }
.q-card:hover::before { height: 4px; background: #0284C7; }
.q-card-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.q-card-name { font-size: 0.95rem; font-weight: 800; color: #0F172A; }
.q-card-badge { font-size: 0.65rem; padding: 2px 10px; border-radius: 12px; font-weight: 700; }
.q-card-badge.good { background: #ECFDF5; color: #047857; }
.q-card-badge.warn { background: #FFFBEB; color: #D97706; }
.q-card-badge.bad { background: #FEF2F2; color: #B91C1C; }
.q-card-rate { font-size: 1.6rem; font-weight: 900; font-family: ui-monospace, monospace; }
.q-card-rate.primary { color: #0284C7; }
.q-card-rate.good { color: #10B981; }
.q-card-rate.warn { color: #F59E0B; }
.q-card-meta { font-size: 0.75rem; color: #94A3B8; margin: 4px 0 10px; }
.q-card-bar { height: 5px; background: #F1F5F9; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s; }
.bar-fill.primary { background: linear-gradient(90deg, #0284C7, #38BDF8); }
.bar-fill.good { background: #10B981; }
.bar-fill.warn { background: #F59E0B; }
.modal-mask { position: fixed; inset: 0; background: rgba(15,23,42,0.65); z-index: 500; display: flex; align-items: center; justify-content: center; backdrop-filter: blur(8px); }
.modal-box { background: #fff; border: 1px solid #E2E8F0; border-radius: 18px; width: 80%; max-width: 900px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 20px 40px -12px rgba(15,23,42,0.12); }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 18px 28px; background: linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #0369A1 100%); color: #fff; border-radius: 18px 18px 0 0; }
.modal-title { font-size: 1.1rem; font-weight: 800; }
.modal-close { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.1); color: #94A3B8; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; transition: all 0.2s; }
.modal-close:hover { background: #EF4444; color: #fff; transform: rotate(90deg); }
.modal-tabs { display: flex; gap: 4px; padding: 12px 24px; border-bottom: 1px solid #E2E8F0; background: #fff; }
.modal-tabs button { background: none; border: none; color: #475569; padding: 10px 20px; cursor: pointer; font-size: 0.85rem; font-weight: 600; border-bottom: 2px solid transparent; transition: all 0.2s; }
.modal-tabs button.active { color: #0284C7; font-weight: 800; border-bottom: 2px solid #0284C7; }
.modal-body { padding: 24px; overflow-y: auto; background: #F8FAFC; flex: 1; }
.modal-stats { display: flex; gap: 32px; justify-content: center; padding: 20px; }
.m-stat { text-align: center; }
.m-stat-val { font-size: 1.8rem; font-weight: 900; font-family: ui-monospace, monospace; }
.m-stat-val.primary { color: #0284C7; }
.m-stat-val.good { color: #10B981; }
.m-stat-val.warn { color: #F59E0B; }
.m-stat-lbl { font-size: 0.75rem; color: #94A3B8; margin-top: 4px; font-weight: 600; }
.tbl-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid #E2E8F0; }
.v2-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #fff; }
.v2-table th { background: #F0F9FF; color: #0369A1; padding: 10px 12px; text-align: left; font-weight: 700; white-space: nowrap; border-bottom: 1px solid #E2E8F0; }
.v2-table td { padding: 8px 12px; border-bottom: 1px solid #F1F5F9; color: #475569; }
.v2-table tr:hover td { background: #F8FAFC; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
</style>
