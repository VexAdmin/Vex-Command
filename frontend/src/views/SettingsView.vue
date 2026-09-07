<template>
  <div v-if="!s" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Settings</h1>
        <p class="lede">Conexiones, moneda, acceso. MFA obligatorio para operators. Nunca visible en el nav del tenant.</p>
      </div>
    </div>
    <div class="grid g-2b">
      <div class="card">
        <h3>Integrations</h3>
        <div v-for="(v, k) in s.integrations" :key="k" class="list-row">
          <span>{{ k }}</span>
          <span class="tag" :class="v === 'connected' ? 'good' : 'warn'">{{ v }}</span>
        </div>
      </div>
      <div class="card">
        <h3>Access</h3>
        <div v-for="op in s.operators" :key="op.email" class="list-row">
          <span>{{ op.email }}</span><b>{{ op.role }}</b>
        </div>
        <div class="list-row"><span>MFA</span><span class="tag good">{{ s.mfa }}</span></div>
        <div class="list-row"><span>Session TTL</span><b class="mono">{{ s.session_ttl }}</b></div>
        <div class="list-row"><span>IP allowlist</span><b>{{ s.ip_allowlist ? 'on' : 'off' }}</b></div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Environment</h3>
      <div class="list-row"><span>Console host</span><b class="mono">{{ s.host }}</b></div>
      <div class="list-row"><span>API prefix</span><b class="mono">{{ s.api_prefix }}</b></div>
      <div class="list-row"><span>Dataset</span><b class="mono">{{ s.dataset }}</b></div>
      <div class="list-row"><span>Currency / FY</span><b>{{ s.currency }} · {{ s.fy_start }}</b></div>
    </div>
    <div class="banner" style="margin-top:14px">
      Hoy no hay clientes pagando. El dataset <code>scale</code> es la plantilla a 1.000 orgs.
      Para el modo honesto: <code>FOUNDER_DATASET=pre_revenue</code> en <code>.env</code> y reinicia la API.
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

onMounted(async () => {
  s.value = await api('/settings')
})
</script>
