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
  datasets: props.series.map((s, i, arr) => ({
    label: s.label,
    data: s.data,
    borderColor: s.color,
    backgroundColor: s.color + 'e6',
    // Each dataset fills toward the NEXT (smaller) one rather than the
    // previous, so the band between two adjacent lines — cards that reached
    // this stage but not the next — is painted with this stage's own color
    // instead of the following stage's.
    fill: i === arr.length - 1 ? 'origin' : i + 1,
    pointRadius: 0,
    borderWidth: 2,
    tension: 0,
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
