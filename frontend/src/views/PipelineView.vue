<template>
  <div v-if="!data" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Pipeline & GTM</h1>
        <p class="lede">CRM ligero opinionated para un founder: deals, stages, win/loss — no Salesforce.</p>
      </div>
    </div>
    <div class="grid g-4" style="margin-bottom:14px">
      <div class="card"><h3>Pipeline $</h3><div class="kpi kpi-sm">{{ money(data.pipeline) }}</div></div>
      <div class="card"><h3>Weighted</h3><div class="kpi kpi-sm">{{ money(data.weighted) }}</div></div>
      <div class="card"><h3>Coverage</h3><div class="kpi kpi-sm">{{ data.coverage.toFixed(1) }}×</div></div>
      <div class="card"><h3>Win rate</h3><div class="kpi kpi-sm">{{ pct(data.win_rate, 0) }}</div></div>
    </div>
    <div class="kanban">
      <div v-for="col in columns" :key="col.id" class="col">
        <h4>{{ col.label }}<span>{{ col.deals.length }}</span></h4>
        <div v-for="d in col.deals" :key="d.id" class="deal">
          <b>{{ d.name }}</b>
          <span>{{ money(d.acv_usd) }} · {{ d.probability }}% · {{ d.source }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'
import type { Deal } from '@/types'

const STAGES = [
  { id: 'lead', label: 'Lead' },
  { id: 'qualified', label: 'Qualified' },
  { id: 'pilot', label: 'Pilot' },
  { id: 'negotiation', label: 'Negotiation' },
  { id: 'won', label: 'Closed Won' },
]

const data = ref<{ items: Deal[]; pipeline: number; weighted: number; coverage: number; win_rate: number } | null>(null)
const columns = computed(() =>
  STAGES.map((s) => ({
    ...s,
    deals: (data.value?.items || []).filter((d) => d.stage === s.id),
  })),
)

onMounted(async () => {
  data.value = await api('/pipeline/deals')
})
</script>
