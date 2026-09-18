import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import { checkSession } from '@/api/client'

const shellChildren = [
  { path: '', name: 'command', meta: { title: 'Hoy' }, component: () => import('@/views/CommandCenterView.vue') },
  { path: 'revenue', name: 'revenue', meta: { title: 'Ingresos' }, component: () => import('@/views/RevenueView.vue') },
  { path: 'customers', name: 'customers', meta: { title: 'Cuentas' }, component: () => import('@/views/CustomersView.vue') },
  { path: 'customers/:id', name: 'account', meta: { title: 'Cuenta' }, component: () => import('@/views/AccountView.vue') },
  { path: 'pipeline', name: 'pipeline', meta: { title: 'Pipeline' }, component: () => import('@/views/PipelineView.vue') },
  { path: 'usage', name: 'usage', meta: { title: 'Uso' }, component: () => import('@/views/UsageView.vue') },
  { path: 'economics', name: 'economics', meta: { title: 'Costes' }, component: () => import('@/views/EconomicsView.vue') },
  { path: 'retention', name: 'retention', meta: { title: 'Salud de cuentas' }, component: () => import('@/views/RetentionView.vue') },
  { path: 'support', name: 'support', meta: { title: 'Soporte' }, component: () => import('@/views/SupportView.vue') },
  { path: 'ops', name: 'ops', meta: { title: 'Plataforma' }, component: () => import('@/views/OpsView.vue') },
  { path: 'goals', name: 'goals', meta: { title: 'Metas' }, component: () => import('@/views/GoalsView.vue') },
  { path: 'settings', name: 'settings', meta: { title: 'Ajustes' }, component: () => import('@/views/SettingsView.vue') },
  { path: 'activity', name: 'activity', meta: { title: 'Actividad' }, component: () => import('@/views/ActivityView.vue') },
]

const routes = [
  {
    path: '/login',
    name: 'login',
    meta: { public: true },
    component: () => import('@/views/LoginView.vue'),
  },
  {
    path: '/',
    component: AppShell,
    children: shellChildren,
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  const ok = await checkSession()
  if (ok) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})
