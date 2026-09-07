<template>
  <div>
    <div class="hero-row">
      <div>
        <h1>Customers</h1>
        <p class="lede">Account 360° a escala 1.000: plan, MRR, health y riesgo — sin findings del tenant.</p>
      </div>
    </div>
    <div class="filters">
      <input v-model="q" placeholder="Buscar org…" style="min-width:220px" @keyup.enter="load(0)" />
      <select v-model="plan" @change="load(0)">
        <option value="">All plans</option>
        <option>Essential</option>
        <option>Professional</option>
        <option>Enterprise</option>
        <option>MSSP</option>
      </select>
      <select v-model="risk" @change="load(0)">
        <option value="">All health</option>
        <option value="risk">Risk only</option>
        <option value="watch">Watch</option>
        <option value="ok">OK</option>
      </select>
      <select v-model="sort" @change="load(0)">
        <option value="mrr">Sort: MRR ↓</option>
        <option value="health">Health ↑</option>
        <option value="last_active">Last active</option>
      </select>
      <button class="btn" type="button" @click="load(0)">Filtrar</button>
    </div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Organization</th><th>Plan</th><th>MRR</th><th>Health</th><th>Risk</th><th>Last active</th>
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
            <td class="mono">{{ o.last_active_days }}d ago</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!items.length" class="empty">No hay orgs en este dataset.</div>
      <div class="pager">
        Mostrando {{ items.length }} de {{ total }}
        <button class="btn" type="button" :disabled="cursor === 0" @click="load(Math.max(0, cursor - 25))">Prev</button>
        <button class="btn" type="button" :disabled="!next" @click="load(next || 0)">Next</button>
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

async function load(c = 0) {
  cursor.value = c
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
}

onMounted(() => load(0))
</script>
