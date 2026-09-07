<template>
  <div v-if="!data" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <RouterLink class="linkish" to="/customers">← Customers</RouterLink>
        <h1>{{ data.org.name }}</h1>
        <p class="lede">Account 360 — metadatos de cuenta y uso agregado. Nunca findings crudos.</p>
      </div>
      <span class="tag" :class="data.org.risk === 'ok' ? 'good' : data.org.risk === 'risk' ? 'bad' : 'warn'">{{ data.org.risk }}</span>
    </div>
    <div class="grid g-4">
      <div class="card"><h3>Plan</h3><div class="kpi kpi-sm">{{ data.org.plan }}</div></div>
      <div class="card"><h3>MRR</h3><div class="kpi kpi-sm">{{ money(data.org.mrr) }}</div></div>
      <div class="card"><h3>Health</h3><div class="kpi kpi-sm">{{ data.org.health }}</div></div>
      <div class="card"><h3>COGS / MRR</h3><div class="kpi kpi-sm">{{ pct(data.margin.ratio, 0) }}</div></div>
    </div>
    <div class="grid g-2b" style="margin-top:14px">
      <div class="card">
        <h3>Usage 30d</h3>
        <div class="list-row"><span>Scans</span><b>{{ data.usage_30d.scans }}</b></div>
        <div class="list-row"><span>High/Crit delivered</span><b>{{ data.usage_30d.findings_hc }}</b></div>
        <div class="list-row"><span>Reports</span><b>{{ data.usage_30d.reports }}</b></div>
        <div class="list-row"><span>Last active</span><b>{{ data.org.last_active_days }}d ago</b></div>
        <div class="list-row"><span>Region / channel</span><b>{{ data.org.region }} · {{ data.org.channel }}</b></div>
        <div class="list-row"><span>Seats</span><b>{{ data.org.seats }}</b></div>
      </div>
      <div class="card">
        <h3>Internal notes</h3>
        <p class="lede" style="margin-bottom:10px">Next step: {{ data.next_step }}</p>
        <form class="filters" @submit.prevent="saveNote">
          <input v-model="note" placeholder="Nota interna…" style="flex:1;min-width:180px" />
          <button class="btn primary" type="submit">Guardar</button>
        </form>
        <div v-for="(n, i) in data.notes" :key="i" class="list-row">
          <span>{{ n.body }}</span>
          <span class="mono">{{ n.actor_email }}</span>
        </div>
        <div v-if="!data.notes.length" class="empty">Sin notas todavía.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'
import type { Org } from '@/types'

interface Account {
  org: Org
  notes: { body: string; actor_email: string }[]
  usage_30d: { scans: number; findings_hc: number; reports: number }
  margin: { mrr: number; cogs: number; ratio: number }
  next_step: string
}

const route = useRoute()
const data = ref<Account | null>(null)
const note = ref('')

async function load() {
  data.value = await api<Account>(`/customers/${route.params.id}`)
}

async function saveNote() {
  if (!note.value.trim()) return
  await api(`/customers/${route.params.id}/notes`, {
    method: 'POST',
    body: JSON.stringify({ body: note.value }),
  })
  note.value = ''
  await load()
}

onMounted(load)
watch(() => route.params.id, load)
</script>
