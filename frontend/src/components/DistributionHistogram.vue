<template>
  <div class="relative h-56">
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import '../chartSetup.js'
import { CHART_GRID_COLOR, CHART_TICK_COLOR, CHART_TOOLTIP_STYLE } from '../chartSetup.js'

const props = defineProps({
  values: { type: Array, required: true },
  color: { type: String, default: '#34d399' },
  unitLabel: { type: String, default: 'days' },
})

const buckets = computed(() => {
  if (!props.values.length) return { labels: [], counts: [] }
  const min = Math.min(...props.values)
  const max = Math.max(...props.values)
  const labels = []
  const counts = []
  for (let v = min; v <= max; v++) {
    labels.push(String(v))
    counts.push(props.values.filter((x) => x === v).length)
  }
  return { labels, counts }
})

const chartData = computed(() => ({
  labels: buckets.value.labels,
  datasets: [
    {
      label: props.unitLabel,
      data: buckets.value.counts,
      backgroundColor: props.color + 'aa',
      borderColor: props.color,
      borderWidth: 1,
      borderRadius: 4,
      maxBarThickness: 36,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: CHART_TOOLTIP_STYLE,
  },
  scales: {
    x: { grid: { display: false }, ticks: { color: CHART_TICK_COLOR } },
    y: {
      grid: { color: CHART_GRID_COLOR },
      ticks: { color: CHART_TICK_COLOR, precision: 0 },
      beginAtZero: true,
    },
  },
}
</script>
