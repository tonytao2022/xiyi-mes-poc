<template>
  <div class="ai-agent">
    <!-- Hero 头部 -->
    <div class="hero">
      <div class="hero-left">
        <div class="hero-icon"><Icon name="scope" :size="32" /></div>
        <div>
          <h1 class="hero-title">AI 智能分析智体</h1>
          <p class="hero-sub">LLM 根因推理 · 三级整改建议 · 一键报告生成</p>
        </div>
      </div>
      <div class="llm-badge" :class="health.enabled ? 'on' : 'off'">
        <span class="dot"></span>
        <span class="txt">{{ health.enabled ? 'LLM 已启用' : '规则降级模式' }}</span>
        <span class="model" v-if="health.model">{{ health.model }}</span>
      </div>
    </div>

    <!-- 域选择 + 操作 -->
    <div class="toolbar">
      <div class="domain-tabs">
        <button
          v-for="d in domains"
          :key="d.id"
          class="domain-tab"
          :class="{ active: domain === d.id }"
          @click="domain = d.id"
        >
          <Icon :name="d.icon" :size="16" />
          <span>{{ d.label }}</span>
        </button>
      </div>
      <button class="btn-primary" :disabled="loading" @click="runDiagnosis">
        <Icon name="flask" :size="16" />
        <span>{{ loading ? '分析中...' : 'AI 智能诊断' }}</span>
      </button>
      <button class="btn-ghost" :disabled="loading || !rc" @click="generateReport">
        <Icon name="check" :size="16" />
        <span>生成 7 段式报告</span>
      </button>
    </div>

    <!-- 主内容 Tab -->
    <div class="body">
      <div class="tabs">
        <button class="tab" :class="{ active: tab === 'reason' }" @click="tab = 'reason'">
          <Icon name="target" :size="16" /> 根因诊断
        </button>
        <button class="tab" :class="{ active: tab === 'suggest' }" @click="switchSuggestTab()">
          <Icon name="wrench" :size="16" /> 三级建议
        </button>
        <button class="tab" :class="{ active: tab === 'report' }" @click="switchReportTab()">
          <Icon name="layers" :size="16" /> 报告中心
          <span class="tab-count" v-if="reportTotal > 0">{{ reportTotal }}</span>
        </button>
      </div>

      <!-- 根因诊断 -->
      <div v-if="tab === 'reason'" class="panel">
        <div v-if="loading && !rc" class="loading-state">
          <div class="spinner"></div>
          <p>正在调用 {{ health.model || 'LLM' }} 进行根因推理...</p>
        </div>
        <div v-else-if="rcErr" class="error-state">{{ rcErr }}</div>
        <template v-else-if="rc">
          <div class="reason-header">
            <div class="risk-box" :class="riskClass(rc.risk_level)">
              <span class="risk-label">风险等级</span>
              <span class="risk-val">{{ rc.risk_level || '中' }}</span>
            </div>
            <div class="meta-badge" v-if="rc._meta">
              <span v-if="rc._meta.llm !== undefined">{{ rc._meta.llm ? 'LLM 推理' : '规则引擎' }}</span>
              <span v-if="rc._meta.model" class="model">{{ rc._meta.model }}</span>
            </div>
          </div>
          <p class="summary">{{ rc.summary || '暂无摘要' }}</p>

          <h4 class="block-title"><Icon name="alert" :size="15" /> 根因列表（{{ (rc.root_causes || []).length }}条）</h4>
          <div class="cause-list">
            <div v-for="(c, i) in (rc.root_causes || [])" :key="i" class="cause-card">
              <div class="cause-idx">{{ i + 1 }}</div>
              <div class="cause-body">
                <div class="cause-top">
                  <span class="cause-title">{{ c.root_cause || c.title || '未命名根因' }}</span>
                  <span class="cause-conf" v-if="c.confidence !== undefined">
                    <span class="conf-bar"><span class="conf-fill" :style="{ width: (c.confidence * 100) + '%' }"></span></span>
                    {{ (c.confidence * 100).toFixed(0) }}%
                  </span>
                </div>
                <div class="cause-domain" v-if="c.domain">{{ c.domain }}</div>
                <div class="cause-evidence" v-if="c.evidence && c.evidence.length">
                  <span class="ev-label">证据</span>
                  <span v-for="(e, j) in c.evidence.slice(0, 3)" :key="j" class="ev-item">{{ e }}</span>
                </div>
                <div class="cause-impact" v-if="c.impact">{{ c.impact }}</div>
              </div>
            </div>
          </div>
          <div v-if="!rc.root_causes || !rc.root_causes.length" class="empty">未识别到根因，请尝试重新诊断</div>
        </template>
        <div v-else class="idle-state">
          <Icon name="search" :size="40" />
          <p>选择分析域后点击「AI 智能诊断」，系统将调用大模型对当前数据做根因推理。</p>
        </div>
      </div>

      <!-- 三级建议 -->
      <div v-if="tab === 'suggest'" class="panel">
        <div v-if="!rc" class="idle-state">
          <Icon name="wrench" :size="40" />
          <p>请先运行「AI 智能诊断」生成根因分析，再查看三级整改建议。</p>
        </div>
        <div v-else-if="loadingSuggest" class="loading-state">
          <div class="spinner"></div>
          <p>正在基于根因生成三级整改建议（{{ health.model || 'LLM' }}）...</p>
        </div>
        <div v-else-if="suggestErr" class="error-state">{{ suggestErr }}</div>
        <div v-else-if="!recs.length" class="empty">暂无建议数据，请点击右上角「生成建议」重新尝试</div>
        <div v-else class="rec-wrap">
          <div class="rec-group">
            <h4 class="group-title"><span class="g-badge short">短期止血</span>立即整改 · 1-7天</h4>
            <div v-for="(r, i) in recs.filter(x => isUrgent(x.level))" :key="'s' + i" class="rec-card short">
              <div class="rec-action">{{ r.action }}</div>
              <div class="rec-meta">
                <span v-if="r.target">🎯 {{ r.target }}</span>
                <span v-if="r.owner">👤 {{ r.owner }}</span>
                <span v-if="r.effort">⏱ {{ r.effort }}</span>
                <span v-if="r.expected_gain" class="gain">📈 {{ r.expected_gain }}</span>
              </div>
            </div>
          </div>
          <div class="rec-group">
            <h4 class="group-title"><span class="g-badge mid">中期改善</span>系统优化 · 1-4周</h4>
            <div v-for="(r, i) in recs.filter(x => isShort(x.level))" :key="'m' + i" class="rec-card mid">
              <div class="rec-action">{{ r.action }}</div>
              <div class="rec-meta">
                <span v-if="r.target">🎯 {{ r.target }}</span>
                <span v-if="r.owner">👤 {{ r.owner }}</span>
                <span v-if="r.effort">⏱ {{ r.effort }}</span>
                <span v-if="r.expected_gain" class="gain">📈 {{ r.expected_gain }}</span>
              </div>
            </div>
          </div>
          <div class="rec-group">
            <h4 class="group-title"><span class="g-badge long">长期治本</span>战略改进 · 1-3月</h4>
            <div v-for="(r, i) in recs.filter(x => isLong(x.level))" :key="'l' + i" class="rec-card long">
              <div class="rec-action">{{ r.action }}</div>
              <div class="rec-meta">
                <span v-if="r.target">🎯 {{ r.target }}</span>
                <span v-if="r.owner">👤 {{ r.owner }}</span>
                <span v-if="r.effort">⏱ {{ r.effort }}</span>
                <span v-if="r.expected_gain" class="gain">📈 {{ r.expected_gain }}</span>
              </div>
            </div>
          </div>
          <div v-if="!recs.some(x => isUrgent(x.level))" class="empty">无紧急建议</div>
        </div>
      </div>

      <!-- 报告中心 -->
      <div v-if="tab === 'report'" class="panel">
        <div class="report-toolbar">
          <select v-model="reportDomain" class="select">
            <option value="">全部域</option>
            <option v-for="d in domains" :key="d.id" :value="d.id">{{ d.label }}</option>
          </select>
          <button class="btn-ghost" :disabled="loadingReport" @click="loadReports(true)">
            <Icon name="recycle" :size="16" /> 刷新
          </button>
        </div>
        <div v-if="loadingReport" class="loading-state"><div class="spinner"></div><p>加载报告列表...</p></div>
        <div v-else-if="!reports.length" class="empty">暂无报告，点击「生成 7 段式报告」创建</div>
        <div v-else class="report-list">
          <div v-for="r in reports" :key="r.id" class="report-card" :class="{ active: r.id === viewingId }" @click="viewReport(r.id)">
            <div class="report-icon"><Icon name="layers" :size="18" /></div>
            <div class="report-info">
              <div class="report-title">{{ r.title }}</div>
              <div class="report-sub">
                <span class="tag" :class="r.domain">{{ domainLabel(r.domain) }}</span>
                <span v-if="r.llm_used" class="tag llm">LLM</span>
                <span class="time">{{ fmtTime(r.created_at) }}</span>
              </div>
            </div>
            <div class="report-actions" @click.stop>
              <a v-if="viewingId !== r.id" class="mini-btn" @click="viewReport(r.id)">查看</a>
              <a class="mini-btn" :href="reportHtmlUrl(r.id)" target="_blank">打开HTML</a>
            </div>
          </div>
        </div>

        <!-- 报告查看器 -->
        <div v-if="detail" class="report-viewer">
          <div class="rv-header">
            <div>
              <h4>{{ detail.title }}</h4>
              <div class="rv-sub">
                <span class="tag" :class="detail.domain">{{ domainLabel(detail.domain) }}</span>
                <span v-if="detail.llm_used" class="tag llm">LLM 生成</span>
                <span v-if="detail.model_used" class="model">{{ detail.model_used }}</span>
              </div>
            </div>
            <button class="btn-ghost" @click="detail = null">关闭</button>
          </div>
          <iframe v-if="detail.htmlUrl" :src="detail.htmlUrl" class="report-frame"></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import Icon from '@/components/common/Icon.vue'
