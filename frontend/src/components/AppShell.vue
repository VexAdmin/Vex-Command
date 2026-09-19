<template>
  <div class="app">
    <aside class="side">
      <div class="brand">
        <img class="brand-logo" src="/vex-logo.svg" alt="" width="32" height="32" />
        <div class="brand-text">
          <p class="brand-title">
            <span class="brand-vex">VEX</span>
            <span class="brand-product">Command</span>
          </p>
          <p class="brand-sub">Operaciones de plataforma</p>
        </div>
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
            <span class="nav-index" aria-hidden="true">{{ item.ico }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </RouterLink>
        </template>
      </div>
      <div class="side-foot">
        Uso interno · ops.vexraptor.com
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <div class="crumb">
          <span class="crumb-root">VEX Command</span>
          <span class="crumb-sep" aria-hidden="true">/</span>
          <span class="crumb-page">{{ title }}</span>
        </div>
        <div class="top-actions">
          <span class="pill"><span class="dot" /> {{ datasetLabel }}</span>
          <button class="btn" type="button" @click="exportCsv">Exportar cuentas</button>
          <button class="btn" type="button" @click="signOut">Salir</button>
        </div>
      </header>
      <div class="content">
        <RouterView />
      </div>
    </div>

    <div v-if="toast" class="modal-back" @click.self="toast = null">
      <div class="modal">
        <pre>{{ toast }}</pre>
        <button class="btn primary" type="button" style="margin-top:14px" @click="toast = null">Cerrar</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, exportAccounting, logout } from '@/api/client'

const router = useRouter()

const route = useRoute()
const title = computed(() => String(route.meta.title || 'Hoy'))
const dataset = ref('scale')
const toast = ref<string | null>(null)

const datasetLabel = computed(() => {
  if (dataset.value === 'pre_revenue') return 'Pre-revenue · ledger manual'
  if (dataset.value === 'offline') return 'Sin conexión'
  if (dataset.value === 'scale') return 'Datos de demo'
  return dataset.value
})

const sections = [
  {
    label: 'Operaciones',
    items: [
      { to: '/', ico: '01', label: 'Hoy' },
      { to: '/customers', ico: '02', label: 'Cuentas' },
      { to: '/pipeline', ico: '03', label: 'Pipeline' },
      { to: '/revenue', ico: '04', label: 'Ingresos' },
      { to: '/ops', ico: '05', label: 'Plataforma' },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { to: '/goals', ico: '06', label: 'Metas' },
      { to: '/settings', ico: '07', label: 'Ajustes' },
      { to: '/activity', ico: '08', label: 'Actividad' },
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
    toast.value = 'No se pudo exportar.'
  }
}

async function signOut() {
  await logout()
  await router.push('/login')
}
</script>
