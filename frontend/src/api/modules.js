import http from './http'

export const overviewApi = {
  kpi: () => http.get('/overview/kpi'),
  directCost: () => http.get('/overview/direct-cost'),
  insights: () => http.get('/overview/insights'),
}

export const qualityApi = {
  complianceOverview: () => http.get('/quality/compliance-overview'),
  complianceByDimension: (dim, process) =>
    http.get('/quality/compliance-by-dimension', { params: { dim, process } }),
  indicatorRanking: (process, order = 'asc') =>
    http.get('/quality/indicator-ranking', { params: { process, order } }),
  mechanicalStats: () => http.get('/quality/mechanical-stats'),
  mechanicalDistribution: () => http.get('/quality/mechanical-distribution'),
  chemicalRadar: () => http.get('/quality/chemical-radar'),
  singleDeviation: (sampleLotNo) =>
    http.get('/quality/single-deviation', { params: { sample_lot_no: sampleLotNo } }),
  heatScore: (limit = 20) => http.get('/quality/heat-score', { params: { limit } }),
  historyBest: (limit = 10) => http.get('/quality/history-best', { params: { limit } }),
  heatTrace: (heatNo) => http.get('/quality/heat-trace', { params: { heat_no: heatNo } }),
  heatingTemperature: () => http.get('/quality/heating-temperature'),
  rollingTemperatureSeries: (limit = 60) => http.get('/quality/rolling-temperature-series', { params: { limit } }),
  hitRateDistribution: () => http.get('/quality/hit-rate-distribution'),
  indicatorDetail: (process, indicator) =>
    http.get('/quality/indicator-detail', { params: { process, indicator } }),
  correlation: () => http.get('/quality/correlation'),
  scatter: (x, y) => http.get('/quality/scatter', { params: { x, y } }),
  dimensionStats: () => http.get('/quality/dimension-stats'),
  mechanicalHistogram: () => http.get('/quality/mechanical-histogram'),
  chemicalStats: () => http.get('/quality/chemical-stats'),
  complianceByGrade: (process) => http.get('/quality/compliance-by-grade', { params: { process } }),
  aiAnalysis: () => http.get('/quality/ai-analysis'),
  aiTrace: (heatNo) => http.get('/quality/ai-trace', { params: { heat_no: heatNo } }),
  insights: () => http.get('/quality/insights'),
}

export const costApi = {
  scrapOverview: () => http.get('/cost/scrap-overview'),
  scrapByGrade: (limit = 10) => http.get('/cost/scrap-by-grade', { params: { limit } }),
  scrapMatrix: (limit = 8) => http.get('/cost/scrap-matrix', { params: { limit } }),
  alloyOverview: () => http.get('/cost/alloy-overview'),
  insights: () => http.get('/cost/insights'),
  aiAnalysis: () => http.get('/cost/ai-analysis'),
}

export const efficiencyApi = {
  durationStats: () => http.get('/efficiency/duration-stats'),
  heatCountByTeam: () => http.get('/efficiency/heat-count-by-team'),
  rollingShiftOutput: () => http.get('/efficiency/rolling-shift-output'),
  heatingStats: () => http.get('/efficiency/heating-stats'),
  equipmentOutput: () => http.get('/efficiency/equipment-output'),
  insights: () => http.get('/efficiency/insights'),
  aiAnalysis: () => http.get('/efficiency/ai-analysis'),
}

export const priceApi = {
  list: (category) => http.get('/price/list', { params: { category } }),
  estimated: () => http.get('/price/estimated-prices'),
}

export const crossoverApi = {
  all: () => http.get('/crossover/all'),
  qualityCost: () => http.get('/crossover/quality-cost'),
  qualityEfficiency: () => http.get('/crossover/quality-efficiency'),
  costEfficiency: () => http.get('/crossover/cost-efficiency'),
}

export const comprehensiveApi = {
  model: (limit = 50) => http.get('/comprehensive/model', { params: { limit } }),
  aiAnalysis: () => http.get('/comprehensive/ai-analysis'),
  qualityLossDetail: () => http.get('/comprehensive/quality-loss-detail'),
  efficiencyLossDetail: () => http.get('/comprehensive/efficiency-loss-detail'),
  tradeoff: () => http.get('/comprehensive/tradeoff'),
  lossSource: () => http.get('/comprehensive/loss-source'),
  simulation: () => http.get('/comprehensive/simulation'),
  sensitivity: (variable) => http.get('/comprehensive/sensitivity', { params: { variable } }),
  recipe: (totalWeight = 100, lowEndLimit = 20, metalReq = 0.9) =>
    http.get('/comprehensive/recipe', { params: { total_weight: totalWeight, low_end_limit: lowEndLimit, metal_requirement: metalReq } }),
  interactive: (p) => http.get('/comprehensive/interactive', { params: p }),
}
