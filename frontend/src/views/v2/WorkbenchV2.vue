<template>
  <div class="workbench">
    <!-- Hero 概况条 -->
    <div class="hero">
      <div class="hero-left">
        <div class="hero-icon"><Icon name="chart" :size="32" /></div>
        <div>
          <h1 class="hero-title">工艺质量·成本·效率 协同分析工作台</h1>
          <p class="hero-sub">{{ kpi.date_from ? kpi.date_from.slice(0,10) : '-' }} ~ {{ kpi.date_to ? kpi.date_to.slice(0,10) : '-' }} · {{ kpi.coverage_days || 0 }}天 · {{ kpi.total_heats || 0 }}炉 · {{ kpi.steel_grade_count || 0 }}钢种</p>
        </div>
      </div>
      <div class="hero-stats">
        <div class="stat-pill"><span class="stat-val" :class="rateClass(kpi.overall_compliance_rate)">{{ kpi.overall_compliance_rate || 0 }}%</span><span class="stat-lbl">总符合率</span></div>
        <div class="stat-pill"><span class="stat-val primary">{{ fmt(kpi.scrap_total_weight) }}</span><span class="stat-lbl">废钢(吨)</span></div>
        <div class="stat-pill"><span class="stat-val primary">{{ fmt(cost.total_direct_cost) }}</span><span class="stat-lbl">直接成本(元)</span></div>
        <div class="stat-pill"><span class="stat-val warn">{{ aiOverview.findings ? aiOverview.findings.filter(f=>f.level==='严重').length : 0 }}</span><span class="stat-lbl">严重问题</span></div>
      </div>
    </div>

    <!-- 三主线概览卡片 -->
    <div class="domain-cards">
      <div class="domain-card" @click="goTo('quality')">
        <div class="dc-header"><Icon name="target" :size="20" /><span class="dc-title">质量</span><span class="dc-arrow">→</span></div>
        <div class="dc-rate" :class="rateClass(kpi.overall_compliance_rate)">{{ kpi.overall_compliance_rate || 0 }}%</div>
        <div class="dc-label">综合符合率</div>
        <div class="dc-ai" v-if="aiOverview.summary">
          <div class="dc-ai-icon"><Icon name="scope" :size="14" /></div>
          <div class="dc-ai-text">{{ aiOverview.summary }}</div>
        </div>
        <div class="dc-findings" v-if="aiOverview.findings">
          <span v-for="(f,i) in aiOverview.findings.slice(0,2)" :key="i" class="dc-finding" :class="levelClass(f.level)">
            <span class="dc-finding-badge">{{ f.level }}</span> {{ f.title }}
          </span>
        </div>
      </div>

      <div class="domain-card" @click="goTo('cost')">
        <div class="dc-header"><Icon name="dollar" :size="20" /><span class="dc-title">成本</span><span class="dc-arrow">→</span></div>
        <div class="dc-rate primary">{{ fmt(cost.total_direct_cost) }}<span class="dc-unit">元</span></div>
        <div class="dc-label">直接成本合计</div>
        <div class="dc-breakdown">
          <span>废钢 {{ fmt(cost.total_scrap_cost) }}</span>
          <span>合金 {{ fmt(cost.total_alloy_cost) }}</span>
        </div>
        <div class="dc-ratio">
          <div class="ratio-bar"><div class="ratio-fill scrap" :style="{width: costPct.scrap + '%'}"></div><div class="ratio-fill alloy" :style="{width: costPct.alloy + '%'}"></div></div>
          <div class="ratio-labels"><span>废钢{{ costPct.scrap }}%</span><span>合金{{ costPct.alloy }}%</span></div>
        </div>
      </div>

      <div class="domain-card" @click="goTo('efficiency')">
        <div class="dc-header"><Icon name="zap" :size="20" /><span class="dc-title">效率</span><span class="dc-arrow">→</span></div>
        <div class="dc-rate warn">{{ compStructure.efficiency_pct || 0 }}%</div>
        <div class="dc-label">效率损失占比</div>
        <div class="dc-breakdown">
          <span>直接 {{ compStructure.direct_pct || 0 }}%</span>
          <span>质量 {{ compStructure.quality_pct || 0 }}%</span>
          <span>效率 {{ compStructure.efficiency_pct || 0 }}%</span>
        </div>
        <div class="dc-bar">
          <div class="bar-seg direct" :style="{width: (compStructure.direct_pct||0) + '%'}"></div>
          <div class="bar-seg quality" :style="{width: (compStructure.quality_pct||0) + '%'}"></div>
          <div class="bar-seg efficiency" :style="{width: (compStructure.efficiency_pct||0) + '%'}"></div>
        </div>
      </div>
    </div>

    <!-- AI智能分析摘要 -->
    <div class="section">
      <h3 class="section-title"><Icon name="scope" :size="18" /> AI 智能分析摘要</h3>
      <div class="ai-summary-grid">
        <div class="ai-summary-card">
          <div class="asc-header"><span class="asc-badge bad">质量</span><span class="asc-risk">{{ aiOverview.risk || '-' }}风险</span></div>
          <p class="asc-summary">{{ aiOverview.summary || '加载中...' }}</p>
          <div class="asc-findings">
            <div v-for="(f,i) in (aiOverview.findings||[]).slice(0,3)" :key="i" class="asc-finding">
              <span class="asc-finding-level" :class="levelClass(f.level)">{{ f.level }}</span>
              <span class="asc-finding-text">{{ f.title }}: {{ f.content.slice(0,60) }}...</span>
            </div>
          </div>
        </div>
        <div class="ai-summary-card">
          <div class="asc-header"><span class="asc-badge warn">成本</span><span class="asc-risk">{{ costRisk }}</span></div>
          <p class="asc-summary">{{ costSummary }}</p>
          <div class="asc-findings">
            <div v-for="(f,i) in costFindings.slice(0,3)" :key="i" class="asc-finding">
              <span class="asc-finding-level" :class="levelClass(f.level)">{{ f.level }}</span>
              <span class="asc-finding-text">{{ f.title }}: {{ f.content.slice(0,60) }}...</span>
            </div>
          </div>
        </div>
        <div class="ai-summary-card">
          <div class="asc-header"><span class="asc-badge info">效率</span><span class="asc-risk">{{ effRisk }}</span></div>
          <p class="asc-summary">{{ effSummary }}</p>
          <div class="asc-findings">
            <div v-for="(f,i) in effFindings.slice(0,3)" :key="i" class="asc-finding">
              <span class="asc-finding-level" :class="levelClass(f.level)">{{ f.level }}</span>
              <span class="asc-finding-text">{{ f.title }}: {{ f.content.slice(0,60) }}...</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="section">
      <h3 class="section-title"><Icon name="layers" :size="18" /> 快捷入口</h3>
      <div class="quick-nav">
        <div class="qn-card" @click="goTo('quality')"><Icon name="target" :size="24" /><span>质量分析</span><span class="qn-desc">符合率/根因/偏差/追溯</span></div>
        <div class="qn-card" @click="goTo('cost')"><Icon name="dollar" :size="24" /><span>成本分析</span><span class="qn-desc">废钢/合金/对标</span></div>
        <div class="qn-card" @click="goTo('efficiency')"><Icon name="zap" :size="24" /><span>效率分析</span><span class="qn-desc">周期/班组/设备</span></div>
        <div class="qn-card" @click="goTo('cross')"><Icon name="link" :size="24" /><span>双维度交叉</span><span class="qn-desc">质量×成本/效率</span></div>
        <div class="qn-card" @click="goTo('model')"><Icon name="calculator" :size="24" /><span>模型模拟</span><span class="qn-desc">综合成本/仿真/配料</span></div>
        <div class="qn-card" @click="goTo('aiagent')"><Icon name="scope" :size="24" /><span>AI 智能智体</span><span class="qn-desc">LLM根因/三级建议/报告</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import Icon from '@/components/common/Icon.vue'
