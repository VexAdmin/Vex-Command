<template>
  <div v-if="!g" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Goals & Alerts</h1>
        <p class="lede">OKRs trimestrales, KPIs semanales y reglas que te pegan en Slack.</p>
      </div>
    </div>
    <p v-if="error" class="lede" style="color:var(--crit);margin-bottom:10px">{{ error }}</p>
    <div class="grid g-2b">
      <div class="card">
        <h3>{{ g.quarter }} OKRs</h3>
        <div v-for="o in g.okrs" :key="o.id" style="margin-bottom:12px">
          <div class="list-row"><span>{{ o.title }}</span><b>{{ fmt(o) }}</b></div>
          <div class="progress"><i :style="{ width: okrPct(o) + '%' }" /></div>
          <div class="filters" style="margin-top:8px;padding:0">
            <input
              v-model.number="drafts[o.id]"
              type="number"
              min="0"
              step="1"
              style="width:100px"
              :disabled="saving === o.id"
            />
            <button
              class="btn primary"
              type="button"
              :disabled="saving === o.id"
              @click="saveOkr(o, drafts[o.id])"
            >
              {{ saving === o.id ? '…' : 'Guardar' }}
            </button>
          </div>
        </div>
        <div v-if="g.net_new" style="margin-top:16px;padding-top:12px;border-top:1px solid var(--line)">
          <h4 style="margin:0 0 8px;font-size:0.8rem;text-transform:uppercase;color:var(--muted)">
            Net new MRR goal
          </h4>
          <div class="list-row">
            <span>Target</span>
            <b>{{ money(g.net_new.current) }} / {{ money(g.net_new.target) }}</b>
          </div>
          <div class="filters" style="margin-top:8px;padding:0">
            <input
              v-model.number="netNewDraft"
              type="number"
              min="0"
              step="1000"
              style="width:120px"
              :disabled="savingNetNew"
            />
            <button class="btn primary" type="button" :disabled="savingNetNew" @click="saveNetNew">
              {{ savingNetNew ? '…' : 'Guardar' }}
            </button>
          </div>
        </div>
      </div>
      <div class="card">
        <h3>Alert rules</h3>
        <div v-for="r in g.rules" :key="r.name" class="list-row">
          <span>{{ r.name }}</span>
          <span class="tag" :class="r.enabled ? 'good' : 'warn'">{{ r.enabled ? 'on' : 'off' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'

interface Okr {
  id: number
  title: string
  current: number | null
  target: number
  unit: string
}

interface GoalsPayload {
  quarter: string
  okrs: Okr[]
  net_new?: { current: number; target: number }
  rules: { name: string; enabled: boolean }[]
}

const g = ref<GoalsPayload | null>(null)
const drafts = ref<Record<number, number>>({})
const netNewDraft = ref(25000)
const saving = ref<number | null>(null)
const savingNetNew = ref(false)
const error = ref('')

function fmt(o: Okr) {
  const cur = o.current ?? 0
  if (o.unit === 'usd') return `${money(cur)} / ${money(o.target)}`
  if (o.unit === 'ratio') return `${pct(cur, 0)} / ${pct(o.target, 0)}`
  return `${cur} / ${o.target}`
}

function okrPct(o: Okr) {
  if (!o.target) return 0
  return Math.min(100, Math.round(((o.current ?? 0) / o.target) * 100))
}

function syncDrafts(data: GoalsPayload) {
  drafts.value = Object.fromEntries(data.okrs.map((o) => [o.id, o.target]))
  if (data.net_new) netNewDraft.value = data.net_new.target
}

async function load() {
  g.value = await api<GoalsPayload>('/goals')
  if (g.value) syncDrafts(g.value)
}

async function saveOkr(o: Okr, newTarget: number) {
  saving.value = o.id
  error.value = ''
  try {
    await api('/goals', {
      method: 'PUT',
      body: JSON.stringify({ kind: 'okr', id: o.id, target: newTarget }),
    })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Error al guardar goal'
  } finally {
    saving.value = null
  }
}

async function saveNetNew() {
  savingNetNew.value = true
  error.value = ''
  try {
    await api('/goals', {
      method: 'PUT',
      body: JSON.stringify({ kind: 'net_new', target: netNewDraft.value }),
    })
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Error al guardar net new'
  } finally {
    savingNetNew.value = false
  }
}

watch(g, (data) => {
  if (data) syncDrafts(data)
})

onMounted(load)
</script>
