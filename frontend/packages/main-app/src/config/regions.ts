/**
 * 地区配置
 */

export interface Region {
  value: string
  label: string
  code: string
}

export const REGIONS: Region[] = [
  { value: 'US', label: '美国', code: 'US' },
  { value: 'GB', label: '英国', code: 'GB' },
  { value: 'DE', label: '德国', code: 'DE' },
  { value: 'JP', label: '日本', code: 'JP' },
  { value: 'KR', label: '韩国', code: 'KR' },
  { value: 'SG', label: '新加坡', code: 'SG' },
  { value: 'MY', label: '马来西亚', code: 'MY' },
  { value: 'TH', label: '泰国', code: 'TH' },
  { value: 'ID', label: '印度尼西亚', code: 'ID' },
  { value: 'BR', label: '巴西', code: 'BR' },
  { value: 'IN', label: '印度', code: 'IN' },
  { value: 'SA', label: '沙特阿拉伯', code: 'SA' }
]

export const REGION_MAP: Record<string, Region> = REGIONS.reduce((acc, region) => {
  acc[region.value] = region
  return acc
}, {} as Record<string, Region>)

export function getRegion(value: string): Region | undefined {
  return REGION_MAP[value]
}

export function getRegionLabel(value: string): string {
  return REGION_MAP[value]?.label || value
}

export function getRegionCode(value: string): string {
  return REGION_MAP[value]?.code || value
}
