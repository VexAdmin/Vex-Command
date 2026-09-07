<template>
  <div v-if="!g" class="empty">Cargando…</div>
  <div v-else>
    <div class="hero-row">
      <div>
        <h1>Goals & Alerts</h1>
        <p class="lede">OKRs trimestrales, KPIs semanales y reglas que te pegan en Slack.</p>
      </div>
    </div>
    <div class="grid g-2b">
      <div class="card">
        <h3>{{ g.quarter }} OKRs</h3>
        <div v-for="o in g.okrs" :key="o.title" style="margin-bottom:12px">
          <div class="list-row"><span>{{ o.title }}</span><b>{{ fmt(o) }}</b></div>
          <div class="progress"><i :style="{ width: okrPct(o) + '%' }" /></div>
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
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money, pct } from '@/lib/format'

interface Okr {
  title: string
  current: number | null
  target: number
  unit: string
}

const g = ref<{ quarter: string; okrs: Okr[]; rules: { name: string; enabled: boolean }[] } | null>(null)

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

onMounted(async () => {
  g.value = await api('/goals')
})
</script>
