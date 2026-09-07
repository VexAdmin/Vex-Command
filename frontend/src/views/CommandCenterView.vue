<template>
  <div v-if="!data" class="empty">Cargando…</div>
  <div v-else>
    <div class="banner">
      Superficie interna de founder — no es el Dashboard MSSP. Host:
      <code>ops.vexraptor.com</code>.
      <span v-if="data.dataset === 'scale'"> Datos de diseño a ~1.000 orgs (hoy puedes correr <code>FOUNDER_DATASET=pre_revenue</code>).</span>
      <span v-else> Modo pre-revenue: 0 logos pagando. Pipeline + ops son la fuente de verdad.</span>
    </div>
    <div class="hero-row">
      <div>
        <h1>Command Center</h1>
        <p class="lede">Una sola pantalla para saber si el negocio respira: dinero, logos, margen y salud de la máquina.</p>
      </div>
    </div>
    <div class="grid g-4">
      <div class="card">
        <h3>ARR</h3>
        <div class="kpi">{{ money(data.arr) }}</div>
        <div class="kpi-sub"><span class="delta up">MRR × 12</span></div>
      </div>
      <div class="card">
        <h3>MRR</h3>
        <div class="kpi">{{ money(data.mrr) }}</div>
        <div class="kpi-sub"><span class="delta" :class="data.net_new_mrr >= 0 ? 'up' : 'down'">{{ data.net_new_mrr >= 0 ? '↑' : '↓' }} {{ money(data.net_new_mrr) }}</span> net new</div>
      </div>
      <div class="card">
        <h3>Paying logos</h3>
        <div class="kpi">{{ num(data.paying_logos) }}</div>
        <div class="kpi-sub">{{ data.pilots }} pilots</div>
      </div>
      <div class="card">
        <h3>Gross margin</h3>
        <div class="kpi">{{ pct(data.gross_margin, 0) }}</div>
        <div class="kpi-sub"><span class="delta flat">Gemini + infra vs MRR</span></div>
      </div>
    </div>
    <div class="grid g-2" style="margin-top:14px">
      <div class="card">
        <h3>MRR trend (12 months)</h3>
        <SparkBars :values="scaledTrend" />
      </div>
      <div class="card">
        <h3>Founder alerts</h3>
        <div v-for="a in data.alerts" :key="a.title" class="alert" :class="a.severity">
          <div>
            <div class="t">{{ a.title }}</div>
            {{ a.body }}
          </div>
        </div>
      </div>
    </div>
    <div class="grid g-3" style="margin-top:14px">
      <div class="card">
        <h3>Goal · Net new MRR</h3>
        <div class="kpi kpi-sm">{{ money(data.goal_net_new.current) }} / {{ money(data.goal_net_new.target) }}</div>
        <div class="progress"><i :style="{ width: goalPct + '%' }" /></div>
        <div class="kpi-sub">{{ goalPct }}% del mes</div>
      </div>
      <div class="card">
        <h3>NRR</h3>
        <div class="kpi">{{ pct(data.nrr, 0) }}</div>
        <div class="kpi-sub"><span class="delta" :class="data.nrr >= 1 ? 'up' : 'down'">{{ data.nrr >= 1 ? 'Expansion > churn' : 'Below 100%' }}</span></div>
      </div>
      <div class="card">
        <h3>Platform health</h3>
        <div class="kpi">{{ pct(data.platform_uptime, 1) }}</div>
        <div class="kpi-sub">Uptime 30d · cola ARQ {{ data.arq_depth }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import SparkBars from '@/components/SparkBars.vue'
import { api } from '@/api/client'
import { money, num, pct } from '@/lib/format'
import type { Overview } from '@/types'

const data = ref<Overview | null>(null)
const scaledTrend = computed(() => (data.value?.mrr_trend || []).map((v) => v / 1000))
const goalPct = computed(() => {
  const g = data.value?.goal_net_new
  if (!g || !g.target) return 0
  return Math.min(100, Math.round((g.current / g.target) * 100))
})

onMounted(async () => {
  data.value = await api<Overview>('/overview')
})
</script>
