import { computed, ref } from 'vue'
import type { Organization, OrganizationMember } from '@/api/organizations'

const ORGANIZATION_STORAGE_KEY = 'animagus_current_organization'

const demoOrganizations: Organization[] = [
  {
    id: 'org-aniforce-growth',
    name: 'ANIFORCE Growth',
    type: 'advertiser',
    role: 'owner',
    status: 'active',
    member_count: 4,
    platform_account_count: 3,
    project_count: 3,
    created_at: '2026-05-01T09:00:00Z',
  },
  {
    id: 'org-overseas-agency',
    name: 'Overseas UA Studio',
    type: 'agency',
    role: 'manager',
    status: 'active',
    member_count: 7,
    platform_account_count: 6,
    project_count: 5,
    created_at: '2026-05-08T09:00:00Z',
  },
]

const demoMembersByOrganization: Record<string, OrganizationMember[]> = {
  'org-aniforce-growth': [
    {
      id: 'member-owner',
      user_id: 'admin-001',
      name: 'Admin',
      email: 'test@animagus.com',
      role: 'owner',
      status: 'active',
      joined_at: '2026-05-01T09:00:00Z',
    },
    {
      id: 'member-manager',
      user_id: 'user-manager',
      name: 'Campaign Manager',
      email: 'manager@aniforce.ai',
      role: 'manager',
      status: 'active',
      joined_at: '2026-05-10T09:00:00Z',
    },
    {
      id: 'member-operator',
      user_id: 'user-operator',
      name: 'Media Buyer',
      email: 'buyer@aniforce.ai',
      role: 'operator',
      status: 'active',
      joined_at: '2026-05-14T09:00:00Z',
    },
  ],
  'org-overseas-agency': [
    {
      id: 'member-agency-manager',
      user_id: 'admin-001',
      name: 'Admin',
      email: 'test@animagus.com',
      role: 'manager',
      status: 'active',
      joined_at: '2026-05-08T09:00:00Z',
    },
  ],
}

const readStoredOrganization = (): string | null => {
  return localStorage.getItem(ORGANIZATION_STORAGE_KEY)
}

const organizations = ref<Organization[]>([...demoOrganizations])
const selectedOrganizationId = ref<string>(
  readStoredOrganization() || demoOrganizations[0].id
)

export function useOrganizationContext() {
  const currentOrganization = computed(() => {
    return organizations.value.find((organization) => organization.id === selectedOrganizationId.value)
      || organizations.value[0]
  })

  const useDemoOrganizations = () => {
    organizations.value = [...demoOrganizations]
    if (!organizations.value.some((organization) => organization.id === selectedOrganizationId.value)) {
      selectedOrganizationId.value = organizations.value[0].id
    }
  }

  const selectOrganization = (organizationId: string) => {
    selectedOrganizationId.value = organizationId
    localStorage.setItem(ORGANIZATION_STORAGE_KEY, organizationId)
  }

  const addLocalOrganization = (organization: Organization) => {
    organizations.value = [organization, ...organizations.value]
    selectOrganization(organization.id)
  }

  const getDemoMembers = (organizationId: string): OrganizationMember[] => {
    return [...(demoMembersByOrganization[organizationId] || [])]
  }

  return {
    organizations,
    currentOrganization,
    selectedOrganizationId,
    useDemoOrganizations,
    selectOrganization,
    addLocalOrganization,
    getDemoMembers,
  }
}
