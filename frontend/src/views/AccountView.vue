<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="!data" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <RouterLink class="linkish" to="/customers">← Cuentas</RouterLink>
        <h1>{{ data.org.name }}</h1>
        <p class="lede">Metadatos de cuenta y uso agregado. Sin findings crudos.</p>
      </div>
      <span class="tag" :class="data.org.risk === 'ok' ? 'good' : data.org.risk === 'risk' ? 'bad' : 'warn'">{{ data.org.risk }}</span>
    </div>
    <div class="grid g-4">
      <div class="card"><h3>Plan</h3><div class="kpi kpi-sm">{{ data.org.plan }}</div></div>
      <div class="card"><h3>MRR</h3><div class="kpi kpi-sm">{{ money(data.org.mrr) }}</div></div>
      <div class="card"><h3>Salud</h3><div class="kpi kpi-sm">{{ data.org.health }}</div></div>
      <div class="card"><h3>COGS / MRR</h3><div class="kpi kpi-sm">{{ pct(data.margin.ratio, 0) }}</div></div>
    </div>
    <div class="grid g-2b" style="margin-top:14px">
      <div class="card">
        <h3>Uso 30d</h3>
        <div class="list-row"><span>Scans</span><b>{{ data.usage_30d.scans }}</b></div>
        <div class="list-row">
          <span>Hallazgos (conteo)</span>
          <b>{{ data.usage_30d.findings_hc }}</b>
        </div>
        <p class="kpi-sub" style="margin:0 0 8px">Conteo total — no filtrado High/Crit.</p>
        <div class="list-row"><span>Reports</span><b>{{ data.usage_30d.reports }}</b></div>
        <div class="list-row"><span>Última actividad</span><b>{{ data.org.last_active_days }}d</b></div>
        <div class="list-row"><span>Región · canal</span><b>{{ data.org.region }} · {{ data.org.channel }}</b></div>
        <div class="list-row"><span>Seats</span><b>{{ data.org.seats }}</b></div>
      </div>
      <div class="card">
        <h3>Targets autorizados</h3>
        <p class="lede" style="margin-bottom:10px">URLs y dominios autorizados para pentest. Los cambios se guardan en Raptor.</p>
        <div v-if="targetsError" class="targets-error">{{ targetsError }}</div>
        <div v-if="data.authorized_targets.length" class="target-list">
          <div v-for="(t, i) in data.authorized_targets" :key="i" class="list-row target-row">
            <span class="mono">{{ t }}</span>
            <button
              class="btn target-remove"
              type="button"
              :disabled="targetsBusy"
              title="Quitar target"
              @click="removeTarget(t)"
            >×</button>
          </div>
        </div>
        <div v-else class="empty">Sin restricción configurada.</div>
        <form class="filters target-form" @submit.prevent="addTarget">
          <input
            v-model="newTarget"
            placeholder="https://ejemplo.com o dominio"
            style="flex:1;min-width:180px"
            :disabled="targetsBusy"
          />
          <button class="btn primary" type="submit" :disabled="targetsBusy || !newTarget.trim()">Agregar</button>
        </form>
        <p v-if="previewText" class="target-preview">Vista previa: <span class="mono">{{ previewText }}</span></p>
        <div v-for="(w, i) in previewWarnings" :key="i" class="target-warning">
          <span class="tag warn">{{ w }}</span>
        </div>
        <p v-if="targetsBusy" class="kpi-sub">Guardando…</p>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Scans recientes</h3>
      <p class="lede" style="margin-bottom:10px">Últimos 25 scans — metadatos solamente.</p>
      <div v-if="data.recent_scans.length" class="scan-table">
        <div class="scan-head">
          <span>Target</span>
          <span>Status</span>
          <span>Findings</span>
          <span>Inicio</span>
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
      <h3>Notas internas</h3>
      <p class="lede" style="margin-bottom:10px">Siguiente paso: {{ data.next_step }}</p>
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'
import { targetAddErrorMessage, targetRemoveErrorMessage } from '@/lib/targetErrors'
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

