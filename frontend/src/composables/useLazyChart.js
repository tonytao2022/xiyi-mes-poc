import { useIntersectionObserver } from '@vueuse/core'

/**
 * 图表滚动懒加载：元素进入视口（threshold 0.15）时触发一次初始化。
 * 对应 demo 中的 icos / initChartOnScroll。
 */
export function useLazyChart(target, onVisible) {
  const { stop } = useIntersectionObserver(
    target,
    ([entry]) => {
      if (entry.isIntersecting) {
        onVisible()
        stop()
      }
    },
    { threshold: 0.15 },
  )
  return { stop }
}
