<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="!o" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Plataforma</h1>
        <p class="lede">Señales operativas de VEX Raptor — no sustituye Grafana.</p>
        <p class="lede" style="margin-top:6px;color:var(--muted);font-size:0.85rem">
          VEX Command no invoca IA. El análisis con LLM vive en Raptor Deep (BYOK del cliente).
        </p>
      </div>
    </div>
    <div class="grid g-4">
      <div class="card">
        <h3>VEX Command</h3>
        <div class="kpi kpi-sm">{{ o.command_env || '—' }}</div>
        <div class="kpi-sub mono">v{{ o.command_version || '—' }}</div>
        <div v-if="o.command_deploy_label" class="kpi-sub mono" style="margin-top:6px">
          deploy {{ o.command_deploy_label }}
        </div>
      </div>
      <div class="card">
        <h3>Estado Raptor</h3>
        <div class="kpi kpi-sm">{{ o.health }}</div>
        <div class="kpi-sub mono">{{ o.version }}</div>
      </div>
      <div class="card">
        <h3>Scans en curso</h3>
        <div class="kpi">{{ o.arq_depth }}</div>
        <div class="kpi-sub">{{ o.scans_7d }} scans en 7d</div>
      </div>
      <div class="card">
        <h3>Huérfanos (&gt;2 h)</h3>
        <div class="kpi">{{ o.orphaned_running }}</div>
        <div class="kpi-sub">{{ o.findings_hc_7d }} findings HC (7d)</div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Uso agregado (SQL)</h3>
      <div class="list-row"><span>Orgs activas (7d)</span><b class="mono">{{ o.wau_orgs }}</b></div>
      <div class="list-row"><span>Scans plataforma (30d)</span><b class="mono">{{ o.platform_scans_30d }}</b></div>
      <div class="list-row"><span>Alembic head (Raptor DB)</span><b class="mono">{{ o.alembic_head }}</b></div>
    </div>
    <div v-if="hasRaptorTelemetry" class="card" style="margin-top:14px">
      <h3>Telemetría Raptor</h3>
      <div v-if="o.uptime_30d != null" class="list-row">
        <span>Uptime 30d</span>
        <b class="mono">{{ fmtUptime(o.uptime_30d) }}</b>
      </div>
      <div v-if="o.errors_5xx_24h != null" class="list-row">
        <span>Errores 5xx (24h)</span>
        <b class="mono">{{ fmtCount(o.errors_5xx_24h) }}</b>
      </div>
      <div v-if="o.playwright" class="list-row">
        <span>Playwright Chromium</span>
        <b class="tag" :class="signalClass(o.playwright)">{{ fmtSignal(o.playwright) }}</b>
      </div>
      <div v-if="o.interactsh" class="list-row">
        <span>Interactsh</span>
        <b class="tag" :class="signalClass(o.interactsh)">{{ fmtSignal(o.interactsh) }}</b>
      </div>
      <div v-if="o.gemini_24h != null" class="list-row">
        <span>Gemini 24h</span>
        <b class="mono">{{ fmtMoney(o.gemini_24h) }}</b>
      </div>
    </div>
    <p v-else class="ops-telemetry-note">{{ o.telemetry_note }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'

interface OpsPayload {
  command_version: string | null
  command_deploy_label: string | null
  command_env: string | null
  health: string
  version: string
  arq_depth: number
  orphaned_running: number
  scans_7d: number
  findings_hc_7d: number
  wau_orgs: number
  platform_scans_30d: number
  uptime_30d: number | null
  errors_5xx_24h: number | null
  alembic_head: string
  playwright: string | null
  interactsh: string | null
  gemini_24h: number | null
  telemetry_note?: string
}

const o = ref<OpsPayload | null>(null)
const loadError = ref(false)

const hasRaptorTelemetry = computed(() => {
  if (!o.value) return false
  return (
    o.value.uptime_30d != null
    || o.value.errors_5xx_24h != null
    || !!o.value.playwright
    || !!o.value.interactsh
    || o.value.gemini_24h != null
  )
})

function isMissing(value: string | number | null | undefined): boolean {
  return value === null || value === undefined || value === '' || value === '—'
}

function fmtSignal(value: string | null | undefined): string {
  return isMissing(value) ? 'Sin dato' : String(value)
}

function fmtMoney(value: number | null | undefined): string {
  return isMissing(value) ? 'Sin dato' : money(value as number)
}

function fmtCount(value: number | null | undefined): string {
  return isMissing(value) ? 'Sin dato' : String(value)
}

function fmtUptime(value: number | null | undefined): string {
  if (isMissing(value)) return 'Sin dato'
  return pct(value as number, 1)
}

function signalClass(value: string | null | undefined): string {
  if (isMissing(value)) return ''
  if (value === 'ok' || value === 'OK') return 'good'
  return 'warn'
}

onMounted(async () => {
  loadError.value = false
  try {
    o.value = await api<OpsPayload>('/ops/platform')
  } catch {
    loadError.value = true
  }
})
</script>

<style scoped>
.ops-telemetry-note {
  margin-top: 14px;
  font-size: 0.85rem;
  color: var(--muted);
  line-height: 1.45;
  max-width: 52rem;
}
</style>
