import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 导航滚动高亮 + 平滑滚动。对应 demo 的 updateNav / 平滑滚动。
 * @param sections 数组 [{ id, label }]
 */
export function useNavScroll(sections) {
  const active = ref(sections[0]?.id || '')

  const onScroll = () => {
    const pos = window.scrollY + 110
    let cur = sections[0]?.id || ''
    for (const s of sections) {
      const el = document.getElementById(s.id)
      if (el && el.offsetTop <= pos) cur = s.id
    }
    active.value = cur
  }

  const scrollTo = (id) => {
    const el = document.getElementById(id)
    if (el) window.scrollTo({ top: el.offsetTop - 70, behavior: 'smooth' })
  }

  onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
  onUnmounted(() => window.removeEventListener('scroll', onScroll))

  return { active, scrollTo }
}
