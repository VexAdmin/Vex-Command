<template>
  <div>
    <div class="hero-row">
      <div>
        <h1>Cuentas</h1>
        <p class="lede">Cuentas en VEX Raptor: plan, MRR, salud y riesgo — sin findings del tenant.</p>
      </div>
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
      <select v-model="sort" @change="load(0)">
        <option value="mrr">Orden: MRR ↓</option>
        <option value="health">Salud ↑</option>
        <option value="last_active">Última actividad</option>
      </select>
      <button class="btn" type="button" @click="load(0)">Filtrar</button>
    </div>
    <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
    <div v-else class="card">
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
      <div v-if="!items.length && !loading" class="empty">No hay cuentas.</div>
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
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { healthColor, money } from '@/lib/format'
import type { Org } from '@/types'

const q = ref('')
const plan = ref('')
const risk = ref('')
const sort = ref('mrr')
const items = ref<Org[]>([])
const total = ref(0)
const cursor = ref(0)
const next = ref<number | null>(null)
const loading = ref(false)
const loadError = ref(false)

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

onMounted(() => load(0))
</script>