import { overviewApi, qualityApi, costApi, efficiencyApi, comprehensiveApi } from '@/api/modules'

const emit = defineEmits(['navigate'])
const kpi = ref({})
const cost = ref({ total_direct_cost: 0, total_scrap_cost: 0, total_alloy_cost: 0 })
const compStructure = ref({})
const aiOverview = ref({})
const costFindings = ref([])
const effFindings = ref([])

const costPct = computed(() => {
  const t = cost.value.total_direct_cost || 1
  return { scrap: Math.round(cost.value.total_scrap_cost / t * 100), alloy: Math.round(cost.value.total_alloy_cost / t * 100) }
})

const costSummary = computed(() => {
  if (!cost.value.total_direct_cost) return '加载中...'
  return `直接成本合计 ${fmt(cost.value.total_direct_cost)} 元，废钢占${costPct.value.scrap}%，合金占${costPct.value.alloy}%。`
})
const costRisk = computed(() => costPct.value.scrap > 80 ? '高' : '中')
const effSummary = computed(() => {
  if (!compStructure.value.efficiency_pct) return '加载中...'
  return `效率损失占综合成本 ${compStructure.value.efficiency_pct}%，是主要损失口子之一。`
})
const effRisk = computed(() => (compStructure.value.efficiency_pct || 0) > 15 ? '高' : '中')

