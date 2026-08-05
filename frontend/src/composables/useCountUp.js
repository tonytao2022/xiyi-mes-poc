import { ref, watch, onMounted } from 'vue'

/**
 * 数字滚动动画（easeOutCubic），对应 demo 的 CountUp。
 * @param target 响应式数值
 * @param duration 毫秒
 */
export function useCountUp(target, duration = 1200) {
  const display = ref(0)
  let raf = null

  const run = (to) => {
    if (raf) cancelAnimationFrame(raf)
    const from = display.value
    const start = performance.now()
    const step = (now) => {
      const p = Math.min((now - start) / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      display.value = from + (to - from) * eased
      if (p < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
  }

  onMounted(() => run(Number(target.value) || 0))
  watch(target, (v) => run(Number(v) || 0))

  return { display }
}
