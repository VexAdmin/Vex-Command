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
              @click="requestRemoveTarget(t)"
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
        <div v-if="(data.target_timeline || []).length" class="target-timeline">
          <h4 class="target-timeline-title">Historial allowlist</h4>
          <div v-for="(ev, i) in data.target_timeline" :key="i" class="list-row timeline-row">
            <span>
              <span class="tag" :class="ev.kind === 'add' ? 'good' : 'warn'">
                {{ ev.kind === 'add' ? 'Añadido' : 'Quitado' }}
              </span>
              <span class="mono timeline-entry">{{ ev.entry }}</span>
            </span>
            <span class="mono timeline-meta">{{ ev.actor_email }} · {{ formatScanDate(ev.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
    <div class="card" style="margin-top:14px">
      <h3>Operación</h3>
      <p class="lede" style="margin-bottom:10px">Estado del piloto y próximo hito — solo en Command (no toca Raptor).</p>
      <div v-if="opsError" class="targets-error">{{ opsError }}</div>
      <form class="ops-form" @submit.prevent="saveOps">
        <label class="ops-field">
          Etapa
          <select v-model="opsPilotStage" :disabled="opsBusy">
            <option value="discovery">Discovery</option>
            <option value="pilot">Piloto</option>
            <option value="production">Producción</option>
            <option value="paused">Pausado</option>
          </select>
        </label>
        <label class="ops-field ops-field-grow">
          Próximo hito
          <input v-model="opsNextStep" type="text" placeholder="Ej. Quarterly review" :disabled="opsBusy" />
        </label>
        <button class="btn primary" type="submit" :disabled="opsBusy">Guardar</button>
      </form>
      <p v-if="data.ops?.updated_by" class="kpi-sub">
        Actualizado por {{ data.ops.updated_by }}
        <span v-if="data.ops.updated_at"> · {{ formatScanDate(data.ops.updated_at) }}</span>
      </p>
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
      <p class="lede" style="margin-bottom:10px">Próximo hito: {{ data.ops?.next_step || data.next_step }}</p>
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

    <div
      v-if="removePending"
      class="modal-back"
      role="dialog"
      aria-modal="true"
      aria-labelledby="remove-target-title"
      @click.self="cancelRemoveTarget"
    >
      <div class="modal remove-target-modal">
        <h3 id="remove-target-title">Quitar target autorizado</h3>
        <p class="lede">
          Vas a quitar <span class="mono">{{ removePending }}</span> de
          <b>{{ data.org.name }}</b>. Los scans contra este dominio quedarán bloqueados si la org usa allowlist estricto.
        </p>
        <p v-if="isLastTargetPending" class="remove-target-last-warn">
          Es el último target de la lista. Sin targets autorizados, los scans pueden quedar bloqueados por completo.
        </p>
        <label class="remove-target-label" for="remove-target-confirm">
          Escribe <span class="mono">eliminar</span> para confirmar
        </label>
        <input
          id="remove-target-confirm"
          ref="removeConfirmInput"
          v-model="removeConfirmText"
          class="remove-target-input"
          type="text"
          autocomplete="off"
          spellcheck="false"
          placeholder="eliminar"
          :disabled="targetsBusy"
          @keydown.enter.prevent="confirmRemoveTarget"
        />
        <div class="remove-target-actions">
          <button class="btn" type="button" :disabled="targetsBusy" @click="cancelRemoveTarget">
            Cancelar
          </button>
          <button
            class="btn danger"
            type="button"
            :disabled="targetsBusy || !removeConfirmReady"
            @click="confirmRemoveTarget"
          >
            Quitar target
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
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

interface TargetTimelineEvent {
  kind: 'add' | 'remove'
  entry: string
  actor_email: string
  created_at: string
}

interface AccountOps {
  pilot_stage: string
  pilot_stage_label: string
  next_step: string | null
  updated_at?: string | null
  updated_by?: string | null
}

interface Account {
  org: Org
  notes: { body: string; actor_email: string }[]
  ops: AccountOps
  target_timeline: TargetTimelineEvent[]
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
const opsPilotStage = ref('pilot')
const opsNextStep = ref('')
const opsBusy = ref(false)
const opsError = ref('')
const removePending = ref<string | null>(null)
const removeConfirmText = ref('')
const removeConfirmInput = ref<HTMLInputElement | null>(null)

const REMOVE_CONFIRM_WORD = 'eliminar'

const removeConfirmReady = computed(
  () => removeConfirmText.value.trim().toLowerCase() === REMOVE_CONFIRM_WORD,
)

const isLastTargetPending = computed(() => {
  if (!data.value || !removePending.value) return false
  return data.value.authorized_targets.length === 1
})

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
    if (data.value?.ops) {
      opsPilotStage.value = data.value.ops.pilot_stage
      opsNextStep.value = data.value.ops.next_step || ''
    }
  } catch {
    loadError.value = true
  }
}

async function saveOps() {
  if (!data.value) return
  opsBusy.value = true
  opsError.value = ''
  try {
    const result = await api<{ ops: AccountOps }>(`/customers/${route.params.id}/ops`, {
      method: 'PATCH',
      body: JSON.stringify({
        pilot_stage: opsPilotStage.value,
        next_step: opsNextStep.value,
      }),
    })
    data.value.ops = result.ops
    data.value.next_step = result.ops.next_step || data.value.next_step
  } catch {
    opsError.value = 'No se pudo guardar la operación de cuenta.'
  } finally {
    opsBusy.value = false
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

async function requestRemoveTarget(entry: string) {
  if (targetsBusy.value) return
  removePending.value = entry
  removeConfirmText.value = ''
  await nextTick()
  removeConfirmInput.value?.focus()
}

function cancelRemoveTarget() {
  if (targetsBusy.value) return
  removePending.value = null
  removeConfirmText.value = ''
}

async function confirmRemoveTarget() {
  if (!data.value || !removePending.value || !removeConfirmReady.value) return
  const entry = removePending.value
  targetsBusy.value = true
  targetsError.value = ''
  try {
    const result = await api<TargetsMutationResult>(`/customers/${route.params.id}/targets`, {
      method: 'DELETE',
      body: JSON.stringify({ entry }),
    })
    data.value.authorized_targets = result.authorized_targets
    removePending.value = null
    removeConfirmText.value = ''
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
watch(removePending, (pending, _, onCleanup) => {
  if (!pending) return
  const onKey = (event: KeyboardEvent) => {
    if (event.key === 'Escape') cancelRemoveTarget()
  }
  document.addEventListener('keydown', onKey)
  onCleanup(() => document.removeEventListener('keydown', onKey))
})
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
.remove-target-modal h3 {
  margin: 0 0 10px;
}
.remove-target-last-warn {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: rgba(180, 35, 24, 0.08);
  color: #9a1f14;
  font-size: 0.9rem;
}
.remove-target-label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.9rem;
  color: var(--muted);
}
.remove-target-input {
  width: 100%;
  margin-bottom: 14px;
}
.remove-target-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.btn.danger {
  background: #b42318;
  color: #fff;
  border-color: #b42318;
}
.btn.danger:disabled {
  opacity: 0.45;
}
.target-timeline {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--line, #d5deea);
}
.target-timeline-title {
  margin: 0 0 8px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.timeline-row {
  flex-wrap: wrap;
  font-size: 0.84rem;
}
.timeline-entry {
  margin-left: 8px;
}
.timeline-meta {
  font-size: 0.75rem;
  opacity: 0.85;
}
.ops-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: flex-end;
}
.ops-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 600;
}
.ops-field-grow {
  flex: 1;
  min-width: 200px;
}
.ops-field select,
.ops-field input {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
  font-size: 0.85rem;
  color: var(--ink);
}
</style>
