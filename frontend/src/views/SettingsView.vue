<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="!s" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Ajustes</h1>
        <p class="lede">Conexiones, moneda y acceso de operadores.</p>
      </div>
    </div>
    <div class="grid g-2b">
      <div class="card">
        <h3>Integraciones</h3>
        <div v-for="(v, k) in s.integrations" :key="k" class="list-row">
          <span>{{ k }}</span>
          <a v-if="String(v).startsWith('http')" :href="v" target="_blank" rel="noopener" class="tag good">
            abrir ↗
          </a>
          <span v-else class="tag" :class="integrationClass(String(v))">{{ integrationLabel(String(v)) }}</span>
        </div>
      </div>
      <div class="card">
        <h3>Acceso</h3>
        <div v-for="op in s.operators" :key="op.email" class="list-row">
          <span>{{ op.email }}</span><b>{{ op.role }}</b>
        </div>
        <div class="list-row"><span>MFA</span><span class="tag warn">{{ s.mfa }}</span></div>
        <div class="list-row"><span>Duración de sesión</span><b class="mono">{{ s.session_ttl }}</b></div>
        <div class="list-row"><span>IP allowlist</span><b>{{ s.ip_allowlist ? 'activa' : 'inactiva' }}</b></div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Entorno</h3>
      <div class="list-row"><span>Host consola</span><b class="mono">{{ s.host }}</b></div>
      <div class="list-row"><span>Prefijo API</span><b class="mono">{{ s.api_prefix }}</b></div>
      <div class="list-row"><span>Fuente de datos</span><b class="mono">{{ s.dataset }}</b></div>
      <div class="list-row"><span>Moneda · FY</span><b>{{ s.currency }} · {{ s.fy_start }}</b></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'

const s = ref<{
  host: string
  api_prefix: string
  currency: string
  fy_start: string
  session_ttl: string
  mfa: string
  ip_allowlist: boolean
  dataset: string
  integrations: Record<string, string>
  operators: { email: string; role: string }[]
} | null>(null)
const loadError = ref(false)

function integrationClass(v: string): string {
  if (v === 'connected') return 'good'
  if (v === 'manual_ledger') return 'warn'
  return 'warn'
}

function integrationLabel(v: string): string {
  if (v === 'manual_ledger') return 'ledger manual'
  if (v === 'connected') return 'conectado'
  return v
}

onMounted(async () => {
  loadError.value = false
  try {
    s.value = await api('/settings')
  } catch {
    loadError.value = true
  }
})
</script>
