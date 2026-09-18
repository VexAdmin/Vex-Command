<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="loading" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Actividad</h1>
        <p class="lede">Registro de acciones de operadores en VEX Command.</p>
      </div>
    </div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Cuándo</th>
            <th>Operador</th>
            <th>Acción</th>
            <th>Org</th>
            <th>Ruta</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in items" :key="i">
            <td class="mono">{{ formatWhen(item.created_at) }}</td>
            <td>{{ item.actor_email }}</td>
            <td><span class="tag">{{ item.action }}</span></td>
            <td class="mono">{{ item.org_id ?? '—' }}</td>
            <td class="mono">{{ item.path }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!items.length" class="empty">Sin actividad registrada.</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'

interface AuditItem {
  actor_email: string
  action: string
  org_id: number | null
  path: string
  ip: string | null
  created_at?: string
}

const items = ref<AuditItem[]>([])
const loading = ref(true)
const loadError = ref(false)

function formatWhen(iso?: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString('es-ES')
}

onMounted(async () => {
  loading.value = true
  loadError.value = false
  try {
    const r = await api<{ items: AuditItem[] }>('/audit')
    items.value = r.items
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})
</script>