const fmt = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
function rateClass(r) { return r >= 90 ? 'good' : r >= 80 ? 'warn' : 'bad' }
function levelClass(l) { return l === '严重' ? 'bad' : l === '警告' ? 'warn' : l === '亮点' ? 'good' : 'info' }

function goTo(domain) { emit('navigate', domain) }

onMounted(async () => {
  // 逐个加载 + 容错：单个接口失败不拖垮整页（避免 Promise.all 一损俱损导致全 O）
  const safe = async (p, fb) => { try { return await p } catch (e) { console.error('[Workbench]', e); return fb } }
  ;[
    ['k', () => overviewApi.kpi(), {}],
    ['c', () => overviewApi.directCost(), {}],
    ['ai', () => qualityApi.aiAnalysis(), { overview: {} }],
    ['comp', () => comprehensiveApi.model(10), { structure: {} }],
    ['costIns', () => costApi.insights(), { items: [] }],
    ['effIns', () => efficiencyApi.insights(), { items: [] }],
  ].forEach(async ([key, fn, fb]) => {
    const data = await safe(fn(), fb)
    if (key === 'k') kpi.value = data
    else if (key === 'c') cost.value = data
    else if (key === 'ai') aiOverview.value = data.overview || {}
    else if (key === 'comp') compStructure.value = data.structure || {}
    else if (key === 'costIns') costFindings.value = data.items || []
    else if (key === 'effIns') effFindings.value = data.items || []
  })
})
</script>

