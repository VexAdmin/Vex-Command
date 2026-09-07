import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'command', meta: { title: 'Command Center' }, component: () => import('@/views/CommandCenterView.vue') },
  { path: '/revenue', name: 'revenue', meta: { title: 'Revenue' }, component: () => import('@/views/RevenueView.vue') },
  { path: '/customers', name: 'customers', meta: { title: 'Customers' }, component: () => import('@/views/CustomersView.vue') },
  { path: '/customers/:id', name: 'account', meta: { title: 'Account 360' }, component: () => import('@/views/AccountView.vue') },
  { path: '/pipeline', name: 'pipeline', meta: { title: 'Pipeline' }, component: () => import('@/views/PipelineView.vue') },
  { path: '/usage', name: 'usage', meta: { title: 'Product Usage' }, component: () => import('@/views/UsageView.vue') },
  { path: '/economics', name: 'economics', meta: { title: 'Unit Economics' }, component: () => import('@/views/EconomicsView.vue') },
  { path: '/retention', name: 'retention', meta: { title: 'Retention' }, component: () => import('@/views/RetentionView.vue') },
  { path: '/support', name: 'support', meta: { title: 'Support / VoC' }, component: () => import('@/views/SupportView.vue') },
  { path: '/ops', name: 'ops', meta: { title: 'Platform Ops' }, component: () => import('@/views/OpsView.vue') },
  { path: '/goals', name: 'goals', meta: { title: 'Goals & Alerts' }, component: () => import('@/views/GoalsView.vue') },
  { path: '/settings', name: 'settings', meta: { title: 'Settings' }, component: () => import('@/views/SettingsView.vue') },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
