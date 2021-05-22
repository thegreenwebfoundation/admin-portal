import statsCharts from './stats-charts'

console.debug({ chartData: window.chartData})
const ctx = document.getElementById("chart-last-30-days")
const res = statsCharts.render(ctx, window.chartData)
