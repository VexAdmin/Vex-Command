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
        <h3>Authorized targets</h3>
        <p class="lede" style="margin-bottom:10px">URLs autorizadas para pentest (solo lectura).</p>
        <div v-if="data.authorized_targets.length" class="target-list">
          <div v-for="(t, i) in data.authorized_targets" :key="i" class="list-row">
            <span class="mono">{{ t }}</span>
          </div>
        </div>
        <div v-else class="empty">Sin restricción configurada (unrestricted).</div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Recent scans</h3>
      <p class="lede" style="margin-bottom:10px">Últimos 25 scans — metadatos solamente.</p>
      <div v-if="data.recent_scans.length" class="scan-table">
        <div class="scan-head">
          <span>Target</span>
          <span>Status</span>
          <span>Findings</span>
          <span>Started</span>
        </div>
        <div v-for="s in data.recent_scans" :key="s.id" class="scan-row">
          <span class="mono scan-target">{{ s.target }}</span>
          <span><span class="tag" :class="scanStatusClass(s.status)">{{ s.status }}</span></span>
          <span>{{ s.finding_count }}</span>
          <span class="mono">{{ formatScanDate(s.started_at) }}</span>
        </div>
      </div>
      <div v-else class="empty">Sin scans registrados para esta cuenta.</div>
    </div>
    <div class="card" style="margin-top:14px">
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
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'
import type { Org } from '@/types'

interface RecentScan {
  id: string
  target: string
  status: string
  started_at: string
  finding_count: number
}

interface Account {
  org: Org
  notes: { body: string; actor_email: string }[]
  authorized_targets: string[]
  recent_scans: RecentScan[]
  usage_30d: { scans: number; findings_hc: number; reports: number }
  margin: { mrr: number; cogs: number; ratio: number }
  next_step: string
}

const route = useRoute()
const data = ref<Account | null>(null)
const note = ref('')

function formatScanDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

function scanStatusClass(status: string): string {
  if (status === 'completed') return 'good'
  if (status === 'running') return 'warn'
  if (status === 'error' || status === 'cancelled') return 'bad'
  return ''
}

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

<style scoped>
.scan-table {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.scan-head,
.scan-row {
  display: grid;
  grid-template-columns: 1fr 100px 80px 160px;
  gap: 12px;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border, rgba(255, 255, 255, 0.08));
}
.scan-head {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.65;
  border-bottom-width: 2px;
}
.scan-target {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.target-list .list-row {
  justify-content: flex-start;
}
</style>