<style scoped>
.workbench { max-width: 1200px; }
.hero { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.hero-left { display: flex; align-items: center; gap: 14px; }
.hero-icon { color: #0284C7; }
.hero-title { font-size: 1.3rem; font-weight: 900; color: #0F172A; margin: 0; }
.hero-sub { font-size: 0.8rem; color: #64748B; margin: 4px 0 0; }
.hero-stats { display: flex; gap: 12px; }
.stat-pill { display: flex; flex-direction: column; align-items: center; gap: 2px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px 18px; min-width: 90px; }
.stat-val { font-size: 1.3rem; font-weight: 900; font-family: ui-monospace, monospace; color: #0284C7; }
.stat-val.good { color: #10B981; } .stat-val.warn { color: #F59E0B; } .stat-val.bad { color: #DC2626; }
.stat-lbl { font-size: 0.68rem; color: #475569; font-weight: 600; }

.domain-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.domain-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px; cursor: pointer; transition: all 0.25s; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.domain-card:hover { transform: translateY(-4px); box-shadow: 0 8px 20px rgba(0,0,0,0.06); border-color: #0284C7; }
.dc-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: #475569; }
.dc-title { font-size: 0.95rem; font-weight: 800; flex: 1; color: #0F172A; }
.dc-arrow { color: #94A3B8; font-size: 1.2rem; }
.dc-rate { font-size: 2rem; font-weight: 900; font-family: ui-monospace, monospace; }
.dc-rate.good { color: #10B981; } .dc-rate.warn { color: #F59E0B; } .dc-rate.bad { color: #DC2626; } .dc-rate.primary { color: #0284C7; }
.dc-unit { font-size: 0.9rem; font-weight: 600; color: #94A3B8; }
.dc-label { font-size: 0.78rem; color: #94A3B8; margin-bottom: 10px; }
.dc-ai { display: flex; gap: 6px; padding: 8px 10px; background: #F0F9FF; border-radius: 6px; margin-bottom: 8px; }
.dc-ai-icon { color: #0284C7; flex-shrink: 0; }
.dc-ai-text { font-size: 0.75rem; color: #0369A1; line-height: 1.5; }
.dc-findings { display: flex; flex-direction: column; gap: 4px; }
.dc-finding { font-size: 0.75rem; color: #475569; display: flex; align-items: center; gap: 4px; }
.dc-finding-badge { font-size: 0.6rem; padding: 1px 6px; border-radius: 8px; font-weight: 700; }
.dc-finding-badge.bad { background: #FEF2F2; color: #B91C1C; } .dc-finding-badge.warn { background: #FFFBEB; color: #D97706; } .dc-finding-badge.good { background: #ECFDF5; color: #047857; } .dc-finding-badge.info { background: #F0F9FF; color: #0369A1; }
.dc-breakdown { display: flex; gap: 12px; font-size: 0.78rem; color: #64748B; margin-bottom: 8px; }
.dc-ratio { margin-top: 8px; }
.ratio-bar { height: 6px; border-radius: 3px; overflow: hidden; display: flex; }
.ratio-fill { height: 100%; } .ratio-fill.scrap { background: #0284C7; } .ratio-fill.alloy { background: #6366F1; }
.ratio-labels { display: flex; justify-content: space-between; font-size: 0.7rem; color: #94A3B8; margin-top: 4px; }
.dc-bar { height: 6px; border-radius: 3px; overflow: hidden; display: flex; margin-top: 8px; }
.bar-seg { height: 100%; } .bar-seg.direct { background: #0284C7; } .bar-seg.quality { background: #DC2626; } .bar-seg.efficiency { background: #F59E0B; }

.section { margin-bottom: 24px; }
.section-title { font-size: 1rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; display: flex; align-items: center; gap: 6px; color: #475569; }
.ai-summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.ai-summary-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.asc-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.asc-badge { font-size: 0.7rem; padding: 2px 10px; border-radius: 10px; font-weight: 700; }
.asc-badge.bad { background: #FEF2F2; color: #B91C1C; } .asc-badge.warn { background: #FFFBEB; color: #D97706; } .asc-badge.info { background: #F0F9FF; color: #0369A1; }
.asc-risk { font-size: 0.72rem; color: #94A3B8; margin-left: auto; }
.asc-summary { font-size: 0.82rem; color: #475569; line-height: 1.5; margin: 0 0 10px; padding: 8px 10px; background: #F8FAFC; border-radius: 6px; }
.asc-findings { display: flex; flex-direction: column; gap: 6px; }
.asc-finding { display: flex; gap: 6px; font-size: 0.75rem; line-height: 1.4; }
.asc-finding-level { font-size: 0.6rem; padding: 1px 6px; border-radius: 6px; font-weight: 700; height: fit-content; white-space: nowrap; }
.asc-finding-level.bad { background: #DC2626; color: #fff; } .asc-finding-level.warn { background: #F59E0B; color: #fff; } .asc-finding-level.good { background: #10B981; color: #fff; } .asc-finding-level.info { background: #0284C7; color: #fff; }
.asc-finding-text { color: #475569; }

.quick-nav { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }
.qn-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px 16px; cursor: pointer; transition: all 0.25s; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 6px; color: #475569; }
.qn-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.06); border-color: #0284C7; color: #0284C7; }
.qn-card span:nth-child(2) { font-size: 0.88rem; font-weight: 700; }
.qn-desc { font-size: 0.72rem; color: #94A3B8; }

@media (max-width: 900px) {
  .domain-cards { grid-template-columns: 1fr; }
  .ai-summary-grid { grid-template-columns: 1fr; }
  .quick-nav { grid-template-columns: repeat(2, 1fr); }
}
</style>
