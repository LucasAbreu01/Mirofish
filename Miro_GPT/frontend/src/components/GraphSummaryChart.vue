<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BarChart, type BarSeriesOption } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  type GridComponentOption,
  type TooltipComponentOption,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { type ComposeOption, type ECharts, init, use } from 'echarts/core'

import type { GraphSnapshot } from '../types'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

type ChartOption = ComposeOption<GridComponentOption | TooltipComponentOption | BarSeriesOption>

const props = defineProps<{
  snapshot?: GraphSnapshot | null
}>()

const host = ref<HTMLElement | null>(null)
let chart: ECharts | null = null

const option = computed(() => {
  const entries = Object.entries(props.snapshot?.entity_types || {})
  return {
    backgroundColor: 'transparent',
    grid: { left: 12, right: 12, top: 18, bottom: 20, containLabel: true },
    xAxis: {
      type: 'category',
      data: entries.map(([label]) => label),
      axisLabel: { color: '#8e959b', fontSize: 11 },
      axisLine: { lineStyle: { color: '#31383c' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#8e959b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#222a2e' } },
    },
    series: [
      {
        type: 'bar',
        data: entries.map(([, value]) => value),
        itemStyle: {
          color: '#d88f43',
          borderRadius: [10, 10, 2, 2],
        },
      },
    ],
    tooltip: {
      trigger: 'axis',
    },
  }
})

function renderChart() {
  if (!host.value) {
    return
  }
  if (!chart) {
    chart = init(host.value)
  }
  chart.setOption(option.value as ChartOption)
  chart.resize()
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', renderChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', renderChart)
  chart?.dispose()
  chart = null
})

watch(option, () => {
  renderChart()
})
</script>

<template>
  <div class="chart-frame">
    <div ref="host" class="chart-host"></div>
  </div>
</template>
