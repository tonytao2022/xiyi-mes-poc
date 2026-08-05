<template>
  <!-- Hero -->
  <div class="hero">
    <div class="hero-left">
      <div <div class="hero-icon"><Icon name="dollar" :size="32" /></div>
      <div><h1 class="hero-title">成本总览</h1><p class="hero-sub">废钢配料 · 合金投入 · 成本结构</p></div>
    </div>
    <div class="hero-stats">
      <div class="stat-pill"><span class="stat-val primary">{{ fmt(scrap.total_weight) }}</span><span class="stat-lbl">废钢总量(吨)</span></div>
      <div class="stat-pill"><span class="stat-val primary">{{ scrap.total_heats }}</span><span class="stat-lbl">总炉数</span></div>
      <div class="stat-pill"><span class="stat-val primary">{{ scrap.steel_grade_count }}</span><span class="stat-lbl">钢种数</span></div>
      <div class="stat-pill"><span class="stat-val primary">{{ alloy.length }}</span><span class="stat-lbl">合金种类</span></div>
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
        <span class="q-card-badge" :class="badgeClass(c)">{{ c.badge }}</span>
      </div>
      <div class="q-card-rate primary">{{ c.value }}</div>
      <div class="q-card-meta">{{ c.sub }}</div>
      <div class="q-card-bar"><div class="bar-fill primary" :style="{ width: c.bar + '%' }"></div></div>
    </div>
  </div>

  <!-- 下钻 Modal -->
  <div v-if="modal.open" class="modal-mask" @click.self="modal.open = false">
    <div class="modal-box">
      <div class="modal-head"><span class="modal-title">{{ modal.title }}</span><button class="modal-close" @click="modal.open = false">✕</button></div>
      <div class="modal-tabs">
        <button v-for="t in ['概览', '明细']" :key="t" :class="{ active: modal.tab === t }" @click="modal.tab = t">{{ t }}</button>
      </div>
      <div class="modal-body">
        <div v-if="modal.tab === '概览'" class="modal-stats">
          <div class="m-stat"><div class="m-stat-val primary">{{ modal.card.value }}</div><div class="m-stat-lbl">{{ modal.card.valueLabel }}</div></div>
          <div class="m-stat"><div class="m-stat-val primary">{{ modal.card.sub }}</div><div class="m-stat-lbl">{{ modal.card.subLabel }}</div></div>
        </div>
        <div v-if="modal.tab === '明细'">
          <div class="tbl-wrap">
            <table class="v2-table">
              <thead><tr><th v-for="h in modal.cols" :key="h">{{ h }}</th></tr></thead>
              <tbody>
                <tr v-for="(r, i) in modal.rows" :key="i"><td v-for="(h, j) in modal.cols" :key="h" :class="{ mono: j === 0 }">{{ r[j] }}</td></tr>
              </tbody>
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
import { costApi, overviewApi } from '@/api/modules'

const scrap = ref({ steel_grade_count: 0, total_weight: 0, total_heats: 0, types: [] })
const byGrade = ref([])
const alloy = ref([])
const view = ref('type')
const views = [
  { key: 'type', icon: 'recycle', label: '按料型' },
  { key: 'grade', icon: 'layers', label: '按钢种' },
  { key: 'alloy', icon: 'cog', label: '按合金' },
]

const fmt = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })

const cards = computed(() => {
  if (view.value === 'type') return (scrap.value.types || []).slice(0, 12).map((t) => ({
    key: t.scrap_type, value: fmt(t.weight) + '吨', badge: t.pct + '%', sub: `占比 ${t.pct}% · ${t.used_grades}钢种`, bar: t.pct,
  }))
  if (view.value === 'grade') return byGrade.value.map((g) => ({
    key: g.steel_grade, value: fmt(g.total_weight) + '吨', badge: g.heats + '炉', sub: `${g.heats} 炉`, bar: Math.min(100, g.total_weight / 30000 * 100),
  }))
  return alloy.value.slice(0, 12).map((a) => ({
    key: a.alloy, value: a.usage_rate + '%', badge: a.used_count + '炉', sub: `使用率 ${a.usage_rate}% · 均值${a.avg_amount}`, bar: a.usage_rate,
  }))
})

function badgeClass(c) { return c.bar >= 50 ? 'good' : c.bar >= 20 ? 'warn' : 'bad' }

const modal = ref({ open: false, title: '', card: {}, cols: [], rows: [], tab: '概览' })

function openDetail(c) {
  let cols = [], rows = []
  if (view.value === 'type') {
    cols = ['料型', '用量(吨)', '占比', '使用钢种数', '每炉均值']
    const t = (scrap.value.types || []).find((x) => x.scrap_type === c.key) || {}
    rows = [[t.scrap_type, fmt(t.weight), t.pct + '%', t.used_grades, fmt(t.avg_per_grade)]]
  } else if (view.value === 'grade') {
    cols = ['钢种', '总重量(吨)', '炉数']
    const g = byGrade.value.find((x) => x.steel_grade === c.key) || {}
    rows = [[g.steel_grade, fmt(g.total_weight), g.heats]]
  } else {
    cols = ['合金', '使用炉数', '使用率', '均值', '最小', '最大', '符合率']
    const a = alloy.value.find((x) => x.alloy === c.key) || {}
    rows = [[a.alloy, a.used_count, a.usage_rate + '%', a.avg_amount, a.min_amount, a.max_amount, a.rate + '%']]
  }
  modal.value = { open: true, title: c.key, card: { ...c, valueLabel: '主指标', subLabel: '辅助' }, cols, rows, tab: '概览' }
}

onMounted(async () => {
  try {
    const [s, g, a] = await Promise.all([costApi.scrapOverview(), costApi.scrapByGrade(20), costApi.alloyOverview()])
    scrap.value = s
    byGrade.value = g
    alloy.value = a
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
.q-card-meta { font-size: 0.75rem; color: #94A3B8; margin: 4px 0 10px; }
.q-card-bar { height: 5px; background: #F1F5F9; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.6s; }
.bar-fill.primary { background: linear-gradient(90deg, #0284C7, #38BDF8); }
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
.m-stat-lbl { font-size: 0.75rem; color: #94A3B8; margin-top: 4px; font-weight: 600; }
.tbl-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid #E2E8F0; }
.v2-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #fff; }
.v2-table th { background: #F0F9FF; color: #0369A1; padding: 10px 12px; text-align: left; font-weight: 700; white-space: nowrap; border-bottom: 1px solid #E2E8F0; }
.v2-table td { padding: 8px 12px; border-bottom: 1px solid #F1F5F9; color: #475569; }
.v2-table tr:hover td { background: #F8FAFC; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
</style>
