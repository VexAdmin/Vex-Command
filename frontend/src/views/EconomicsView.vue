<template>
  <div v-if="!e" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Unit Economics</h1>
        <p class="lede">Sin coste Gemini por scan no hay pricing defendible. Este módulo exige instrumentar PRICE-00 en Vex Raptor.</p>
      </div>
    </div>
    <div class="grid g-4">
      <div class="card"><h3>COGS Gemini</h3><div class="kpi kpi-sm">{{ money(e.gemini) }}</div><div class="kpi-sub">{{ pct(e.gemini_share, 0) }} rev</div></div>
      <div class="card"><h3>Infra alloc</h3><div class="kpi kpi-sm">{{ money(e.infra) }}</div><div class="kpi-sub">{{ pct(e.infra_share, 0) }} rev</div></div>
      <div class="card"><h3>Gross margin</h3><div class="kpi kpi-sm">{{ pct(e.gross_margin, 0) }}</div></div>
      <div class="card"><h3>Orgs COGS &gt; 40%</h3><div class="kpi kpi-sm">{{ e.thin_margin_orgs }}</div><div class="kpi-sub delta down">revisar Deep scans</div></div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Cost per scan by profile</h3>
      <table>
        <thead><tr><th>Profile</th><th>Avg tokens $</th><th>Infra $</th><th>Total</th><th>vs plan floor</th></tr></thead>
        <tbody>
          <tr v-for="r in e.per_scan" :key="r.profile">
            <td>{{ r.profile }}</td>
            <td class="mono">{{ money(r.tokens, 2) }}</td>
            <td class="mono">{{ money(r.infra, 2) }}</td>
            <td class="mono">{{ money(r.total, 2) }}</td>
            <td><span class="tag" :class="r.flag === 'ok' ? 'good' : 'warn'">{{ r.flag }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'

const e = ref<{
  gemini: number
  infra: number
  gross_margin: number
  gemini_share: number
  infra_share: number
  thin_margin_orgs: number
  per_scan: { profile: string; tokens: number; infra: number; total: number; flag: string }[]
} | null>(null)

onMounted(async () => {
  e.value = await api('/economics/cogs')
})
</script>
