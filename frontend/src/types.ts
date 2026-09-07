export type Plan = 'Essential' | 'Professional' | 'Enterprise' | 'MSSP'
export type Risk = 'ok' | 'watch' | 'risk'

export interface Org {
  id: number
  name: string
  slug: string
  plan: Plan
  mrr: number
  health: number
  risk: Risk
  region: string
  channel: string
  stage: string
  last_active_days: number
  scans_30d: number
  findings_hc_30d: number
  reports_30d: number
  seats: number
  created_at: string
  owner: string
  payment_ok: boolean
  cogs_gemini: number
  cogs_infra: number
}

export interface Overview {
  dataset: string
  arr: number
  mrr: number
  net_new_mrr: number
  paying_logos: number
  pilots: number
  gross_margin: number
  nrr: number
  logo_churn: number
  revenue_churn: number
  platform_uptime: number
  arq_depth: number
  mrr_trend: number[]
  goal_net_new: { current: number; target: number }
  alerts: { severity: string; title: string; body: string }[]
  billing_mode: string
}

export interface Deal {
  id: number
  name: string
  org_id: number | null
  stage: string
  acv_usd: number
  probability: number
  source: string
  region: string
  close_date: string
  owner_email: string
}
