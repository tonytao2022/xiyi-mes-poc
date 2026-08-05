<template>
  <div class="app-layout v2-app">
    <header class="top-bar">
      <div class="brand">
        <span class="brand-icon"><Icon name="factory" :size="28" /></span>
        <div>
          <div class="brand-title">钢铁 MES · 工艺质量成本效率协同</div>
          <div class="brand-sub">Steel Manufacturing Intelligence</div>
        </div>
      </div>
      <div class="user">
        <span class="user-avatar">工</span>
        <span class="user-name">工艺工程师 ▾</span>
      </div>
    </header>

    <div class="layout-body">
      <!-- 一级图标轨（定域，不跳页） -->
      <aside class="rail">
        <button
          v-for="g in groups"
          :key="g.id"
          class="rail-btn"
          :class="{ active: activeGroup === g.id }"
          @click="activeGroup = g.id"
        >
          <span class="rail-icon"><Icon :name="g.icon" /></span>
          <span class="rail-label">{{ g.label }}</span>
        </button>
      </aside>

      <!-- 主内容区：根据域渲染，Tab在域组件内 -->
      <main class="main">
        <WorkbenchV2 v-if="activeGroup === 'workbench'" @navigate="activeGroup = $event" />
        <QualityDomain v-else-if="activeGroup === 'quality'" />
        <CostDomain v-else-if="activeGroup === 'cost'" />
        <EfficiencyDomain v-else-if="activeGroup === 'efficiency'" />
        <ComprehensiveDomain v-else-if="activeGroup === 'comprehensive'" />
        <AiAgentV2 v-else-if="activeGroup === 'aiagent'" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { provide, ref } from 'vue'
import '@/styles/v2-theme.scss'
import Icon from '@/components/common/Icon.vue'
import WorkbenchV2 from '@/views/v2/WorkbenchV2.vue'
import QualityDomain from '@/views/v2/QualityDomain.vue'
import CostDomain from '@/views/v2/CostDomain.vue'
import EfficiencyDomain from '@/views/v2/EfficiencyDomain.vue'
import ComprehensiveDomain from '@/views/v2/ComprehensiveDomain.vue'
import AiAgentV2 from '@/views/v2/AiAgentV2.vue'

const activeGroup = ref('workbench')
provide('echartTheme', 'mes-light')

const groups = [
  { id: 'workbench', icon: 'chart', label: '工作台' },
  { id: 'aiagent', icon: 'scope', label: 'AI智体' },
  { id: 'quality', icon: 'target', label: '质量' },
  { id: 'cost', icon: 'dollar', label: '成本' },
  { id: 'efficiency', icon: 'zap', label: '效率' },
  { id: 'comprehensive', icon: 'link', label: '综合分析' },
]
</script>

<style scoped>
.app-layout { min-height: 100vh; background: #F8FAFC; }
.top-bar {
  position: fixed; top: 0; left: 0; right: 0; height: 64px; z-index: 200;
  background: #FFFFFF; border-bottom: 1px solid #E5E7EB;
  display: flex; align-items: center; justify-content: space-between; padding: 0 24px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-icon { font-size: 1.6rem; }
.brand-title { font-size: 1rem; font-weight: 900; color: #0369A1; letter-spacing: 0.5px; }
.brand-sub { font-size: 0.65rem; color: #94A3B8; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
.user { display: flex; align-items: center; gap: 10px; }
.user-avatar { width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #0284C7, #0369A1); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; }
.user-name { color: #475569; font-size: 0.85rem; font-weight: 600; }
.layout-body { padding-top: 64px; display: flex; min-height: calc(100vh - 64px); background: #F8FAFC; }
.rail {
  width: 80px; background: #131E32; display: flex; flex-direction: column;
  padding: 24px 0; gap: 16px; align-items: center; position: fixed; top: 64px; bottom: 0; left: 0; z-index: 100;
}
.rail-btn {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  width: 60px; height: 60px; border-radius: 12px; background: none; border: none; cursor: pointer;
  color: #94A3B8; transition: all 0.3s;
}
.rail-btn:hover { color: #E2E8F0; }
.rail-btn.active { color: #fff; background: linear-gradient(135deg, #0284C7, #0369A1); box-shadow: 0 4px 12px rgba(2,132,199,0.4); }
.rail-icon { font-size: 22px; }
.rail-label { font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }
.main { flex: 1; margin-left: 80px; padding: 24px; overflow-y: auto; background: #F8FAFC; min-height: calc(100vh - 64px); }
</style>
