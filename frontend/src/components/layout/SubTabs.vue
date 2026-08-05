<template>
  <div class="subtabs">
    <RouterLink v-for="t in tabs" :key="t.to" :to="t.to" :class="{ disabled: t.disabled }">
      <span>{{ t.label }}</span>
      <span v-if="t.badge" class="tab-badge">{{ t.badge }}</span>
    </RouterLink>
  </div>
</template>

<script setup>
defineProps({ tabs: { type: Array, default: () => [] } })
</script>

<style scoped>
.subtabs {
  display: flex;
  gap: 4px;
  padding: 8px 2rem;
  overflow-x: auto;
  border-bottom: 1px solid var(--border);
  background: rgba(10, 14, 26, 0.6);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 60px;
  z-index: 50;
  scrollbar-width: thin;
}
.subtabs a {
  color: var(--dim);
  font-size: 0.8rem;
  padding: 6px 12px;
  border-radius: 8px;
  white-space: nowrap;
  text-decoration: none;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.subtabs a:hover {
  color: var(--text);
  background: rgba(255, 255, 255, 0.04);
}
.subtabs a.router-link-active {
  color: var(--accent);
  background: rgba(96, 165, 250, 0.1);
}
.subtabs a.disabled {
  opacity: 0.4;
  pointer-events: none;
}
.tab-badge {
  font-size: 0.62rem;
  background: var(--accent2);
  color: var(--bg);
  border-radius: 3px;
  padding: 1px 4px;
  font-weight: 700;
}
</style>
