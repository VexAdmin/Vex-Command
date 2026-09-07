<template>
  <div v-if="!wf" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Revenue & Billing</h1>
        <p class="lede">Waterfall, cohorts y facturación. Stripe es la fuente de verdad; los deals offline viven en ajustes manuales.</p>
      </div>
    </div>
    <div class="grid g-4">
      <div class="card"><h3>New</h3><div class="kpi kpi-sm">{{ money(wf.new) }}</div></div>
      <div class="card"><h3>Expansion</h3><div class="kpi kpi-sm">{{ money(wf.expansion) }}</div></div>
      <div class="card"><h3>Contraction</h3><div class="kpi kpi-sm">{{ money(wf.contraction) }}</div></div>
      <div class="card"><h3>Churned MRR</h3><div class="kpi kpi-sm">{{ money(wf.churn) }}</div></div>
    </div>
    <div class="grid g-2" style="margin-top:14px">
      <div class="card">
        <h3>MRR waterfall (this month)</h3>
        <SparkBars :values="waterfallBars" />
        <div class="kpi-sub">Start → New → Expansion → Contraction → Churn → End</div>
      </div>
      <div>
        <div class="card">
          <h3>By plan</h3>
          <div v-for="(v, k) in wf.by_plan" :key="k" class="list-row"><span>{{ k }}</span><b>{{ money(v) }}</b></div>
        </div>
        <div class="card" style="margin-top:14px">
          <h3>Billing health</h3>
          <div class="list-row"><span>Open invoices</span><b>{{ wf.billing.open_invoices }}</b></div>
          <div class="list-row"><span>Past due</span><b class="delta down">{{ wf.billing.past_due }}</b></div>
          <div class="list-row"><span>Dunning active</span><b>{{ wf.billing.dunning }}</b></div>
          <div class="list-row"><span>Refunds 30d</span><b>{{ money(wf.billing.refunds_30d) }}</b></div>
        </div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Revenue retention cohorts</h3>
      <table>
        <thead><tr><th>Cohort</th><th>M0</th><th>M1</th><th>M2</th><th>M3</th><th>M6</th></tr></thead>
        <tbody>
          <tr v-for="c in cohorts" :key="c.cohort">
            <td>{{ c.cohort }}</td>
            <td>{{ cell(c.m0) }}</td>
            <td>{{ cell(c.m1) }}</td>
            <td>{{ cell(c.m2) }}</td>
            <td>{{ cell(c.m3) }}</td>
            <td>{{ cell(c.m6) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import SparkBars from '@/components/SparkBars.vue'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'

interface Waterfall {
  start: number
  new: number
  expansion: number
  contraction: number
  churn: number
  end: number
  by_plan: Record<string, number>
  billing: { open_invoices: number; past_due: number; dunning: number; refunds_30d: number }
}

const wf = ref<Waterfall | null>(null)
const cohorts = ref<{ cohort: string; m0: number; m1: number | null; m2: number | null; m3: number | null; m6: number | null }[]>([])
const waterfallBars = computed(() => {
  if (!wf.value) return []
  return [wf.value.start, wf.value.new, wf.value.expansion, -wf.value.contraction, -wf.value.churn, wf.value.end].map((v) => v / 1000)
})

function cell(v: number | null) {
  return v == null ? '—' : pct(v, 0)
}

onMounted(async () => {
  wf.value = await api<Waterfall>('/revenue/waterfall')
  const r = await api<{ cohorts: typeof cohorts.value }>('/revenue/cohorts')
  cohorts.value = r.cohorts
})
</script>
