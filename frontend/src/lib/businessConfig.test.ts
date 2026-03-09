import { describe, it, expect } from 'vitest'
import {
  businessConfig,
  getBusinessConfig,
  getBusinessTypeOptions,
  getBusinessPrimaryColor,
} from './businessConfig'

describe('businessConfig', () => {
  const allTypes = ['food', 'clothing', 'salon', 'services', 'bakery', 'general']

  it('has all expected business types', () => {
    for (const type of allTypes) {
      expect(businessConfig[type]).toBeDefined()
    }
  })

  it('each type has required fields', () => {
    const requiredFields = [
      'icon', 'buttonLabel', 'pageTitle', 'orderTitle',
      'emoji', 'cartIcon', 'cartLabel', 'primaryColor',
      'categories', 'features', 'labels',
    ]

    for (const type of allTypes) {
      const config = businessConfig[type]
      for (const field of requiredFields) {
        expect(config).toHaveProperty(field)
      }
    }
  })

  it('each type has at least 2 categories', () => {
    for (const type of allTypes) {
      expect(businessConfig[type].categories.length).toBeGreaterThanOrEqual(2)
    }
  })

  it('food type has delivery zones enabled', () => {
    expect(businessConfig.food.features.deliveryZones).toBe(true)
  })

  it('salon type has appointment date enabled', () => {
    expect(businessConfig.salon.features.appointmentDate).toBe(true)
  })

  it('clothing type has size options', () => {
    expect(businessConfig.clothing.features.sizeOptions).toBe(true)
    expect(businessConfig.clothing.sizes).toBeDefined()
    expect(businessConfig.clothing.sizes!.length).toBeGreaterThan(0)
  })

  it('bakery type has custom message', () => {
    expect(businessConfig.bakery.features.customMessage).toBe(true)
    expect(businessConfig.bakery.customMessagePlaceholder).toBeDefined()
  })

  it('services type has location choice', () => {
    expect(businessConfig.services.features.locationChoice).toBe(true)
    expect(businessConfig.services.locationOptions).toBeDefined()
  })
})

describe('getBusinessConfig', () => {
  it('returns correct config for known type', () => {
    const config = getBusinessConfig('food')
    expect(config.icon).toBe('🛵')
  })

  it('falls back to general for unknown type', () => {
    const config = getBusinessConfig('nonexistent')
    expect(config).toEqual(businessConfig.general)
  })
})

describe('getBusinessTypeOptions', () => {
  it('returns all business type options', () => {
    const options = getBusinessTypeOptions()
    expect(options.length).toBe(6)
    const ids = options.map(o => o.id)
    expect(ids).toContain('food')
    expect(ids).toContain('clothing')
    expect(ids).toContain('general')
  })

  it('each option has id, icon, and label', () => {
    for (const option of getBusinessTypeOptions()) {
      expect(option.id).toBeDefined()
      expect(option.icon).toBeDefined()
      expect(option.label).toBeDefined()
    }
  })
})

describe('getBusinessPrimaryColor', () => {
  it('returns hex color for known type', () => {
    const color = getBusinessPrimaryColor('food')
    expect(color).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('falls back to general color for unknown type', () => {
    const color = getBusinessPrimaryColor('unknown')
    expect(color).toBe(businessConfig.general.primaryColor)
  })
})
