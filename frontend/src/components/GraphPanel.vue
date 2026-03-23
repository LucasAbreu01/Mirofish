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
  Concept: '#f0883e',
  Unknown: '#8b949e'
}
const DEFAULT_COLOR = '#8b949e'

function getColor(type) {
  if (!type) return DEFAULT_COLOR
  const typeMap = {
    person: 'Person', human: 'Person', people: 'Person',
    personagem: 'Person', autor: 'Person', escritor: 'Person',
    jogador: 'Person', técnico: 'Person', psicólogo: 'Person',
    sócio: 'Person', advogado: 'Person', ceo: 'Person',
    organization: 'Organization', company: 'Organization', org: 'Organization',
    government: 'Organization', ngo: 'Organization',
    instituição: 'Organization', empresa: 'Organization', escritório: 'Organization',
    clube: 'Organization', time: 'Organization', entidade: 'Organization',
    location: 'Location', place: 'Location', city: 'Location', country: 'Location',
    local: 'Location', cidade: 'Location',
    event: 'Event', evento: 'Event',
    concept: 'Concept', idea: 'Concept', product: 'Concept', technology: 'Concept',
    ai_platform: 'Concept', obra: 'Concept', conceito: 'Concept',
    política: 'Concept', lei: 'Concept', regulação: 'Concept',
    sentimento: 'Event', tema: 'Concept',
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

  const defs = svg.append('defs')

  // Glow filter
  const filter = defs.append('filter').attr('id', 'glow')
  filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur')
  filter.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'blur').attr('operator', 'over')

  // Hover glow filter (stronger)
  const hoverFilter = defs.append('filter').attr('id', 'glow-hover')
  hoverFilter.append('feGaussianBlur').attr('stdDeviation', '6').attr('result', 'blur')
  hoverFilter.append('feComposite').attr('in', 'SourceGraphic').attr('in2', 'blur').attr('operator', 'over')

  // Arrow marker
  defs.append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 24)
    .attr('refY', 0)
    .attr('markerWidth', 5)
    .attr('markerHeight', 5)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-4L8,0L0,4')
    .attr('fill', '#3d444d')

  // Gradient for links
  defs.append('linearGradient')
    .attr('id', 'link-gradient')
    .attr('gradientUnits', 'userSpaceOnUse')
    .selectAll('stop')
    .data([
      { offset: '0%', color: 'rgba(88, 166, 255, 0.3)' },
      { offset: '100%', color: 'rgba(88, 166, 255, 0.08)' }
    ])
    .join('stop')
    .attr('offset', d => d.offset)
    .attr('stop-color', d => d.color)

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
    .attr('stroke', '#2d333b')
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.6)
    .attr('marker-end', 'url(#arrowhead)')

  // Edge labels
  const edgeLabel = g.append('g')
    .selectAll('text')
    .data(edges)
    .join('text')
    .text(d => d.relation_type || '')
    .attr('font-size', '8px')
    .attr('fill', '#484f58')
    .attr('text-anchor', 'middle')
    .attr('font-family', "'JetBrains Mono', monospace")
    .style('pointer-events', 'none')

  // Node groups
  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .style('cursor', 'pointer')

  // Outer glow ring
  node.append('circle')
    .attr('r', 20)
    .attr('fill', 'none')
    .attr('stroke', d => getColor(d.entity_type))
    .attr('stroke-width', 1)
    .attr('stroke-opacity', 0.2)
    .attr('filter', 'url(#glow)')

  // Main circle
  node.append('circle')
    .attr('r', 14)
    .attr('fill', d => {
      const c = d3.color(getColor(d.entity_type))
      c.opacity = 0.15
      return c + ''
    })
    .attr('stroke', d => getColor(d.entity_type))
    .attr('stroke-width', 2)
    .attr('class', 'node-circle')

  // Inner dot
  node.append('circle')
    .attr('r', 4)
    .attr('fill', d => getColor(d.entity_type))

  // Node labels
  node.append('text')
    .text(d => d.name || d.entity_name || d.id || '')
    .attr('dy', 28)
    .attr('text-anchor', 'middle')
    .attr('fill', '#adbac7')
    .attr('font-size', '10px')
    .attr('font-weight', '500')
    .attr('font-family', "'JetBrains Mono', monospace")
    .style('pointer-events', 'none')
    .style('text-shadow', '0 1px 4px rgba(0,0,0,0.8)')

  // Hover effects
  node
    .on('mouseenter', function(event, d) {
      d3.select(this).select('.node-circle')
        .transition().duration(200)
        .attr('r', 18)
        .attr('stroke-width', 3)
        .attr('fill', () => {
          const c = d3.color(getColor(d.entity_type))
          c.opacity = 0.3
          return c + ''
        })
      d3.select(this).select('text')
        .transition().duration(200)
        .attr('fill', '#e6edf3')
        .attr('font-size', '11px')
      // Highlight connected links
      link.attr('stroke', l =>
        (l.source === d || l.target === d) ? getColor(d.entity_type) : '#2d333b'
      ).attr('stroke-opacity', l =>
        (l.source === d || l.target === d) ? 0.8 : 0.3
      ).attr('stroke-width', l =>
        (l.source === d || l.target === d) ? 2.5 : 1.5
      )
    })
    .on('mouseleave', function(event, d) {
      d3.select(this).select('.node-circle')
        .transition().duration(300)
        .attr('r', 14)
        .attr('stroke-width', 2)
        .attr('fill', () => {
          const c = d3.color(getColor(d.entity_type))
          c.opacity = 0.15
          return c + ''
        })
      d3.select(this).select('text')
        .transition().duration(300)
        .attr('fill', '#adbac7')
        .attr('font-size', '10px')
      link.attr('stroke', '#2d333b')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', 1.5)
    })
    .on('click', (event, d) => {
      event.stopPropagation()
      emit('node-click', d)
    })

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
      .distance(120)
    )
    .force('charge', d3.forceManyBody().strength(-350))
    .force('collide', d3.forceCollide().radius(35))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('x', d3.forceX(width / 2).strength(0.05))
    .force('y', d3.forceY(height / 2).strength(0.05))
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
  background: radial-gradient(ellipse at center, #131920 0%, #0d1117 70%);
  border-radius: 8px;
}

.graph-panel svg {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
