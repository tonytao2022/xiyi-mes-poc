<template>
  <SectionPanel title="尺寸检验统计（对标 demo S9）" icon="📏">
    <div class="stats">
      <StatCard label="检验样本" :rows="[{ k: '数量', v: dim.sample_count || 0 }]" />
      <StatCard label="内径对角线1(mm)" :rows="[
        { k: '均值', v: dim.diagonal1?.avg ?? '-' },
        { k: '范围', v: (dim.diagonal1?.min ?? '-') + '~' + (dim.diagonal1?.max ?? '-') },
      ]" />
      <StatCard label="内径对角线2(mm)" :rows="[{ k: '均值', v: dim.diagonal2?.avg ?? '-' }]" />
      <StatCard label="对角线差值(mm)" :rows="[{ k: '均值', v: dim.diag_diff?.avg ?? '-' }]" />
      <StatCard label="尺寸合格率" :rows="[{ k: '合格率', v: (dim.dim_pass_rate ?? 0) + '%', cls: 'pass-good' }]" />
    </div>

    <h3 class="sub-title">质量判定汇总</h3>
    <DataTable :columns="judgeCols" :rows="judgeRows" :scroll-x="true" />

    <p v-if="coldUpsettingBad" class="cold-warn">
      ⚠️ 冷镦质量仅 1/5 合格，需重点关注（对标 demo 关注点）
    </p>
  </SectionPanel>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import StatCard from '@/components/cards/StatCard.vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import { qualityApi } from '@/api/modules'

const dim = ref({})

const judgeCols = [
  { key: 'item', title: '判定项' },
  { key: 'pass', title: '合格数' },
  { key: 'n', title: '总数' },
  { key: 'rate', title: '合格率(%)', rate: true },
]
const judgeRows = computed(() =>
  (dim.value.judges || []).map((j) => ({
    ...j,
    rate: j.n ? round(100 * j.pass / j.n, 1) : 0,
  })),
)
function round(v, n) { return Number(v.toFixed(n)) }

const coldUpsettingBad = computed(() => {
  const j = (dim.value.judges || []).find((x) => x.item === '冷镦质量')
  return j && j.pass < j.n
})

onMounted(async () => {
  try { dim.value = await qualityApi.dimensionStats() } catch (e) { console.error(e) }
})
</script>

<style scoped>
.sub-title { margin: 1.2rem 0 0.6rem; font-size: 1rem; color: var(--accent2); font-weight: 600; }
.cold-warn {
  margin-top: 1rem;
  padding: 10px 14px;
  background: rgba(248, 113, 113, 0.1);
  border-left: 3px solid var(--red);
  border-radius: var(--radius-sm);
  color: var(--red);
  font-size: 0.88rem;
}
</style>
