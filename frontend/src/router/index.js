import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue') },
  {
    path: '/quality',
    component: () => import('@/layouts/QualityLayout.vue'),
    children: [
      { path: '', redirect: '/quality/compliance' },
      { path: 'compliance', name: 'q-compliance', component: () => import('@/views/quality/ComplianceView.vue') },
      { path: 'indicators', name: 'q-indicators', component: () => import('@/views/quality/IndicatorsView.vue') },
      { path: 'mechanical', name: 'q-mechanical', component: () => import('@/views/quality/MechanicalView.vue') },
      { path: 'chemical', name: 'q-chemical', component: () => import('@/views/quality/ChemicalView.vue') },
      { path: 'deviation', name: 'q-deviation', component: () => import('@/views/quality/DeviationView.vue') },
      { path: 'dimension', name: 'q-dimension', component: () => import('@/views/quality/DimensionView.vue') },
      { path: 'correlation', name: 'q-correlation', component: () => import('@/views/quality/CorrelationView.vue') },
      { path: 'rolling', name: 'q-rolling', component: () => import('@/views/quality/RollingView.vue') },
      { path: 'evaluate', name: 'q-evaluate', component: () => import('@/views/quality/EvaluateView.vue') },
      { path: 'trace', name: 'q-trace', component: () => import('@/views/quality/TraceView.vue') },
    ],
  },
  { path: '/cost', name: 'cost', component: () => import('@/views/CostView.vue') },
  { path: '/efficiency', name: 'efficiency', component: () => import('@/views/EfficiencyView.vue') },
  { path: '/overview', name: 'overview', component: () => import('@/views/OverviewView.vue') },
  {
    path: '/crossover',
    component: () => import('@/layouts/CrossoverLayout.vue'),
    children: [
      { path: '', redirect: '/crossover/quality-cost' },
      { path: 'quality-cost', name: 'xc-qc', component: () => import('@/views/crossover/QualityCostView.vue') },
      { path: 'quality-efficiency', name: 'xc-qe', component: () => import('@/views/crossover/QualityEfficiencyView.vue') },
      { path: 'cost-efficiency', name: 'xc-ce', component: () => import('@/views/crossover/CostEfficiencyView.vue') },
    ],
  },
  { path: '/comprehensive', name: 'comprehensive', component: () => import('@/views/ComprehensiveView.vue') },
  { path: '/simulation', name: 'simulation', component: () => import('@/views/SimulationView.vue') },
  { path: '/v2', redirect: '/v2/workbench' },
  { path: '/v2/workbench', name: 'v2', component: () => import('@/layouts/AppLayout.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

export default router
