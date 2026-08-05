<template>
  <div class="domain">
    <div class="domain-tabs">
      <button :class="{ active: active === 'comprehensive' }" @click="active = 'comprehensive'">综合成本模型</button>
      <button :class="{ active: active === 'simulation' }" @click="active = 'simulation'">模型模拟</button>
    </div>
    <div class="domain-content">
      <ComprehensiveV2 v-if="active === 'comprehensive'" />
      <SimulationV2 v-else />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Icon from '@/components/common/Icon.vue'
import ComprehensiveV2 from '@/views/v2/ComprehensiveV2.vue'
import SimulationV2 from '@/views/v2/SimulationV2.vue'

const active = ref('comprehensive')
</script>

<style scoped>
.domain-tabs {
  display: flex; gap: 0; border-bottom: 2px solid #E2E8F0; margin-bottom: 20px;
  background: #fff; border-radius: 14px 14px 0 0; padding: 0 8px;
}
.domain-tabs button {
  background: none; border: none; color: #475569; padding: 14px 24px; cursor: pointer;
  font-size: 0.88rem; font-weight: 600; border-bottom: 3px solid transparent; transition: all 0.2s;
  margin-bottom: -2px;
}
.domain-tabs button:hover { color: #0284C7; }
.domain-tabs button.active { color: #0284C7; font-weight: 800; border-bottom-color: #0284C7; }
</style>
