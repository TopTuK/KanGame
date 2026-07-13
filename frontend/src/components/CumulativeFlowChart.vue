<template>
  <div class="relative h-64">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import '../chartSetup.js'
import { CHART_GRID_COLOR, CHART_TICK_COLOR, CHART_TOOLTIP_STYLE } from '../chartSetup.js'

const props = defineProps({
  days: { type: Array, required: true },
  // ordered largest→smallest cumulative count: [{ key, label, color, data }]
  series: { type: Array, required: true },
})

const chartData = computed(() => ({
  labels: props.days,
  datasets: props.series.map((s, i) => ({
    label: s.label,
    data: s.data,
    borderColor: s.color,
    backgroundColor: s.color + '55',
    fill: i === 0 ? 'origin' : '-1',
    pointRadius: 0,
    borderWidth: 2,
    tension: 0.15,
  })),
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { labels: { color: CHART_TICK_COLOR, boxWidth: 12, font: { family: 'Inter' } } },
    tooltip: CHART_TOOLTIP_STYLE,
  },
  scales: {
    x: { grid: { color: CHART_GRID_COLOR }, ticks: { color: CHART_TICK_COLOR } },
    y: { grid: { color: CHART_GRID_COLOR }, ticks: { color: CHART_TICK_COLOR }, beginAtZero: true },
  },
}
</script>
