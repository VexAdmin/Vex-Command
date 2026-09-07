<template>
  <div v-if="!o" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Platform Ops</h1>
        <p class="lede">Puente a ingeniería: no reemplaza Grafana — resume lo que el founder necesita ver.</p>
      </div>
    </div>
    <div class="grid g-4">
      <div class="card"><h3>/health</h3><div class="kpi kpi-sm">{{ o.health }}</div><div class="kpi-sub mono">{{ o.version }}</div></div>
      <div class="card"><h3>ARQ depth</h3><div class="kpi">{{ o.arq_depth }}</div></div>
      <div class="card"><h3>Orphaned RUNNING</h3><div class="kpi">{{ o.orphaned_running }}</div></div>
      <div class="card"><h3>5xx rate 24h</h3><div class="kpi kpi-sm">{{ pct(o.errors_5xx_24h, 2) }}</div></div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Live signals</h3>
      <div class="list-row"><span>Alembic head</span><b class="mono">{{ o.alembic_head }}</b></div>
      <div class="list-row"><span>Playwright Chromium</span><b class="tag good">{{ o.playwright }}</b></div>
      <div class="list-row"><span>Interactsh</span><b class="tag warn">{{ o.interactsh }}</b></div>
      <div class="list-row"><span>Gemini spend 24h</span><b class="mono">{{ money(o.gemini_24h) }}</b></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'

const o = ref<{
  health: string
  version: string
  arq_depth: number
  orphaned_running: number
  errors_5xx_24h: number
  alembic_head: string
  playwright: string
  interactsh: string
  gemini_24h: number
} | null>(null)

onMounted(async () => {
  o.value = await api('/ops/platform')
})
</script>
