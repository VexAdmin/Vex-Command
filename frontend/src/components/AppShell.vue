<template>
  <div class="app">
    <aside class="side">
      <div class="brand">
        <img src="/vex-logo.svg" alt="VEX" />
        <span class="brand-sub">Command</span>
      </div>
      <div class="nav-scroll">
        <template v-for="section in sections" :key="section.label">
          <div class="nav-section">{{ section.label }}</div>
          <RouterLink
            v-for="item in section.items"
            :key="item.to"
            class="nav-btn"
            :class="{ active: isOn(item.to) }"
            :to="item.to"
          >
            <span class="ico">{{ item.ico }}</span>{{ item.label }}
          </RouterLink>
        </template>
      </div>
      <div class="side-foot">
        <strong>ops.vexraptor.com</strong>
        Founder only · never in tenant nav
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="crumb">Founder Console / <b>{{ title }}</b></div>
        <div class="top-actions">
          <span class="pill"><span class="dot" /> {{ datasetLabel }}</span>
          <span class="pill mono">FY2026 · USD</span>
          <button class="btn" type="button" @click="exportCsv">Export CSV</button>
          <button class="btn primary" type="button" @click="runBrief">Weekly brief</button>
        </div>
      </header>
      <div class="content">
        <RouterView />
      </div>
    </div>

    <div v-if="brief" class="modal-back" @click.self="brief = null">
      <div class="modal">
        <h3 style="margin:0 0 12px">Weekly brief</h3>
        <pre>{{ brief }}</pre>
        <button class="btn primary" type="button" style="margin-top:14px" @click="brief = null">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, exportAccounting } from '@/api/client'

const route = useRoute()
const title = computed(() => String(route.meta.title || 'Command Center'))
const dataset = ref('scale')
const brief = ref<string | null>(null)

const datasetLabel = computed(() =>
  dataset.value === 'pre_revenue' ? 'Pre-revenue · manual ledger' : 'Demo @ 1.000 orgs · ETL −4m',
)

const sections = [
  {
    label: 'Business',
    items: [
      { to: '/', ico: '01', label: 'Command Center' },
      { to: '/revenue', ico: '02', label: 'Revenue' },
      { to: '/customers', ico: '03', label: 'Customers' },
      { to: '/pipeline', ico: '04', label: 'Pipeline' },
    ],
  },
  {
    label: 'Product & Ops',
    items: [
      { to: '/usage', ico: '05', label: 'Product Usage' },
      { to: '/economics', ico: '06', label: 'Unit Economics' },
      { to: '/retention', ico: '07', label: 'Retention' },
      { to: '/support', ico: '08', label: 'Support / VoC' },
      { to: '/ops', ico: '09', label: 'Platform Ops' },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/goals', ico: '10', label: 'Goals & Alerts' },
      { to: '/settings', ico: '11', label: 'Settings' },
    ],
  },
]

onMounted(async () => {
  try {
    const o = await api<{ dataset: string }>('/overview')
    dataset.value = o.dataset
  } catch {
    dataset.value = 'offline'
  }
})

function isOn(to: string): boolean {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(`${to}/`)
}

async function exportCsv() {
  try {
    await exportAccounting()
  } catch {
    brief.value = 'Export CSV falló — ¿JWT configurado?'
  }
}

async function runBrief() {
  try {
    const r = await api<{ brief: string[] }>('/reports/weekly/run', { method: 'POST' })
    brief.value = r.brief.map((l) => `• ${l}`).join('\n')
  } catch {
    brief.value = 'API offline. Arranca `make api` en el puerto 8081.'
  }
}
</script>
