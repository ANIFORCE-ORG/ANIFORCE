import { http } from './http'

export type OrganizationType = 'advertiser' | 'agency'
export type OrganizationRole = 'owner' | 'manager' | 'operator'
export type OrganizationMemberStatus = 'active' | 'invited' | 'requested' | 'disabled'

export interface Organization {
  id: string
  name: string
  type: OrganizationType
  role: OrganizationRole
  status: 'active' | 'disabled'
  member_count: number
  platform_account_count: number
  project_count: number
  created_at: string
}

export interface OrganizationMember {
  id: string
  user_id: string
  name: string
  email: string
  role: OrganizationRole
  status: OrganizationMemberStatus
  joined_at: string
}

export interface CreateOrganizationPayload {
  name: string
  type: OrganizationType
}

interface OrganizationsResponse {
  organizations: Organization[]
}

interface OrganizationMembersResponse {
  members: OrganizationMember[]
}

const normalizeOrganizations = (response: Organization[] | OrganizationsResponse): Organization[] => {
  return Array.isArray(response) ? response : response.organizations || []
}

const normalizeMembers = (response: OrganizationMember[] | OrganizationMembersResponse): OrganizationMember[] => {
  return Array.isArray(response) ? response : response.members || []
}

export async function getOrganizations(): Promise<Organization[]> {
  const response = await http.get<Organization[] | OrganizationsResponse>('/organizations')
  return normalizeOrganizations(response)
}

export async function createOrganization(payload: CreateOrganizationPayload): Promise<Organization> {
  return http.post<Organization>('/organizations', payload)
}

export async function getOrganizationMembers(organizationId: string): Promise<OrganizationMember[]> {
  const response = await http.get<OrganizationMember[] | OrganizationMembersResponse>(
    `/organizations/${organizationId}/members`
  )
  return normalizeMembers(response)
}

export async function inviteOrganizationMember(
  organizationId: string,
  payload: { email: string; role: OrganizationRole }
): Promise<OrganizationMember> {
  return http.post<OrganizationMember>(`/organizations/${organizationId}/invitations`, payload)
}

export async function setCurrentOrganization(organizationId: string): Promise<{ organization_id: string }> {
  return http.post<{ organization_id: string }>('/me/current-organization', { organization_id: organizationId })
}
