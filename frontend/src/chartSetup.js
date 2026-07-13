import {
  Chart,
  LineElement,
  PointElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'

Chart.register(
  LineElement,
  PointElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Filler,
  Tooltip,
  Legend,
)

export const CHART_GRID_COLOR = 'rgba(148, 163, 184, 0.1)'
export const CHART_TICK_COLOR = '#94a3b8'

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: '#1e293b',
  borderColor: '#475569',
  borderWidth: 1,
  titleColor: '#f1f5f9',
  bodyColor: '#cbd5e1',
  padding: 10,
  cornerRadius: 8,
  displayColors: true,
}
