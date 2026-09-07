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

    <form class="filters" style="margin-bottom:14px" @submit.prevent="createDeal">
      <input v-model="newName" placeholder="Nuevo deal…" style="flex:1;min-width:180px" required />
      <input v-model.number="newAcv" type="number" min="0" step="1000" placeholder="ACV USD" style="width:120px" />
      <select v-model="newSource">
        <option value="inbound">Inbound</option>
        <option value="outbound">Outbound</option>
        <option value="referral">Referral</option>
        <option value="direct">Direct</option>
        <option value="mssp">MSSP</option>
      </select>
      <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '…' : 'Añadir deal' }}</button>
    </form>
    <p v-if="error" class="lede" style="color:var(--crit);margin-bottom:10px">{{ error }}</p>

    <div class="kanban">
      <div v-for="col in columns" :key="col.id" class="col">
        <h4>{{ col.label }}<span>{{ col.deals.length }}</span></h4>
        <div v-for="d in col.deals" :key="d.id" class="deal">
          <b>{{ d.name }}</b>
          <span>{{ money(d.acv_usd) }} · {{ d.probability }}% · {{ d.source }}</span>
          <div class="deal-actions">
            <button
              v-if="prevStage(col.id)"
              class="btn"
              type="button"
              title="Mover atrás"
              @click="moveDeal(d.id, prevStage(col.id)!)"
            >
              ←
            </button>
            <button
              v-if="nextStage(col.id)"
              class="btn primary"
              type="button"
              title="Mover adelante"
              @click="moveDeal(d.id, nextStage(col.id)!)"
            >
              →
            </button>
            <button
              v-if="col.id !== 'lost'"
              class="btn"
              type="button"
              title="Marcar lost"
              @click="moveDeal(d.id, 'lost')"
            >
              Lost
            </button>
          </div>
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

const ORDER = STAGES.map((s) => s.id)

const data = ref<{ items: Deal[]; pipeline: number; weighted: number; coverage: number; win_rate: number } | null>(null)
const newName = ref('')
const newAcv = ref(10000)
const newSource = ref('inbound')
const saving = ref(false)
const error = ref('')

const columns = computed(() =>
  STAGES.map((s) => ({
    ...s,
    deals: (data.value?.items || []).filter((d) => d.stage === s.id),
  })),
)

function nextStage(stage: string): string | null {
  const i = ORDER.indexOf(stage)
  return i >= 0 && i < ORDER.length - 1 ? ORDER[i + 1] : null
}

function prevStage(stage: string): string | null {
  const i = ORDER.indexOf(stage)
  return i > 0 ? ORDER[i - 1] : null
}

async function load() {
  data.value = await api('/pipeline/deals')
}

async function createDeal() {
  saving.value = true
  error.value = ''
  try {
    await api('/pipeline/deals', {
      method: 'POST',
      body: JSON.stringify({
        name: newName.value.trim(),
        acv_usd: newAcv.value || 0,
        source: newSource.value,
        stage: 'lead',
      }),
    })
    newName.value = ''
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Error al crear deal'
  } finally {
    saving.value = false
  }
}

async function moveDeal(id: number, stage: string) {
  error.value = ''
  try {
    await api(`/pipeline/deals/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ stage }),
    })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Error al mover deal'
  }
}

onMounted(load)
</script>

<style scoped>
.deal-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.deal-actions .btn {
  padding: 4px 8px;
  font-size: 0.72rem;
}
</style>
