<template>
  <div v-if="!r" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Retention & Health</h1>
        <p class="lede">NRR, churn y lista de riesgo accionable. Health = recency 40% + payment 30% + usage 20% + support 10%.</p>
      </div>
    </div>
    <div class="grid g-3">
      <div class="card"><h3>Logo churn</h3><div class="kpi">{{ pct(r.logo_churn, 1) }}</div></div>
      <div class="card"><h3>Revenue churn</h3><div class="kpi">{{ pct(r.revenue_churn, 1) }}</div></div>
      <div class="card"><h3>NRR</h3><div class="kpi">{{ pct(r.nrr, 0) }}</div></div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Top churn risks</h3>
      <table>
        <thead><tr><th>Org</th><th>MRR</th><th>Health</th><th>Signal</th><th>Next step</th></tr></thead>
        <tbody>
          <tr v-for="o in r.risks" :key="o.id">
            <td><RouterLink class="linkish" :to="`/customers/${o.id}`">{{ o.name }}</RouterLink></td>
            <td class="mono">{{ money(o.mrr) }}</td>
            <td>{{ o.health }}</td>
            <td>{{ o.signal }}</td>
            <td>{{ o.next_step }}</td>
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
import type { Org } from '@/types'

const r = ref<{
  logo_churn: number
  revenue_churn: number
  nrr: number
  risks: (Org & { signal: string; next_step: string })[]
} | null>(null)

onMounted(async () => {
  r.value = await api('/retention/health')
})
</script>
