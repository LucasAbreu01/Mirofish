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
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background-color: #0d1117;
  color: #e6edf3;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}
</style>
