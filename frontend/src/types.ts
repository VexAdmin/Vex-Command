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
  arr: number | null
  mrr: number | null
  net_new_mrr: number | null
  paying_logos: number
  orgs_with_plan?: number
  org_count?: number
  pilots: number
  gross_margin: number | null
  nrr: number | null
  logo_churn: number | null
  revenue_churn: number | null
  platform_uptime: number | null
  arq_depth: number
  mrr_trend: number[] | null
  goal_net_new: { current: number | null; target: number }
  alerts: { severity: string; title: string; body: string; href?: string }[]
  billing_mode: string
  ledger_wired?: boolean
  ledger_month_usd?: number | null
  open_deals?: number | null
  stripe_wired?: boolean
  scans_7d?: number
  wau_orgs?: number
  orphaned_running?: number | null
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
