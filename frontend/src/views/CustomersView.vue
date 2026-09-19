<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="loading && !items.length" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Cuentas</h1>
        <p class="lede">Cuentas en VEX Raptor: plan, MRR, salud y riesgo — sin findings del tenant.</p>
      </div>
    </div>
    <div class="view-chips" role="group" aria-label="Vistas rápidas">
      <button
        v-for="p in presets"
        :key="p.key"
        type="button"
        class="chip-btn"
        :class="{ active: activePreset === p.key }"
        @click="applyPreset(p.key)"
      >
        {{ p.label }}
      </button>
    </div>
    <div class="filters">
      <input v-model="q" placeholder="Buscar org…" style="min-width:220px" @keyup.enter="load(0)" />
      <select v-model="plan" @change="load(0)">
        <option value="">Todos los planes</option>
        <option>Essential</option>
        <option>Professional</option>
        <option>Enterprise</option>
        <option>MSSP</option>
      </select>
      <select v-model="risk" @change="load(0)">
        <option value="">Toda la salud</option>
        <option value="risk">Solo riesgo</option>
        <option value="watch">Vigilar</option>
        <option value="ok">OK</option>
      </select>
      <select v-model="pilotStage" @change="onPilotStageChange">
        <option value="">Todas las etapas</option>
        <option value="discovery">Discovery</option>
        <option value="pilot">Piloto</option>
        <option value="production">Producción</option>
        <option value="paused">Pausado</option>
      </select>
      <select v-model="sort" @change="load(0)">
        <option value="mrr">Orden: MRR ↓</option>
        <option value="health">Salud ↑</option>
        <option value="last_active">Última actividad</option>
      </select>
      <button class="btn" type="button" @click="applyFilters">Filtrar</button>
    </div>
    <p v-if="activePresetLabel" class="filter-hint">Vista: <b>{{ activePresetLabel }}</b> · {{ total }} cuenta(s)</p>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Organización</th><th>Plan</th><th>MRR</th><th>Salud</th><th>Riesgo</th><th>Última actividad</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in items" :key="o.id">
            <td><RouterLink class="linkish" :to="`/customers/${o.id}`"><b>{{ o.name }}</b></RouterLink></td>
            <td><span class="tag">{{ o.plan }}</span></td>
            <td class="mono">{{ money(o.mrr) }}</td>
            <td>
              <div class="progress" style="width:90px;display:inline-block;vertical-align:middle">
                <i :style="{ width: o.health + '%', background: healthColor(o.health) }" />
              </div>
              <span class="mono"> {{ o.health }}</span>
            </td>
            <td><span class="tag" :class="o.risk === 'ok' ? 'good' : o.risk === 'risk' ? 'bad' : 'warn'">{{ o.risk }}</span></td>
            <td class="mono">{{ o.last_active_days }}d</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!items.length && !loading" class="empty">No hay cuentas con estos filtros.</div>
      <div v-if="loading" class="empty">Cargando…</div>
      <div class="pager">
        Mostrando {{ items.length }} de {{ total }}
        <button class="btn" type="button" :disabled="cursor === 0" @click="load(Math.max(0, cursor - 25))">Anterior</button>
        <button class="btn" type="button" :disabled="!next" @click="load(next || 0)">Siguiente</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { healthColor, money } from '@/lib/format'
import type { Org } from '@/types'

const presets = [
  { key: '', label: 'Todas' },
  { key: 'inactive_14d', label: 'Sin actividad 14d+' },
  { key: 'no_scans_30d', label: 'Sin scans 30d' },
  { key: 'empty_allowlist', label: 'Allowlist vacía' },
  { key: 'risk', label: 'En riesgo' },
] as const

type PresetKey = (typeof presets)[number]['key']

const route = useRoute()
const router = useRouter()

const q = ref('')
const plan = ref('')
const risk = ref('')
const view = ref('')
const pilotStage = ref('')
const sort = ref('mrr')
const items = ref<Org[]>([])
const total = ref(0)
const cursor = ref(0)
const next = ref<number | null>(null)
const loading = ref(false)
const loadError = ref(false)

const activePreset = computed((): PresetKey => {
  if (view.value) return view.value as PresetKey
  if (risk.value === 'risk' && !pilotStage.value) return 'risk'
  return ''
})

const activePresetLabel = computed(() => {
  const p = presets.find((x) => x.key === activePreset.value)
  return p && p.key ? p.label : pilotStage.value ? `Etapa: ${pilotStage.value}` : ''
})

function syncFromRoute() {
  const query = route.query
  q.value = typeof query.q === 'string' ? query.q : ''
  plan.value = typeof query.plan === 'string' ? query.plan : ''
  risk.value = typeof query.risk === 'string' ? query.risk : ''
  view.value = typeof query.view === 'string' ? query.view : ''
  pilotStage.value = typeof query.pilot_stage === 'string' ? query.pilot_stage : ''
  sort.value = typeof query.sort === 'string' ? query.sort : 'mrr'
}

function pushQuery() {
  const query: Record<string, string> = {}
  if (q.value) query.q = q.value
  if (plan.value) query.plan = plan.value
  if (risk.value) query.risk = risk.value
  if (view.value) query.view = view.value
  if (pilotStage.value) query.pilot_stage = pilotStage.value
  if (sort.value && sort.value !== 'mrr') query.sort = sort.value
  router.replace({ query })
}

function applyPreset(key: PresetKey) {
  view.value = ''
  risk.value = ''
  if (key === 'risk') {
    risk.value = 'risk'
  } else if (key) {
    view.value = key
    if (key === 'inactive_14d' && sort.value === 'mrr') sort.value = 'last_active'
  }
  load(0)
  pushQuery()
}

function onPilotStageChange() {
  view.value = ''
  applyFilters()
}

function applyFilters() {
  load(0)
  pushQuery()
}

async function load(c = 0) {
  loading.value = true
  loadError.value = false
  cursor.value = c
  try {
    const params = new URLSearchParams({
      q: q.value,
      plan: plan.value,
      risk: risk.value,
      sort: sort.value,
      cursor: String(c),
      limit: '25',
    })
    if (view.value) params.set('view', view.value)
    if (pilotStage.value) params.set('pilot_stage', pilotStage.value)
    const r = await api<{ total: number; next_cursor: number | null; items: Org[] }>(`/customers?${params}`)
    items.value = r.items
    total.value = r.total
    next.value = r.next_cursor
  } catch {
    loadError.value = true
    items.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query,
  () => {
    syncFromRoute()
    load(0)
  },
  { immediate: true },
)
</script>
