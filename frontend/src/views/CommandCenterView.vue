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
        <div class="kpi-sub">{{ home.pilots }} pilot · {{ home.orgsWithPlan }} con plan</div>
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
        <div class="kpi">{{ ledgerLabel }}</div>
        <div class="kpi-sub">{{ ledgerSub }}</div>
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
      <h3>Alertas operativas</h3>
      <div v-for="a in realAlerts" :key="a.title" class="alert" :class="a.severity">
        <div>
          <div class="t">{{ a.title }}</div>
          {{ a.body }}
          <RouterLink v-if="a.href" class="alert-link" :to="a.href">Ver cuentas →</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import { money, num } from '@/lib/format'
import type { Overview } from '@/types'

interface HomeSnapshot {
  orgCount: number | null
  orgsWithPlan: number
  pilots: number
  scans7d: number | null
  wau: number | null
  openDeals: number | null
  ledgerMonth: number | null
  ledgerWired: boolean
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

const ledgerLabel = computed(() => {
  if (!home.value?.ledgerWired) return 'Sin dato'
  return money(home.value.ledgerMonth ?? 0)
})

const ledgerSub = computed(() => {
  if (!home.value?.ledgerWired) return 'Ledger no conectado'
  return 'MRR manual registrado'
})

onMounted(async () => {
  loading.value = true
  loadError.value = false
  try {
    const overview = await api<Overview>('/overview')

    home.value = {
      orgCount: overview.org_count ?? overview.paying_logos + overview.pilots,
      orgsWithPlan: overview.orgs_with_plan ?? overview.paying_logos,
      pilots: overview.pilots,
      scans7d: overview.scans_7d ?? null,
      wau: overview.wau_orgs ?? null,
      openDeals: overview.open_deals ?? null,
      ledgerMonth: overview.ledger_month_usd ?? null,
      ledgerWired: overview.ledger_wired ?? false,
      runningScans: overview.arq_depth ?? null,
      orphaned: overview.orphaned_running ?? null,
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
