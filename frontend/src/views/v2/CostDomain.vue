<template>
  <div class="domain">
    <div class="domain-tabs">
      <button v-for="t in tabs" :key="t.key" :class="{ active: active === t.key }" @click="active = t.key">{{ t.label }}</button>
    </div>
    <div class="domain-content" :key="active">
      <!-- Tab 1: 总览 -->
      <div v-if="active === 'overview'">
        <AnalysisCard :data="ai.overview || {}" />
        <CostV2 />
      </div>

      <!-- Tab 2: 钢铁料 -->
      <div v-else-if="active === 'steel'">
        <AnalysisCard :data="ai.steel_material || {}" />
        <div class="card">
          <h3 class="card-title">废钢料型用量与成本</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>料型</th><th>用量(吨)</th><th>占比</th><th>单价(元/吨)</th><th>成本(元)</th></tr></thead>
              <tbody>
                <tr v-for="t in scrapTypes" :key="t.type">
                  <td class="mono">{{ t.type }}</td><td>{{ fmt(t.weight) }}</td><td>{{ t.pct }}%</td>
                  <td>{{ t.price }}</td><td class="primary">{{ fmt(t.cost) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 3: 合金 -->
      <div v-else-if="active === 'alloy'">
        <AnalysisCard :data="ai.alloy || {}" />
        <div class="card">
          <h3 class="card-title">合金加入量与成本</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>合金</th><th>总加入量</th><th>使用炉数</th><th>均值</th><th>单价</th><th>成本(元)</th></tr></thead>
              <tbody>
                <tr v-for="a in alloyData" :key="a.alloy">
                  <td class="mono">{{ a.alloy }}</td><td>{{ a.amount }}</td><td>{{ a.used }}</td>
                  <td>{{ a.avg }}</td><td>{{ a.price }}</td><td class="primary">{{ fmt(a.cost) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 4: 成本对标 -->
      <div v-else-if="active === 'benchmark'">
        <AnalysisCard :data="ai.benchmark || {}" />
        <div class="card">
          <h3 class="card-title">钢种直接成本排名</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>钢种</th><th>炉数</th><th>废钢(吨)</th><th>单炉(吨)</th></tr></thead>
              <tbody>
                <tr v-for="g in gradeCosts" :key="g.grade">
                  <td class="mono">{{ g.grade }}</td><td>{{ g.heats }}</td><td>{{ fmt(g.weight) }}</td>
                  <td class="primary">{{ g.per_heat }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 5: 价格管理 -->
      <div v-else-if="active === 'price'">
        <AnalysisCard :data="ai.price_risk || {}" />
        <div class="card">
          <h3 class="card-title">SMM实时价格</h3>
          <div class="tbl-wrap">
            <table class="data-table">
              <thead><tr><th>品种</th><th>地区</th><th>日期</th><th>均价(元/吨)</th><th>来源</th></tr></thead>
              <tbody>
                <tr v-for="p in prices" :key="p.price_id">
                  <td class="mono">{{ p.item_name }}</td><td>{{ p.region }}</td><td>{{ p.price_date }}</td>
                  <td class="primary">{{ fmt(p.unit_price) }}</td><td>{{ p.source }}</td>
                </tr>
                <tr v-if="!prices.length"><td colspan="5" class="empty">暂无SMM价格数据</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import CostV2 from '@/views/v2/CostV2.vue'
import AnalysisCard from '@/components/common/AnalysisCard.vue'
import { costApi, priceApi } from '@/api/modules'

const active = ref('overview')
const tabs = [
  { key: 'overview', label: '总览' },
  { key: 'steel', label: '钢铁料' },
  { key: 'alloy', label: '合金' },
  { key: 'benchmark', label: '成本对标' },
  { key: 'price', label: '价格管理' },
]
const ai = ref({})
const scrapTypes = ref([])
const alloyData = ref([])
const gradeCosts = ref([])
const prices = ref([])
const fmt = (v) => Number(v || 0).toLocaleString('zh-CN', { maximumFractionDigits: 0 })

onMounted(async () => {
  try {
    const [aiData, scrap, alloy, grade, priceList] = await Promise.all([
      costApi.aiAnalysis(),
      costApi.scrapOverview(),
      costApi.alloyOverview(),
      costApi.scrapByGrade(10),
      priceApi.list(),
    ])
    ai.value = aiData
    scrapTypes.value = (scrap.types || []).map(t => ({
      type: t.scrap_type, weight: t.weight, pct: t.pct,
      price: t.price || 2800, cost: t.weight * (t.price || 2800)
    }))
    alloyData.value = (alloy || []).map(a => ({
      alloy: a.alloy, amount: a.avg_amount, used: a.used_count, avg: a.avg_amount, price: 8000,
      cost: (a.avg_amount || 0) * (a.used_count || 0) * 8000
    }))
    gradeCosts.value = (grade || []).map(g => ({
      grade: g.steel_grade, heats: g.heats, weight: g.total_weight, per_heat: (g.total_weight / g.heats).toFixed(1)
    }))
    prices.value = priceList || []
  } catch (e) { console.error(e) }
})
</script>

<style scoped>
.domain-tabs { display: flex; gap: 0; border-bottom: 2px solid #E2E8F0; margin-bottom: 20px; background: #fff; border-radius: 14px 14px 0 0; padding: 0 8px; overflow-x: auto; }
.domain-tabs button { background: none; border: none; color: #475569; padding: 14px 20px; cursor: pointer; font-size: 0.88rem; font-weight: 600; border-bottom: 3px solid transparent; transition: all 0.2s; margin-bottom: -2px; white-space: nowrap; }
.domain-tabs button:hover { color: #0284C7; }
.domain-tabs button.active { color: #0284C7; font-weight: 800; border-bottom-color: #0284C7; }
.domain-content { color: #0F172A; }
.card { background: #fff; border: 1px solid #E2E8F0; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.card-title { font-size: 1rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; }
.tbl-wrap { overflow-x: auto; border-radius: 8px; border: 1px solid #E2E8F0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; background: #fff; }
.data-table th { background: #F0F9FF; color: #0369A1; padding: 10px 12px; text-align: left; font-weight: 700; white-space: nowrap; }
.data-table td { padding: 8px 12px; border-bottom: 1px solid #F1F5F9; color: #475569; }
.data-table tr:hover td { background: #F8FAFC; }
.mono { font-family: ui-monospace, monospace; color: #0369A1; font-weight: 600; }
.primary { color: #0284C7; font-weight: 700; }
.empty { text-align: center; color: #94A3B8; padding: 20px; }
</style>
