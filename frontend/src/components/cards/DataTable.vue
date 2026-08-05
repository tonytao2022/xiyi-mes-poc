<template>
  <div class="tbl-wrap">
    <table :class="{ 'scroll-x': scrollX }">
      <thead>
        <tr>
          <th v-for="c in columns" :key="c.key">{{ c.title }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, i) in rows" :key="i">
          <td v-for="c in columns" :key="c.key">
            <span v-if="c.mono" class="mono">{{ fmt(row[c.key], c) }}</span>
            <span v-else :class="rateClass(row[c.key], c)">{{ fmt(row[c.key], c) }}</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length" class="empty">暂无数据</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  scrollX: { type: Boolean, default: false },
})

function fmt(v, c) {
  if (v === null || v === undefined || v === '') return '-'
  if (c.format) return c.format(v)
  return v
}

function rateClass(v, c) {
  if (!c.rate) return ''
  const n = Number(v)
  if (isNaN(n)) return ''
  if (n >= 95) return 'pass-good'
  if (n >= 80) return 'pass-warn'
  return 'pass-bad'
}
</script>
