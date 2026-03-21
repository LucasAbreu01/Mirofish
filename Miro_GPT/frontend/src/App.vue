<script setup lang="ts">
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div>
        <p class="eyebrow">Miro_GPT</p>
        <h1>Mini MiroFish</h1>
      </div>
      <p class="header-copy">
        Upload, ontology, graph, simulation, report. Single-user and local-first.
      </p>
    </header>

    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <Suspense>
          <template #default>
            <component :is="Component" />
          </template>
          <template #fallback>
            <section class="stack">
              <article class="panel">
                <p class="eyebrow">Loading</p>
                <h2>Preparing view</h2>
                <p>The workspace is fetching the latest project state.</p>
              </article>
            </section>
          </template>
        </Suspense>
      </RouterView>
    </main>
  </div>
</template>
