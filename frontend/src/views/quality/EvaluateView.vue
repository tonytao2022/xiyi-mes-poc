<template>
  <SectionPanel title="炉次质量评分 Top20" icon="🏆">
    <p class="section-hint">
      借鉴兴澄质量评价：Score = 符合率×100（judge=1 比例）。后续可扩展为 Score=Σ(参数得分×权重)×工序修正系数，配分段/线性扣分。
    </p>
    <DataTable :columns="scoreCols" :rows="scores" :scroll-x="true" />
  </SectionPanel>

  <SectionPanel title="历史最优炉次（按钢种）" icon="⭐">
    <p class="section-hint">借鉴兴澄历史最优指导生产：按钢种查历史最高分炉次，供生产参考。</p>
    <DataTable :columns="bestCols" :rows="best" :scroll-x="true" />
  </SectionPanel>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import SectionPanel from '@/components/cards/SectionPanel.vue'
import DataTable from '@/components/cards/DataTable.vue'
import { qualityApi } from '@/api/modules'

const scores = ref([])
const best = ref([])

const scoreCols = [
  { key: 'rank', title: '排名' },
  { key: 'heat_no', title: '熔炼号', mono: true },
  { key: 'steel_grade', title: '钢种' },
  { key: 'team', title: '班组' },
  { key: 'equipment', title: '设备' },
  { key: 'judged', title: '判定数' },
  { key: 'hit', title: '命中数' },
  { key: 'score', title: '评分', rate: true },
]
const bestCols = [
  { key: 'steel_grade', title: '钢种', mono: true },
  { key: 'heat_no', title: '最优熔炼号', mono: true },
  { key: 'team', title: '班组' },
  { key: 'judged', title: '判定数' },
  { key: 'hit', title: '命中数' },
  { key: 'score', title: '评分', rate: true },
]

onMounted(async () => {
  try {
    const [s, b] = await Promise.all([qualityApi.heatScore(20), qualityApi.historyBest(15)])
    scores.value = s.map((x, i) => ({ ...x, rank: i + 1 }))
    best.value = b
  } catch (e) { console.error(e) }
})
</script>
