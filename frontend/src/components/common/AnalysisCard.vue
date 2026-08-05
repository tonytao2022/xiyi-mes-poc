<template>
  <div class="ai-card">
    <div class="ai-header">
      <span class="ai-icon"><Icon name="scope" :size="20" /></span>
      <span class="ai-title">AI 智能分析</span>
      <span class="ai-risk" :class="riskClass">{{ data.risk || '-' }}风险</span>
    </div>
    <div v-if="data.layer_summary" class="layer-summary">
      <div class="ls-item"><span class="ls-label">L1 产品质量</span><span class="ls-val" :class="rateClass(data.layer_summary.L1_product_quality)">{{ data.layer_summary.L1_product_quality }}%</span></div>
      <div class="ls-arrow">→</div>
      <div class="ls-item"><span class="ls-label">L2 工艺参数</span><span class="ls-val" :class="rateClass(data.layer_summary.L2_process_quality)">{{ data.layer_summary.L2_process_quality }}%</span></div>
      <div class="ls-arrow">→</div>
      <div class="ls-item"><span class="ls-label">L3 操作规范</span><span class="ls-val" :class="rateClass(data.layer_summary.L3_operational)">{{ data.layer_summary.L3_operational }}%</span></div>
    </div>
    <div class="ai-summary">{{ data.summary }}</div>
    <div class="ai-findings">
      <div v-for="(f, i) in (data.findings || [])" :key="i" class="finding" :class="levelClass(f.level)">
        <span class="finding-badge" :class="levelClass(f.level)">{{ f.level }}</span>
        <div class="finding-body">
          <div class="finding-title">{{ f.title }}</div>
          <div class="finding-content">{{ f.content }}</div>
          <div v-if="f.evidence" class="finding-evidence">依据: {{ f.evidence }}</div>
          <div v-if="f.chain" class="finding-chain">
            <span v-for="(step, ci) in f.chain" :key="ci" class="chain-step">
              {{ step }}
              <span v-if="ci < f.chain.length - 1" class="chain-arrow">→</span>
            </span>
          </div>
        </div>
      </div>
    </div>
    <div v-if="(data.recommendations || []).length" class="ai-recommendations">
      <div class="rec-title">改进建议</div>
      <div v-for="(r, i) in data.recommendations" :key="i" class="rec-item">
        <span class="rec-num">{{ i + 1 }}</span>{{ r }}
      </div>
    </div>
  </div>
</template>

<script setup>
import Icon from '@/components/common/Icon.vue'
defineProps({ data: { type: Object, default: () => ({}) } })
function levelClass(l) { return l === '严重' ? 'bad' : l === '警告' ? 'warn' : l === '亮点' ? 'good' : 'info' }
function riskClass(r) { return r === '高' ? 'bad' : r === '中' ? 'warn' : 'good' }
function rateClass(r) { return r >= 90 ? 'good' : r >= 80 ? 'warn' : 'bad' }
</script>

<style scoped>
.ai-card {
  background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px;
  margin-top: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-left: 4px solid #0284C7;
}
.ai-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.ai-icon { color: #0284C7; display: flex; align-items: center; }
.ai-title { font-size: 1rem; font-weight: 800; color: #0F172A; }
.ai-risk { font-size: 0.72rem; padding: 2px 10px; border-radius: 12px; font-weight: 700; margin-left: auto; }
.ai-risk.good { background: #ECFDF5; color: #047857; }
.ai-risk.warn { background: #FFFBEB; color: #D97706; }
.ai-risk.bad { background: #FEF2F2; color: #B91C1C; }
.ai-summary { font-size: 0.88rem; color: #475569; line-height: 1.6; margin-bottom: 16px; padding: 10px 14px; background: #F0F9FF; border-radius: 8px; border-left: 3px solid #0284C7; }
.layer-summary { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; padding: 12px 16px; background: linear-gradient(135deg, #F0F9FF, #F8FAFC); border-radius: 10px; border: 1px solid #E2E8F0; }
.ls-item { display: flex; flex-direction: column; align-items: center; gap: 2px; flex: 1; }
.ls-label { font-size: 0.72rem; color: #64748B; font-weight: 600; }
.ls-val { font-size: 1.2rem; font-weight: 900; font-family: ui-monospace, monospace; }
.ls-val.good { color: #10B981; } .ls-val.warn { color: #F59E0B; } .ls-val.bad { color: #DC2626; }
.ls-arrow { color: #CBD5E1; font-size: 1.2rem; }
.ai-findings { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.finding { display: flex; gap: 10px; padding: 10px 12px; border-radius: 8px; background: #F8FAFC; }
.finding.bad { background: #FEF2F2; }
.finding.warn { background: #FFFBEB; }
.finding.good { background: #ECFDF5; }
.finding.info { background: #F0F9FF; }
.finding-badge { font-size: 0.65rem; padding: 2px 8px; border-radius: 10px; font-weight: 700; height: fit-content; white-space: nowrap; }
.finding-badge.bad { background: #DC2626; color: #fff; }
.finding-badge.warn { background: #F59E0B; color: #fff; }
.finding-badge.good { background: #10B981; color: #fff; }
.finding-badge.info { background: #0284C7; color: #fff; }
.finding-body { flex: 1; }
.finding-title { font-size: 0.85rem; font-weight: 700; color: #0F172A; margin-bottom: 2px; }
.finding-content { font-size: 0.8rem; color: #475569; line-height: 1.5; }
.finding-evidence { font-size: 0.72rem; color: #94A3B8; margin-top: 2px; font-family: ui-monospace, monospace; }
.finding-chain { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-top: 6px; padding: 6px 10px; background: rgba(2,132,199,0.05); border-radius: 6px; border: 1px dashed #BAE6FD; }
.chain-step { font-size: 0.72rem; color: #0369A1; font-weight: 600; }
.chain-arrow { color: #94A3B8; margin: 0 2px; }
.ai-recommendations { border-top: 1px solid #F1F5F9; padding-top: 12px; }
.rec-title { font-size: 0.82rem; font-weight: 700; color: #0F172A; margin-bottom: 8px; }
.rec-item { display: flex; align-items: flex-start; gap: 8px; font-size: 0.8rem; color: #475569; margin-bottom: 6px; line-height: 1.5; }
.rec-num { display: flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%; background: #0284C7; color: #fff; font-size: 0.7rem; font-weight: 700; flex-shrink: 0; margin-top: 1px; }
</style>
