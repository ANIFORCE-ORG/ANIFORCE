import { http } from './http'

export interface MediaOpsDashboard {
  metrics: Record<string, number>
  status_funnel: Array<{ status: string; label: string; count: number }>
  pending_tasks: Array<{ type: string; title: string; owner: string; priority: string }>
  alerts: Array<{ level: string; message: string }>
}

export interface MediaCustomer {
  id: string
  name: string
  industry: string
  level: string
  payment_preference: string
  contact_group: string
  owner: string
  risk_note?: string
}

export interface MediaProduct {
  id: string
  platform: string
  name: string
  account_type: string
  account_property: string
  eligible_industries: string[]
  min_recharge_usd: number
  delivery_sla_minutes: number
  selling_points: string[]
}

export interface AccountOrder {
  id: string
  customer_id: string
  customer_name: string
  product_id: string
  product_name: string
  platform: string
  account_type: string
  timezone: string
  email: string
  quantity: number
  ad_industry: string
  payment_method: 'USD' | 'USDT'
  receivable_amount: number
  status: string
  owner: string
  created_at: string
  updated_at: string
  next_action: string
  delivered_accounts: string[]
  remark?: string
}

export interface PaymentVoucher {
  id: string
  order_id: string
  customer_name: string
  amount: number
  currency: 'USD' | 'USDT'
  status: string
  transaction_hash?: string
  screenshot_url?: string
  submitted_at: string
  reviewed_by?: string
  reviewed_at?: string
}

export interface MediaAccount {
  id: string
  account_id: string
  account_name: string
  customer_name: string
  platform: string
  account_type: string
  account_property: string
  timezone: string
  email: string
  business_manager_id?: string
  status: string
  spend: number
  balance: number
  delivered_at?: string
  owner: string
  operation_flags: string[]
}

export interface ServiceTicket {
  id: string
  customer_name: string
  account_id?: string
  ticket_type: string
  priority: string
  status: string
  owner: string
  sla_due_at: string
  summary: string
}

export interface KnowledgeArticle {
  id: string
  category: string
  title: string
  trigger_keywords: string[]
  answer: string
}

export async function getMediaOpsDashboard(): Promise<MediaOpsDashboard> {
  return http.get('/media-ops/dashboard')
}

export async function getMediaCustomers(): Promise<MediaCustomer[]> {
  return http.get('/media-ops/customers')
}

export async function getMediaProducts(): Promise<MediaProduct[]> {
  return http.get('/media-ops/products')
}

export async function getMediaOrders(): Promise<AccountOrder[]> {
  return http.get('/media-ops/orders')
}

export async function getPaymentVouchers(): Promise<PaymentVoucher[]> {
  return http.get('/media-ops/payments')
}

export async function getMediaAccounts(): Promise<MediaAccount[]> {
  return http.get('/media-ops/accounts')
}

export async function getServiceTickets(): Promise<ServiceTicket[]> {
  return http.get('/media-ops/tickets')
}

export async function getKnowledgeArticles(keyword?: string): Promise<KnowledgeArticle[]> {
  const suffix = keyword ? `?keyword=${encodeURIComponent(keyword)}` : ''
  return http.get(`/media-ops/knowledge${suffix}`)
}