import http from '@/api/http'

const domains = [
  { id: 'comprehensive', label: '综合分析', icon: 'link' },
  { id: 'quality', label: '质量', icon: 'target' },
  { id: 'cost', label: '成本', icon: 'dollar' },
  { id: 'efficiency', label: '效率', icon: 'zap' },
]

const domain = ref('comprehensive')
const tab = ref('reason')
const loading = ref(false)
const rc = ref(null)
const rcErr = ref('')
const recs = ref([])
const loadingSuggest = ref(false)
const suggestErr = ref('')

// 三级建议与 LLM 输出 level 严格一一对应：urgent → 短期止血 / short → 中期改善 / long → 长期治本
function isUrgent(lv) { return ['urgent'].includes((lv || '').toLowerCase()) }
function isShort(lv) { return ['short'].includes((lv || '').toLowerCase()) }
function isLong(lv) { return ['long'].includes((lv || '').toLowerCase()) }
const health = ref({ enabled: false, model: '' })

const reportDomain = ref('')
const reports = ref([])
const reportTotal = ref(0)
const viewingId = ref(null)
const detail = ref(null)
const loadingReport = ref(false)

function riskClass(r) { return r === '高' ? 'high' : r === '低' ? 'low' : 'mid' }
function domainLabel(id) {
  const d = domains.find(x => x.id === id)
  return d ? d.label : id
}
function fmtTime(t) {
  if (!t) return ''
  return String(t).replace('T', ' ').slice(0, 16)
}

