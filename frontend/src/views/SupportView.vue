<template>
  <div v-if="!s" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Support & Voice of Customer</h1>
        <p class="lede">Inbox ligero + NPS. El ticketing pesado se queda en Linear/email.</p>
      </div>
      <a v-if="linearUrl" :href="linearUrl" target="_blank" rel="noopener" class="btn primary">
        Abrir en Linear ↗
      </a>
      <span v-else class="tag warn">Linear sin configurar (LINEAR_WORKSPACE_URL)</span>
    </div>
    <div class="grid g-3">
      <div class="card"><h3>Open threads</h3><div class="kpi">{{ s.open }}</div></div>
      <div class="card"><h3>Median first reply</h3><div class="kpi kpi-sm">{{ s.median_first_reply_h }}h</div></div>
      <div class="card"><h3>NPS (90d)</h3><div class="kpi">{{ s.nps ?? '—' }}</div><div class="kpi-sub">n={{ s.nps_n }}</div></div>
    </div>
    <div class="grid g-2b" style="margin-top:14px">
      <div class="card">
        <h3>Open</h3>
        <div v-for="t in s.tickets" :key="t.id" class="list-row">
          <span>{{ t.title }} · {{ t.org_name }}</span>
          <span class="tag" :class="t.priority === 'P1' ? 'bad' : t.priority === 'P2' ? 'warn' : ''">{{ t.priority }}</span>
        </div>
      </div>
      <div class="card">
        <h3>Themes</h3>
        <div v-for="th in s.themes" :key="th.name" class="list-row">
          <span>{{ th.name }}</span><b>{{ th.mentions }} mentions</b>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'

type SupportPayload = {
  open: number
  median_first_reply_h: number
  nps: number | null
  nps_n: number
  tickets: { id: number; org_name: string; title: string; priority: string }[]
  themes: { name: string; mentions: number }[]
}

const s = ref<SupportPayload | null>(null)
const linearUrl = ref<string | null>(null)

onMounted(async () => {
  const [support, settings] = await Promise.all([
    api<SupportPayload>('/support'),
    api<{ integrations: Record<string, string> }>('/settings'),
  ])
  const linear = settings.integrations.linear
  linearUrl.value = linear && linear.startsWith('http') ? linear : null
  s.value = support
})
</script>
