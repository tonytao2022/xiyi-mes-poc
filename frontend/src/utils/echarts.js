import * as echarts from 'echarts'

// 注册暗色玻璃拟态主题，颜色对应 theme.scss 的设计 token
echarts.registerTheme('mes-dark', {
  color: ['#60a5fa', '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#22d3ee', '#f472b6'],
  backgroundColor: 'transparent',
  textStyle: { color: '#94a3b8', fontFamily: 'inherit' },
  title: { textStyle: { color: '#e2e8f0' }, subtextStyle: { color: '#94a3b8' } },
  legend: { textStyle: { color: '#94a3b8' }, inactiveColor: '#475569' },
  tooltip: {
    backgroundColor: 'rgba(15,23,42,0.92)',
    borderColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1,
    textStyle: { color: '#e2e8f0' },
    extraCssText: 'backdrop-filter:blur(12px);border-radius:8px;',
  },
  grid: { containLabel: true },
  categoryAxis: {
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    axisTick: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    axisLabel: { color: '#94a3b8' },
    splitLine: { show: false, lineStyle: { color: 'rgba(255,255,255,0.06)' } },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#94a3b8' },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.06)' } },
  },
  radar: {
    axisName: { color: '#94a3b8' },
    axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
    splitLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
    splitArea: { areaStyle: { color: ['rgba(255,255,255,0.02)', 'rgba(255,255,255,0.04)'] } },
  },
  bar: { itemStyle: { borderRadius: [4, 4, 0, 0] } },
  line: {
    itemStyle: { borderWidth: 2 },
    lineStyle: { width: 2 },
    symbolSize: 6,
    symbol: 'circle',
  },
})

// 浅色主题（demandAI 风格，用于 v2 架构）
echarts.registerTheme('mes-light', {
  color: ['#0284C7', '#38BDF8', '#10B981', '#F59E0B', '#DC2626', '#6366F1', '#94A3B8'],
  backgroundColor: 'transparent',
  textStyle: { color: '#475569', fontFamily: 'inherit' },
  title: { textStyle: { color: '#0F172A' }, subtextStyle: { color: '#64748B' } },
  legend: { textStyle: { color: '#475569' } },
  tooltip: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E2E8F0',
    borderWidth: 1,
    textStyle: { color: '#0F172A' },
    extraCssText: 'box-shadow:0 4px 12px rgba(0,0,0,0.08);border-radius:8px;',
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#E2E8F0' } },
    axisTick: { lineStyle: { color: '#E2E8F0' } },
    axisLabel: { color: '#94A3B8' },
    splitLine: { show: false, lineStyle: { color: '#F1F5F9' } },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#94A3B8' },
    splitLine: { lineStyle: { color: '#F1F5F9' } },
  },
  radar: {
    axisName: { color: '#475569' },
    axisLine: { lineStyle: { color: '#E2E8F0' } },
    splitLine: { lineStyle: { color: '#F1F5F9' } },
    splitArea: { areaStyle: { color: ['#FFFFFF', '#F8FAFC'] } },
  },
  bar: { itemStyle: { borderRadius: [4, 4, 0, 0] } },
  line: { itemStyle: { borderWidth: 2 }, lineStyle: { width: 2 }, symbolSize: 6 },
})

export default echarts
