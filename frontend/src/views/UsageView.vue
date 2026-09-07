<template>
  <div v-if="!u" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Product Usage</h1>
        <p class="lede">Leading indicators de retención: si no escanean ni abren reportes, el MRR es frágil.</p>
      </div>
    </div>
    <div class="grid g-4">
      <div class="card"><h3>Scans / 7d</h3><div class="kpi">{{ num(u.scans_7d) }}</div></div>
      <div class="card"><h3>High/Crit delivered</h3><div class="kpi">{{ num(u.findings_hc_7d) }}</div></div>
      <div class="card"><h3>WAU orgs</h3><div class="kpi">{{ num(u.wau_orgs) }}</div></div>
      <div class="card"><h3>Reports PDF</h3><div class="kpi">{{ num(u.reports_30d) }}</div></div>
    </div>
    <div class="grid g-2b" style="margin-top:14px">
      <div class="card">
        <h3>By engine (7d)</h3>
        <div class="list-row"><span>Pentest / Raptor</span><b>{{ num(u.by_engine.pentest) }}</b></div>
        <div class="list-row"><span>Arsenal</span><b>{{ num(u.by_engine.arsenal) }}</b></div>
        <div class="list-row"><span>ASM</span><b>{{ num(u.by_engine.asm) }}</b></div>
        <div class="list-row"><span>Sense check-ins</span><b>{{ num(u.by_engine.sense) }}</b></div>
      </div>
      <div class="card">
        <h3>Pilot funnel</h3>
        <div class="list-row"><span>Signup</span><b>{{ u.funnel.signup }}</b></div>
        <div class="list-row"><span>First scan</span><b>{{ u.funnel.first_scan }}</b></div>
        <div class="list-row"><span>First High finding</span><b>{{ u.funnel.first_high }}</b></div>
        <div class="list-row"><span>Converted</span><b>{{ u.funnel.converted }} · {{ u.funnel.signup ? Math.round((u.funnel.converted / u.funnel.signup) * 100) : 0 }}%</b></div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Feature adoption</h3>
      <div v-for="(v, k) in u.adoption" :key="k" class="list-row">
        <span>{{ k }}</span>
        <b>{{ pct(Number(v), 0) }}</b>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { num, pct } from '@/lib/format'

const u = ref<{
  scans_7d: number
  findings_hc_7d: number
  wau_orgs: number
  reports_30d: number
  by_engine: Record<string, number>
  funnel: { signup: number; first_scan: number; first_high: number; converted: number }
  adoption: Record<string, number>
} | null>(null)

onMounted(async () => {
  u.value = await api('/usage/summary')
})
</script>
