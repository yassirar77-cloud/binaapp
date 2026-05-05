'use client'

import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'binaapp_onboarding'

export interface PhotoSlot {
  file?: File
  url: string
  preview: string
  slot: 'hero' | 'menu_1' | 'menu_2' | 'menu_3' | 'menu_4' | 'interior'
}

export interface DishSuggestion {
  slot: string
  name: string
  description: string
  price: number
  photoUrl: string
}

export interface OnboardingState {
  photos: PhotoSlot[]
  dishes: DishSuggestion[]
  styleDna: string | null
  step: number
}

const defaultState: OnboardingState = {
  photos: [],
  dishes: [],
  styleDna: null,
  step: 1,
}

export function useOnboardingState() {
  const [state, setState] = useState<OnboardingState>(defaultState)

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        setState(parsed)
      }
    } catch {}
  }, [])

  const persist = useCallback((next: OnboardingState) => {
    setState(next)
    try {
      // Don't persist File objects
      const toStore = {
        ...next,
        photos: next.photos.map(p => ({ ...p, file: undefined })),
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore))
    } catch {}
  }, [])

  const setPhotos = useCallback((photos: PhotoSlot[]) => {
    persist({ ...state, photos, step: Math.max(state.step, 1) })
  }, [state, persist])

  const setDishes = useCallback((dishes: DishSuggestion[]) => {
    persist({ ...state, dishes, step: Math.max(state.step, 2) })
  }, [state, persist])

  const setStyleDna = useCallback((styleDna: string) => {
    persist({ ...state, styleDna, step: Math.max(state.step, 3) })
  }, [state, persist])

  const reset = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setState(defaultState)
  }, [])

  return { state, setPhotos, setDishes, setStyleDna, reset }
}
