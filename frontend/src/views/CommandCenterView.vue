<template>
  <div v-if="loadError" class="empty">No se pudo cargar. Reintenta.</div>
  <div v-else-if="loading" class="empty">Cargando…</div>
  <div v-else-if="home">
    <div v-if="showPreRevenueBanner" class="banner">
      Sin facturación automática. Los ingresos salen del ledger manual.
    </div>
    <div class="hero-row">
      <div>
        <h1>Hoy</h1>
        <p class="lede">Lo que existe hoy: cuentas, uso, pipeline, ledger y salud de la plataforma.</p>
      </div>
    </div>
    <div class="grid g-4">
      <div class="card">
        <h3>Cuentas</h3>
        <div class="kpi">{{ num(home.orgCount ?? 0) }}</div>
        <div class="kpi-sub">{{ home.pilots }} pilot · {{ home.paying }} con plan</div>
      </div>
      <div v-if="home.scans7d != null" class="card">
        <h3>Scans 7d</h3>
        <div class="kpi">{{ num(home.scans7d) }}</div>
      </div>
      <div v-if="home.wau != null" class="card">
        <h3>WAU</h3>
        <div class="kpi">{{ num(home.wau) }}</div>
        <div class="kpi-sub">Orgs con actividad reciente</div>
      </div>
      <div class="card">
        <h3>Deals abiertos</h3>
        <div class="kpi">{{ num(home.openDeals ?? 0) }}</div>
      </div>
    </div>
    <div class="grid g-3" style="margin-top:14px">
      <div class="card">
        <h3>Ledger del mes</h3>
        <div class="kpi">{{ money(home.ledgerMonth ?? 0) }}</div>
        <div class="kpi-sub">MRR manual registrado</div>
      </div>
      <div v-if="home.runningScans != null" class="card">
        <h3>Scans en curso</h3>
        <div class="kpi">{{ num(home.runningScans) }}</div>
      </div>
      <div v-if="home.orphaned != null" class="card">
        <h3>Huérfanos (&gt;2 h)</h3>
        <div class="kpi">{{ num(home.orphaned) }}</div>
      </div>
    </div>
    <div v-if="realAlerts.length" class="card" style="margin-top:14px">
      <h3>Alertas</h3>
      <div v-for="a in realAlerts" :key="a.title" class="alert" :class="a.severity">
        <div>
          <div class="t">{{ a.title }}</div>
          {{ a.body }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { money, num } from '@/lib/format'
import type { Deal, Overview } from '@/types'

interface HomeSnapshot {
  orgCount: number | null
  paying: number
  pilots: number
  scans7d: number | null
  wau: number | null
  openDeals: number | null
  ledgerMonth: number | null
  runningScans: number | null
  orphaned: number | null
  billingMode: string
  alerts: Overview['alerts']
}

const loading = ref(true)
const loadError = ref(false)
const home = ref<HomeSnapshot | null>(null)

const showPreRevenueBanner = computed(
  () => home.value?.billingMode === 'manual_ledger' || home.value?.billingMode === 'manual',
)

const realAlerts = computed(() =>
  (home.value?.alerts || []).filter((a) => a.title !== 'Pre-revenue mode'),
)

function currentMonthPrefix(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

function sumLedgerMonth(items: { period_month: string; mrr_usd: number }[]): number {
  const prefix = currentMonthPrefix()
  return items
    .filter((e) => String(e.period_month).startsWith(prefix))
    .reduce((sum, e) => sum + e.mrr_usd, 0)
}

onMounted(async () => {
  loading.value = true
  loadError.value = false
  try {
    const [overview, deals, manual, ops] = await Promise.all([
      api<Overview>('/overview'),
      api<{ items: Deal[] }>('/pipeline/deals'),
      api<{ items: { period_month: string; mrr_usd: number }[] }>('/revenue/manual'),
      api<{ arq_depth: number; orphaned_running: number }>('/ops/platform'),
    ])

    const openDeals = deals.items.filter((d) => d.stage !== 'won' && d.stage !== 'lost').length
    const orgCount = overview.paying_logos + overview.pilots

    home.value = {
      orgCount: orgCount,
      paying: overview.paying_logos,
      pilots: overview.pilots,
      scans7d: overview.scans_7d ?? null,
      wau: overview.wau_orgs ?? null,
      openDeals,
      ledgerMonth: sumLedgerMonth(manual.items),
      runningScans: ops.arq_depth ?? null,
      orphaned: ops.orphaned_running ?? null,
      billingMode: overview.billing_mode,
      alerts: overview.alerts,
    }
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})
</script>