async function runDiagnosis() {
  loading.value = true
  rcErr.value = ''
  try {
    // LLM 根因推理较慢(偶发>30s)，单独放宽超时到 180s
    const res = await http.post('/ai/reason', null, { params: { domain: domain.value }, timeout: 180000 })
    rc.value = res
    // 只在根因接口确实携带了建议时直接复用，否则留空由三级建议 Tab 按需拉取
    recs.value = (res && res.recommendations) || []
    tab.value = 'reason'
  } catch (e) {
    rcErr.value = '根因分析失败：' + (e?.response?.data?.detail || e.message)
    rc.value = null
    recs.value = []
  } finally {
    loading.value = false
  }
}

async function switchSuggestTab() {
  tab.value = 'suggest'
  // 未生成根因：提示先诊断
  if (!rc.value) return
  // 已有建议：直接展示，不再重复调用
  if (recs.value && recs.value.length) return
  // 按需拉取三级建议：基于已生成的根因，单次 LLM 调用（与 /reason 解耦，避免接口超时翻倍）
  loadingSuggest.value = true
  suggestErr.value = ''
  try {
    const res = await http.post('/ai/suggestions',
      { root_causes: (rc.value.root_causes || []) },
      { params: { domain: domain.value }, timeout: 180000 })
    recs.value = (res && res.recommendations) || []
  } catch (e) {
    suggestErr.value = '三级建议生成失败：' + (e?.response?.data?.detail || e.message)
  } finally {
    loadingSuggest.value = false
  }
}

