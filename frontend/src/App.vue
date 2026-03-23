<template>
  <router-view />
</template>

<style>
:root {
  --accent: #ff6b35;
  --bg: #0d1117;
  --bg-secondary: #161b22;
  --bg-card: #1c2128;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --border: #30363d;
  --success: #3fb950;
  --error: #f85149;
  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background-color: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}
</style>
