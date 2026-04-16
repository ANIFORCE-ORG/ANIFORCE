/**
 * 产品类型配置
 */

export interface ProductType {
  value: string
  label: string
  icon: string
  color: string
}

export const PRODUCT_TYPES: ProductType[] = [
  { value: 'short_drama', label: '短剧', icon: '🎬', color: '#E91E63' },
  { value: 'game_rpg', label: 'RPG游戏', icon: '🗡️', color: '#F44336' },
  { value: 'game_slg', label: 'SLG游戏', icon: '⚔️', color: '#FF9800' },
  { value: 'game_casual', label: '休闲游戏', icon: '🎮', color: '#4CAF50' },
  { value: 'social_app', label: '社交应用', icon: '💬', color: '#2196F3' },
  { value: 'ecommerce', label: '电商', icon: '🛒', color: '#9C27B0' },
  { value: 'tool_app', label: '工具应用', icon: '🔧', color: '#607D8B' },
  { value: 'education', label: '教育', icon: '📚', color: '#00BCD4' }
]

export const PRODUCT_TYPE_MAP: Record<string, ProductType> = PRODUCT_TYPES.reduce((acc, type) => {
  acc[type.value] = type
  return acc
}, {} as Record<string, ProductType>)

export function getProductType(value: string): ProductType | undefined {
  return PRODUCT_TYPE_MAP[value]
}

export function getProductTypeLabel(value: string): string {
  return PRODUCT_TYPE_MAP[value]?.label || value
}

export function getProductTypeIcon(value: string): string {
  return PRODUCT_TYPE_MAP[value]?.icon || '📱'
}

export function getProductTypeColor(value: string): string {
  return PRODUCT_TYPE_MAP[value]?.color || '#607D8B'
}