async function generateReport() {
  loading.value = true
  try {
    // 报告需根因+建议两步 LLM 串联，更慢，放宽到 300s
    await http.post('/ai/report/generate', null, { params: { domain: domain.value, include_llm: true }, timeout: 300000 })
    await loadReports(true)
    tab.value = 'report'
  } catch (e) {
    alert('报告生成失败：' + (e?.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function loadReports(reset = false) {
  loadingReport.value = true
  if (reset) viewingId.value = null
  try {
    const res = await http.get('/ai/report/list', { params: { page: 1, page_size: 50, domain: reportDomain.value || undefined } })
    reports.value = res.items || []
    reportTotal.value = res.total || 0
  } catch (e) {
    console.error('[AiAgent] list', e)
  } finally {
    loadingReport.value = false
  }
}

function reportHtmlUrl(id) { return `/api/ai/report/${id}?mode=html` }

async function viewReport(id) {
  viewingId.value = id
  detail.value = null
  try {
    const res = await http.get(`/ai/report/${id}`, { params: { mode: 'json' } })
    detail.value = { ...res, htmlUrl: reportHtmlUrl(id) }
  } catch (e) {
    alert('加载报告详情失败')
  }
}

function switchReportTab() {
  if (tab.value !== 'report') {
    tab.value = 'report'
    loadReports()
  }
}

watch(reportDomain, () => loadReports(true))

onMounted(async () => {
  const safe = async (p, fb) => { try { return await p } catch (e) { return fb } }
  const h = await safe(http.get('/ai/health'), { enabled: false })
  health.value = h
  if (health.value.enabled) {
    // 预热一次诊断，让用户一进来就有结果可看
    runDiagnosis()
  }
})

// 域切换时自动清空旧结果
watch(domain, () => {
  rc.value = null
  rcErr.value = ''
})
</script>

<style scoped>
.ai-agent { max-width: 1200px; }
.hero { display: flex; align-items: center; justify-content: space-between; background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.hero-left { display: flex; align-items: center; gap: 14px; }
.hero-icon { color: #0284C7; }
.hero-title { font-size: 1.3rem; font-weight: 900; color: #0F172A; margin: 0; }
.hero-sub { font-size: 0.8rem; color: #64748B; margin: 4px 0 0; }
.llm-badge { display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 24px; font-size: 0.8rem; font-weight: 700; }
.llm-badge.on { background: #ECFDF5; color: #047857; border: 1px solid #D1FAE5; }
.llm-badge.off { background: #F1F5F9; color: #64748B; border: 1px solid #E2E8F0; }
.llm-badge .dot { width: 8px; height: 8px; border-radius: 50%; }
.llm-badge.on .dot { background: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.2); }
.llm-badge.off .dot { background: #94A3B8; }
.llm-badge .model { font-size: 0.68rem; color: #94A3B8; font-weight: 600; }

.toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.domain-tabs { display: flex; gap: 8px; flex: 1; }
.domain-tab { display: flex; align-items: center; gap: 6px; padding: 9px 16px; border-radius: 10px; border: 1px solid #E2E8F0; background: #fff; cursor: pointer; color: #475569; font-size: 0.85rem; font-weight: 700; transition: all 0.2s; }
.domain-tab:hover { border-color: #0284C7; color: #0284C7; }
.domain-tab.active { background: var(--v2-grad); color: #fff; border-color: transparent; box-shadow: var(--v2-shadow-primary); }

.btn-primary, .btn-ghost { display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px; border-radius: 10px; font-size: 0.85rem; font-weight: 700; cursor: pointer; border: none; transition: all 0.2s; }
.btn-primary { background: var(--v2-grad); color: #fff; box-shadow: var(--v2-shadow-primary); }
.btn-primary:hover { filter: brightness(1.08); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-ghost { background: #fff; color: #475569; border: 1px solid #E2E8F0; }
.btn-ghost:hover { border-color: #0284C7; color: #0284C7; }
.btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

.tabs { display: flex; gap: 4px; background: #E2E8F0; padding: 4px; border-radius: 12px; margin-bottom: 16px; width: fit-content; }
.tab { display: flex; align-items: center; gap: 6px; padding: 9px 20px; border-radius: 9px; border: none; background: transparent; cursor: pointer; color: #64748B; font-size: 0.85rem; font-weight: 700; transition: all 0.2s; }
.tab.active { background: #fff; color: #0284C7; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.tab-count { background: #0284C7; color: #fff; font-size: 0.65rem; padding: 1px 7px; border-radius: 10px; }

.panel { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); min-height: 300px; }
.idle-state, .empty, .loading-state, .error-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: 60px 20px; color: #94A3B8; text-align: center; font-size: 0.85rem; }
.loading-state p { color: #64748B; }
.error-state { color: #DC2626; }
.spinner { width: 32px; height: 32px; border: 3px solid #E2E8F0; border-top-color: #0284C7; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.reason-header { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.risk-box { display: flex; flex-direction: column; align-items: center; padding: 8px 18px; border-radius: 10px; }
.risk-box.high { background: #FEF2F2; color: #B91C1C; }
.risk-box.mid { background: #FFFBEB; color: #D97706; }
.risk-box.low { background: #ECFDF5; color: #047857; }
.risk-label { font-size: 0.65rem; opacity: 0.8; }
.risk-val { font-size: 1.3rem; font-weight: 900; }
.meta-badge { margin-left: auto; display: flex; gap: 8px; }
.meta-badge span { font-size: 0.7rem; background: #F1F5F9; color: #64748B; padding: 4px 10px; border-radius: 12px; font-weight: 700; }
.meta-badge .model { font-family: ui-monospace, monospace; }
.summary { font-size: 0.88rem; color: #475569; line-height: 1.6; background: #F8FAFC; border-left: 4px solid #0284C7; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 0 0 20px; }
.block-title { font-size: 0.9rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; display: flex; align-items: center; gap: 6px; }
.cause-list { display: flex; flex-direction: column; gap: 10px; }
.cause-card { display: flex; gap: 12px; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px; }
.cause-idx { width: 28px; height: 28px; border-radius: 8px; background: var(--v2-grad); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.85rem; flex-shrink: 0; }
.cause-body { flex: 1; }
.cause-top { display: flex; align-items: center; gap: 12px; }
.cause-title { font-size: 0.9rem; font-weight: 700; color: #0F172A; flex: 1; }
.cause-conf { display: flex; align-items: center; gap: 6px; font-size: 0.72rem; color: #64748B; font-weight: 700; white-space: nowrap; }
.conf-bar { width: 50px; height: 5px; background: #E2E8F0; border-radius: 3px; overflow: hidden; }
.conf-fill { display: block; height: 100%; background: var(--v2-grad-progress); }
.cause-domain { display: inline-block; font-size: 0.68rem; background: #F0F9FF; color: #0369A1; padding: 2px 8px; border-radius: 8px; margin-top: 6px; font-weight: 600; }
.cause-evidence { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.ev-label { font-size: 0.68rem; color: #94A3B8; font-weight: 700; }
.ev-item { font-size: 0.72rem; background: #F1F5F9; color: #475569; padding: 3px 8px; border-radius: 6px; }
.cause-impact { font-size: 0.78rem; color: #B91C1C; background: #FEF2F2; padding: 6px 10px; border-radius: 6px; margin-top: 8px; }

.rec-wrap { display: flex; flex-direction: column; gap: 24px; }
.rec-group { border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px; }
.group-title { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; }
.g-badge { font-size: 0.7rem; padding: 2px 10px; border-radius: 12px; color: #fff; }
.g-badge.short { background: #DC2626; }
.g-badge.mid { background: #F59E0B; }
.g-badge.long { background: #0284C7; }
.rec-card { border-left: 4px solid #E2E8F0; background: #F8FAFC; border-radius: 0 8px 8px 0; padding: 12px 14px; margin-bottom: 8px; }
.rec-card.short { border-left-color: #DC2626; }
.rec-card.mid { border-left-color: #F59E0B; }
.rec-card.long { border-left-color: #0284C7; }
.rec-action { font-size: 0.88rem; color: #0F172A; font-weight: 600; line-height: 1.5; }
.rec-meta { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; font-size: 0.75rem; color: #64748B; }
.rec-meta .gain { color: #047857; font-weight: 700; }

.report-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.select { padding: 8px 12px; border: 1px solid #E2E8F0; border-radius: 8px; font-size: 0.82rem; color: #475569; background: #fff; }
.report-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.report-card { display: flex; align-items: center; gap: 14px; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px 16px; cursor: pointer; transition: all 0.2s; }
.report-card:hover { border-color: #0284C7; }
.report-card.active { border-color: #0284C7; background: #F0F9FF; }
.report-icon { color: #0284C7; }
.report-info { flex: 1; }
.report-title { font-size: 0.88rem; font-weight: 700; color: #0F172A; }
.report-sub { display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.tag { font-size: 0.65rem; padding: 2px 8px; border-radius: 8px; font-weight: 700; }
.tag.comprehensive { background: #EEF2FF; color: #4338CA; }
.tag.quality { background: #FEF2F2; color: #B91C1C; }
.tag.cost { background: #FFFBEB; color: #D97706; }
.tag.efficiency { background: #F0F9FF; color: #0369A1; }
.tag.llm { background: #ECFDF5; color: #047857; }
.time { font-size: 0.72rem; color: #94A3B8; }
.report-actions { display: flex; gap: 6px; }
.mini-btn { font-size: 0.72rem; color: #0284C7; font-weight: 700; cursor: pointer; padding: 4px 8px; border-radius: 6px; }
.mini-btn:hover { background: #E0F2FE; }
.rv-header { display: flex; align-items: flex-start; justify-content: space-between; border-top: 1px solid #E2E8F0; padding-top: 16px; margin-top: 8px; }
.rv-header h4 { margin: 0; font-size: 1rem; color: #0F172A; }
.rv-sub { display: flex; gap: 8px; margin-top: 6px; align-items: center; }
.rv-sub .model { font-size: 0.7rem; color: #94A3B8; font-family: ui-monospace, monospace; }
.report-frame { width: 100%; height: 520px; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 14px; background: #fff; }

@media (max-width: 900px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .domain-tabs { justify-content: flex-start; overflow-x: auto; }
  .hero { flex-direction: column; align-items: flex-start; gap: 12px; }
}
</style>
