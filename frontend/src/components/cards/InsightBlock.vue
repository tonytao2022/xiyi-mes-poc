<template>
  <div class="ib-list">
    <div v-for="(it, i) in items" :key="i" class="ib" :class="levelClass(it.level)">
      <h4>
        <span class="lvl-badge" :class="it.level">{{ it.level }}</span>
        {{ it.title }}
      </h4>
      <div class="ii">{{ it.content }}</div>
    </div>
    <div v-if="!items.length" class="empty">暂无洞察</div>
  </div>
</template>

<script setup>
defineProps({ items: { type: Array, default: () => [] } })
const levelClass = (lvl) => ({
  严重: 'lv-severe', 警告: 'lv-warn', 提示: 'lv-info', 亮点: 'lv-good',
}[lvl] || 'lv-info')
</script>

<style scoped>
.ib-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 1rem;
}
.ib {
  background: var(--glass2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 1rem 1.2rem;
  border-left: 4px solid var(--accent);
  opacity: 0;
  transform: translateX(-16px);
  animation: ibIn 0.5s ease forwards;
}
.ib:nth-child(n) { animation-delay: calc(var(--i, 0) * 0.06s); }
@keyframes ibIn { to { opacity: 1; transform: translateX(0); } }
.ib.lv-severe { border-left-color: var(--red); }
.ib.lv-warn { border-left-color: var(--yellow); }
.ib.lv-info { border-left-color: var(--accent); }
.ib.lv-good { border-left-color: var(--green); }
.ib h4 {
  font-size: 0.9rem;
  color: var(--text);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.lvl-badge {
  font-size: 0.65rem;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 700;
  color: var(--bg);
  white-space: nowrap;
}
.lvl-badge.严重 { background: var(--red); }
.lvl-badge.警告 { background: var(--yellow); }
.lvl-badge.提示 { background: var(--accent); }
.lvl-badge.亮点 { background: var(--green); }
.ii { font-size: 0.85rem; color: var(--dim); line-height: 1.6; }
</style>