interface TargetsMutationResult {
  ok: boolean
  entry: string
  authorized_targets: string[]
  warnings?: string[]
}

const route = useRoute()
const data = ref<Account | null>(null)
const note = ref('')
const loadError = ref(false)
const newTarget = ref('')
const targetsBusy = ref(false)
const targetsError = ref('')

function normalizePreview(entry: string): string {
  const trimmed = entry.trim()
  if (!trimmed) return ''
  if (/^[0-9a-fA-F:.]+\/\d{1,3}$/.test(trimmed)) return trimmed
  try {
    const url = trimmed.includes('://') ? trimmed : `https://${trimmed}`
    const host = new URL(url).hostname.toLowerCase()
    return host || trimmed.toLowerCase()
  } catch {
    return trimmed.toLowerCase()
  }
}

const previewText = computed(() => normalizePreview(newTarget.value))

const previewWarnings = computed(() => {
  const p = previewText.value
  if (!p) return []
  const warnings: string[] = []
  if (p.includes('metadata') || p === 'metadata.google.internal' || p === 'metadata.goog') {
    warnings.push('Hostname de metadata cloud — revisa antes de autorizar.')
  }
  if (p.startsWith('169.254.')) {
    warnings.push('IP link-local (169.254.x.x) — típica de metadata cloud.')
  }
  if (p === '127.0.0.1' || p === 'localhost') {
    warnings.push('IP loopback — solo válida en labs controlados.')
  }
  return warnings
})

function formatScanDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('es-ES')
}

function scanStatusClass(status: string): string {
  if (status === 'completed') return 'good'
  if (status === 'running') return 'warn'
  if (status === 'error' || status === 'cancelled') return 'bad'
  return ''
}

async function load() {
  loadError.value = false
  data.value = null
  try {
    data.value = await api<Account>(`/customers/${route.params.id}`)
  } catch {
    loadError.value = true
  }
}

async function addTarget() {
  const entry = newTarget.value.trim()
  if (!entry || !data.value) return
  targetsBusy.value = true
  targetsError.value = ''
  try {
    const result = await api<TargetsMutationResult>(`/customers/${route.params.id}/targets`, {
      method: 'POST',
      body: JSON.stringify({ entry }),
    })
    data.value.authorized_targets = result.authorized_targets
    newTarget.value = ''
  } catch (e) {
    targetsError.value = targetAddErrorMessage(e)
  } finally {
    targetsBusy.value = false
  }
}

async function removeTarget(entry: string) {
  if (!data.value) return
  const isLast = data.value.authorized_targets.length === 1
  if (isLast) {
    const ok = window.confirm(
      'Este es el último target autorizado. Si la org usa modo allowlist estricto, los scans quedarán bloqueados. ¿Continuar?'
    )
    if (!ok) return
  }
  targetsBusy.value = true
  targetsError.value = ''
  try {
    const result = await api<TargetsMutationResult>(`/customers/${route.params.id}/targets`, {
      method: 'DELETE',
      body: JSON.stringify({ entry }),
    })
    data.value.authorized_targets = result.authorized_targets
  } catch (e) {
    targetsError.value = targetRemoveErrorMessage(e)
  } finally {
    targetsBusy.value = false
  }
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
.target-list .list-row,
.target-row {
  justify-content: space-between;
  gap: 8px;
}
.target-form {
  margin-top: 12px;
}
.target-preview {
  margin: 8px 0 0;
  font-size: 0.9rem;
  opacity: 0.85;
}
.target-warning {
  margin-top: 6px;
}
.targets-error {
  color: #b42318;
  margin-bottom: 8px;
  font-size: 0.9rem;
}
.target-remove {
  min-width: 28px;
  padding: 2px 8px;
  line-height: 1.2;
}
</style>
