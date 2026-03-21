<template>
  <div ref="container" class="graph-panel">
    <svg ref="svgEl"></svg>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  graphData: {
    type: Object,
    default: () => ({ nodes: [], edges: [] })
  }
})

const emit = defineEmits(['node-click'])

const container = ref(null)
const svgEl = ref(null)

let simulation = null
let resizeObserver = null

const TYPE_COLORS = {
  Person: '#ff6b35',
  Organization: '#3fb950',
  Location: '#58a6ff',
  Event: '#d2a8ff',
  Concept: '#f0883e'
}
const DEFAULT_COLOR = '#8b949e'

function getColor(type) {
  if (!type) return DEFAULT_COLOR
  // Normalize: "person" -> "Person", "company" -> "Organization", etc.
  const typeMap = {
    person: 'Person',
    human: 'Person',
    people: 'Person',
    organization: 'Organization',
    company: 'Organization',
    org: 'Organization',
    government: 'Organization',
    ngo: 'Organization',
    location: 'Location',
    place: 'Location',
    city: 'Location',
    country: 'Location',
    event: 'Event',
    concept: 'Concept',
    idea: 'Concept',
    product: 'Concept',
    technology: 'Concept',
    ai_platform: 'Concept',
  }
  const normalized = typeMap[type.toLowerCase()] || type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
  return TYPE_COLORS[normalized] || DEFAULT_COLOR
}

function render() {
  if (!svgEl.value || !container.value) return

  const svg = d3.select(svgEl.value)
  svg.selectAll('*').remove()

  const nodes = (props.graphData?.nodes || []).map(d => ({ ...d }))
  const edges = (props.graphData?.edges || []).map(d => ({ ...d }))

  if (!nodes.length) return

  const width = container.value.clientWidth || 800
  const height = container.value.clientHeight || 600

  svg.attr('width', width).attr('height', height)

  // Arrow marker
  svg.append('defs').append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 28)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#484f58')

  // Zoom group
  const g = svg.append('g')

  const zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  svg.call(zoom)

  // Links
  const link = g.append('g')
    .selectAll('line')
    .data(edges)
    .join('line')
    .attr('stroke', '#484f58')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arrowhead)')

  // Edge labels
  const edgeLabel = g.append('g')
    .selectAll('text')
    .data(edges)
    .join('text')
    .text(d => d.relation_type || '')
    .attr('font-size', '9px')
    .attr('fill', '#6e7681')
    .attr('text-anchor', 'middle')
    .attr('font-family', "'JetBrains Mono', monospace")
    .style('pointer-events', 'none')

  // Node groups
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      event.stopPropagation()
      emit('node-click', d)
    })

  // Circles
  node.append('circle')
    .attr('r', 16)
    .attr('fill', d => getColor(d.entity_type))
    .attr('stroke', d => d3.color(getColor(d.entity_type)).brighter(0.6))
    .attr('stroke-width', 2)

  // Node labels
  node.append('text')
    .text(d => d.name || d.entity_name || d.id || '')
    .attr('dy', 30)
    .attr('text-anchor', 'middle')
    .attr('fill', '#e6edf3')
    .attr('font-size', '10px')
    .attr('font-family', "'JetBrains Mono', monospace")
    .style('pointer-events', 'none')

  // Drag behavior
  const drag = d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    })
    .on('drag', (event, d) => {
      d.fx = event.x
      d.fy = event.y
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
    })

  node.call(drag)

  // Simulation
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges)
      .id(d => d.id)
      .distance(150)
    )
    .force('charge', d3.forceManyBody().strength(-400))
    .force('collide', d3.forceCollide().radius(40))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      edgeLabel
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2 - 6)

      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })
}

function cleanup() {
  if (simulation) {
    simulation.stop()
    simulation = null
  }
}

watch(
  () => props.graphData,
  () => {
    cleanup()
    nextTick(render)
  },
  { deep: true }
)

onMounted(() => {
  render()
  resizeObserver = new ResizeObserver(() => {
    cleanup()
    render()
  })
  if (container.value) {
    resizeObserver.observe(container.value)
  }
})

onBeforeUnmount(() => {
  cleanup()
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<style scoped>
.graph-panel {
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--bg);
  border-radius: 8px;
}

.graph-panel svg {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
