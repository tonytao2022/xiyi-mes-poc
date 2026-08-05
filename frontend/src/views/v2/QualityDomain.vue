<template>
  <div class="domain">
    <div class="domain-tabs">
      <button v-for="t in tabs" :key="t.key" :class="{ active: active === t.key }" @click="active = t.key">{{ t.label }}</button>
    </div>
    <div class="domain-content" :key="active">
      <!-- Tab 1: 总览 -->
      <div v-if="active === 'overview'">
        <div class="layer-cards" v-if="ai.layer_summary">
          <div class="layer-card l1">
            <div class="lc-header"><Icon name="check" :size="18" /><span>L1 产品质量</span></div>
            <div class="lc-rate" :class="rateClass(ai.layer_summary.L1_product_quality)">{{ ai.layer_summary.L1_product_quality }}%</div>
            <div class="lc-desc">成分{{ l1m.chemical_rate }}% / 力学{{ l1m.mechanical_rate }}% / 尺寸{{ l1m.dimension_rate }}%</div>
            <div class="lc-sample">样本: {{ l1m.sample_n }}炉</div>
          </div>
          <div class="layer-card l2">
            <div class="lc-header"><Icon name="scope" :size="18" /><span>L2 工艺参数</span></div>
            <div class="lc-rate" :class="rateClass(ai.layer_summary.L2_process_quality)">{{ ai.layer_summary.L2_process_quality }}%</div>
            <div class="lc-desc">终点命中{{ l2m.endpoint_hit_rate }}% / 补吹{{ l2m.reblow_rate }}% / 过热度{{ l2m.superheat_rate }}%</div>
            <div class="lc-sample">加权符合率（排除合金）</div>
          </div>
          <div class="layer-card l3">
            <div class="lc-header"><Icon name="sliders" :size="18" /><span>L3 操作规范</span></div>
            <div class="lc-rate" :class="rateClass(ai.layer_summary.L3_operational)">{{ ai.layer_summary.L3_operational }}%</div>
            <div class="lc-desc">操作执行率</div>
            <div class="lc-sample">管理合规性</div>
          </div>
        </div>
        <AnalysisCard :data="ai.overview || {}" />
        <QualityV2 />
      </div>

      <!-- Tab 2: L1 产品质量诊断 -->
      <div v-else-if="active === 'l1'">
        <AnalysisCard :data="{ summary: l1Summary, findings: ai.l1_product?.findings || [], recommendations: l1Recs, risk: l1Risk }" />
        <ChemicalView />
        <MechanicalView />
        <DimensionView />
      </div>

      <!-- Tab 3: L2 工艺过程诊断 -->
      <div v-else-if="active === 'l2'">
        <AnalysisCard :data="{ summary: l2Summary, findings: ai.l2_process?.findings || [], recommendations: l2Recs, risk: l2Risk }" />
        <ComplianceView />
        <RollingView />
      </div>

      <!-- Tab 4: 根因下钻 -->
      <div v-else-if="active === 'rootcause'">
        <IndicatorsView />
      </div>

      <!-- Tab 5: 追溯 -->
      <div v-else-if="active === 'trace'">
        <AnalysisCard :data="aiTrace" />
        <TraceView />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import Icon from '@/components/common/Icon.vue'
import QualityV2 from '@/views/v2/QualityV2.vue'
import ChemicalView from '@/views/quality/ChemicalView.vue'
import MechanicalView from '@/views/quality/MechanicalView.vue'
import DimensionView from '@/views/quality/DimensionView.vue'
import ComplianceView from '@/views/quality/ComplianceView.vue'
import RollingView from '@/views/quality/RollingView.vue'
import IndicatorsView from '@/views/quality/IndicatorsView.vue'
import TraceView from '@/views/quality/TraceView.vue'
import AnalysisCard from '@/components/common/AnalysisCard.vue'
import { qualityApi } from '@/api/modules'

const active = ref('overview')
const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'l1', label: '产品质量诊断(L1)' },
  { key: 'l2', label: '工艺过程诊断(L2)' },
  { key: 'rootcause', label: '根因下钻' },
  { key: 'trace', label: '全流程追溯' },
]
const ai = ref({ overview: {}, layer_summary: {}, l1_product: { metrics: {} }, l2_process: { metrics: {} } })
const aiTrace = ref({})

const l1m = computed(() => ai.value.l1_product?.metrics || {})
const l2m = computed(() => ai.value.l2_process?.metrics || {})

