<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="loading" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Ingresos (ledger)</h1>
        <p class="lede">Hasta Stripe, la fuente de verdad es el ledger manual. Waterfall y cohorts llegarán con facturación automática.</p>
      </div>
    </div>
    <div class="card">
      <h3>Ledger manual</h3>
      <div v-if="!manual.length" class="empty">Sin entradas en el ledger.</div>
      <div v-for="e in manual" :key="e.id" class="list-row">
        <span>{{ e.period_month }} · {{ e.channel }} · {{ e.reason }}</span>
        <b>{{ money(e.mrr_usd) }}</b>
      </div>
      <div class="filters" style="margin-top:10px;padding:0">
        <input v-model="form.period_month" type="month" />
        <input v-model.number="form.mrr_usd" type="number" placeholder="MRR neto USD" />
        <select v-model="form.channel">
          <option value="direct">direct</option>
          <option value="partner">partner</option>
        </select>
        <input v-model="form.reason" type="text" placeholder="Motivo (ej: Tyndall — Cliente X — neto post 50/50)" style="min-width:260px" />
        <button class="btn primary" type="button" :disabled="saving" @click="addManual">
          {{ saving ? '…' : 'Agregar' }}
        </button>
      </div>
      <p v-if="error" class="lede" style="color:var(--crit)">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money } from '@/lib/format'

interface ManualEntry {
  id: number
  org_id: number | null
  period_month: string
  mrr_usd: number
  channel: string
  reason: string
  actor_email: string
}

const manual = ref<ManualEntry[]>([])
const form = ref({ period_month: '', mrr_usd: 0, channel: 'direct', reason: '' })
const saving = ref(false)
const error = ref('')
const loading = ref(true)
const loadError = ref(false)

async function loadManual() {
  const r = await api<{ items: ManualEntry[] }>('/revenue/manual')
  manual.value = r.items
}

async function addManual() {
  saving.value = true
  error.value = ''
  try {
    await api('/revenue/manual', {
      method: 'POST',
      body: JSON.stringify({ ...form.value, period_month: `${form.value.period_month}-01` }),
    })
    form.value = { period_month: '', mrr_usd: 0, channel: 'direct', reason: '' }
    await loadManual()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Error al guardar'
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  loading.value = true
  loadError.value = false
  try {
    await loadManual()
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})
</script>
