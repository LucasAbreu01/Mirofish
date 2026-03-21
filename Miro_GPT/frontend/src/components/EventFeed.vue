<script setup lang="ts">
defineProps<{
  rounds: Array<Record<string, unknown>>
  events: Array<Record<string, unknown>>
}>()
</script>

<template>
  <section class="feed-grid">
    <article v-for="round in rounds" :key="String(round.round_index)" class="feed-card">
      <div class="feed-head">
        <strong>Round {{ round.round_index }}</strong>
        <span>{{ round.events_count }} events</span>
      </div>
      <ul class="feed-highlights">
        <li
          v-for="highlight in (round.highlights as string[])"
          :key="highlight"
        >
          {{ highlight }}
        </li>
      </ul>
    </article>

    <article class="feed-card full-span">
      <div class="feed-head">
        <strong>Latest events</strong>
        <span>{{ events.length }}</span>
      </div>
      <ul class="feed-events">
        <li
          v-for="event in events.slice(-12).reverse()"
          :key="`${event.round_index}-${event.timestamp}-${event.content}`"
        >
          <span class="feed-badge">{{ event.event_type }}</span>
          <div>
            <strong>Round {{ event.round_index }}</strong>
            <p>{{ event.content }}</p>
          </div>
        </li>
      </ul>
    </article>
  </section>
</template>