const l1Summary = computed(() => `L1产品质量：化学成分合格率${l1m.value.chemical_rate || 0}%，力学${l1m.value.mechanical_rate || 0}%，尺寸${l1m.value.dimension_rate || 0}%。样本${l1m.value.sample_n || 0}炉。`)
const l1Recs = computed(() => {
  const recs = []
  if ((l1m.value.chemical_rate || 100) < 95) recs.push('加强化学成分窄控制，特别是C/Mn元素稳定性')
  if ((l1m.value.mechanical_rate || 100) < 100) recs.push('对不合格试样追溯轧制温度和化学成分')
  recs.push('建立一次合格率统计（需补全最终判定数据）')
  return recs
})
const l1Risk = computed(() => {
  const avg = ((l1m.value.chemical_rate || 0) + (l1m.value.mechanical_rate || 0) + (l1m.value.dimension_rate || 0)) / 3
  return avg >= 95 ? '低' : avg >= 85 ? '中' : '高'
})
const l2Summary = computed(() => `L2工艺参数：终点命中率${l2m.value.endpoint_hit_rate || 0}%，补吹率${l2m.value.reblow_rate || 0}%，过热度${l2m.value.superheat_rate || 0}%，加权${l2m.value.weighted_rate || 0}%。`)
const l2Recs = computed(() => {
  const recs = []
  if ((l2m.value.endpoint_hit_rate || 100) < 85) recs.push(`优先提升终点命中率(当前${l2m.value.endpoint_hit_rate}%)`)
  if ((l2m.value.reblow_rate || 0) > 10) recs.push(`降低补吹率(当前${l2m.value.reblow_rate}%)`)
  if ((l2m.value.superheat_rate || 100) < 80) recs.push(`稳定过热度(当前${l2m.value.superheat_rate}%)`)
  return recs.length ? recs : ['各工艺参数基本达标']
})
const l2Risk = computed(() => (l2m.value.endpoint_hit_rate || 100) < 70 ? '高' : (l2m.value.endpoint_hit_rate || 100) < 85 ? '中' : '低')

function rateClass(r) { return r >= 90 ? 'good' : r >= 80 ? 'warn' : 'bad' }

async function loadTrace() {
  try { aiTrace.value = await qualityApi.aiTrace() } catch (e) { console.error(e) }
}
onMounted(async () => {
  try { ai.value = await qualityApi.aiAnalysis() } catch (e) { console.error(e) }
})
watch(() => active.value, (v) => {
  if (v === 'trace' && !aiTrace.value.summary) loadTrace()
})
</script>

<style scoped>
.domain-tabs { display: flex; gap: 0; border-bottom: 2px solid #E2E8F0; margin-bottom: 20px; background: #fff; border-radius: 14px 14px 0 0; padding: 0 8px; overflow-x: auto; }
.domain-tabs button { background: none; border: none; color: #475569; padding: 14px 20px; cursor: pointer; font-size: 0.88rem; font-weight: 600; border-bottom: 3px solid transparent; transition: all 0.2s; margin-bottom: -2px; white-space: nowrap; }
.domain-tabs button:hover { color: #0284C7; }
.domain-tabs button.active { color: #0284C7; font-weight: 800; border-bottom-color: #0284C7; }
.domain-content { color: #0F172A; --bg: #F8FAFC; --glass: #FFFFFF; --glass2: #F8FAFC; --border: rgba(226, 232, 240, 0.8); --text: #0F172A; --dim: #64748B; --accent: #0284C7; --accent2: #6366F1; --green: #10B981; --red: #DC2626; --yellow: #F59E0B; --radius: 14px; --radius-sm: 8px; --space-sm: 0.5rem; --space-md: 1rem; --space-lg: 2rem; }
.layer-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
.layer-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border-top: 4px solid #94A3B8; }
.layer-card.l1 { border-top-color: #10B981; }
.layer-card.l2 { border-top-color: #0284C7; }
.layer-card.l3 { border-top-color: #F59E0B; }
.lc-header { display: flex; align-items: center; gap: 6px; color: #475569; margin-bottom: 8px; font-size: 0.85rem; font-weight: 700; }
.lc-rate { font-size: 2rem; font-weight: 900; font-family: ui-monospace, monospace; }
.lc-rate.good { color: #10B981; } .lc-rate.warn { color: #F59E0B; } .lc-rate.bad { color: #DC2626; }
.lc-desc { font-size: 0.75rem; color: #64748B; margin-top: 6px; }
.lc-sample { font-size: 0.7rem; color: #94A3B8; margin-top: 2px; }
@media (max-width: 768px) { .layer-cards { grid-template-columns: 1fr; } }
</style>
