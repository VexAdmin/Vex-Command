<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="!o" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Plataforma</h1>
        <p class="lede">Señales operativas de VEX Raptor — no sustituye Grafana.</p>
      </div>
    </div>
    <div class="grid g-3">
      <div class="card">
        <h3>Estado Raptor</h3>
        <div class="kpi kpi-sm">{{ o.health }}</div>
        <div class="kpi-sub mono">{{ o.version }}</div>
      </div>
      <div class="card">
        <h3>Scans en curso</h3>
        <div class="kpi">{{ o.arq_depth }}</div>
      </div>
      <div class="card">
        <h3>Huérfanos (&gt;2 h)</h3>
        <div class="kpi">{{ o.orphaned_running }}</div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Señales en vivo</h3>
      <div class="list-row"><span>Alembic head</span><b class="mono">{{ o.alembic_head }}</b></div>
      <div class="list-row">
        <span>Playwright Chromium</span>
        <b class="tag" :class="signalClass(o.playwright)">{{ o.playwright }}</b>
      </div>
      <div class="list-row">
        <span>Interactsh</span>
        <b class="tag" :class="signalClass(o.interactsh)">{{ o.interactsh }}</b>
      </div>
      <div class="list-row">
        <span>Gemini 24h</span>
        <b class="mono">{{ o.gemini_24h ? money(o.gemini_24h) : 'Sin dato' }}</b>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money } from '@/lib/format'

const o = ref<{
  health: string
  version: string
  arq_depth: number
  orphaned_running: number
  alembic_head: string
  playwright: string
  interactsh: string
  gemini_24h: number
} | null>(null)
const loadError = ref(false)

function signalClass(value: string): string {
  if (value === '—' || !value) return ''
  if (value === 'ok' || value === 'OK') return 'good'
  return 'warn'
}

onMounted(async () => {
  loadError.value = false
  try {
    o.value = await api('/ops/platform')
  } catch {
    loadError.value = true
  }
})
</script>
