'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Sparkles, Loader2 } from 'lucide-react'
import ProgressBar from '../ProgressBar'
import { useOnboardingState, DishSuggestion } from '@/hooks/useOnboardingState'

export default function DishesPage() {
  const router = useRouter()
  const { state, setDishes } = useOnboardingState()
  const [dishes, setLocalDishes] = useState<DishSuggestion[]>(state.dishes)
  const [loading, setLoading] = useState(false)
  const [loadingSlots, setLoadingSlots] = useState<Set<string>>(new Set())

  const menuPhotos = state.photos.filter(p => p.slot.startsWith('menu_'))

  // Auto-suggest on mount if we have menu photos and no dishes yet
  useEffect(() => {
    if (menuPhotos.length > 0 && dishes.length === 0) {
      suggestAll()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function suggestDish(photoUrl: string, slot: string): Promise<DishSuggestion> {
    try {
      const res = await fetch('/api/dish-suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ photoUrl }),
      })
      const data = await res.json()
      return {
        slot,
        name: data.name || '',
        description: data.description || '',
        price: data.suggested_price_rm || 0,
        photoUrl,
      }
    } catch {
      return { slot, name: '', description: '', price: 0, photoUrl }
    }
  }

  async function suggestAll() {
    setLoading(true)
    const slots = new Set(menuPhotos.map(p => p.slot))
    setLoadingSlots(slots)

    const results = await Promise.all(
      menuPhotos.map(p => suggestDish(p.url, p.slot))
    )

    setLocalDishes(results)
    setDishes(results)
    setLoadingSlots(new Set())
    setLoading(false)
  }

  function updateDish(index: number, field: keyof DishSuggestion, value: string | number) {
    const updated = [...dishes]
    updated[index] = { ...updated[index], [field]: value }
    setLocalDishes(updated)
  }

  function handleContinue() {
    setDishes(dishes)
    router.push('/onboarding/style')
  }

  // If no photos uploaded, show manual entry
  const showManualEntry = menuPhotos.length === 0

  return (
    <>
      <ProgressBar currentStep={2} />

      <div className="text-center mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
          Hidangan Anda
        </h1>
        <p className="text-gray-600">
          {showManualEntry
            ? 'Masukkan butiran hidangan anda secara manual.'
            : 'AI telah cadangkan nama berdasarkan foto anda. Edit jika perlu.'}
        </p>
      </div>

      {loading && (
        <div className="text-center py-8">
          <Loader2 size={32} className="animate-spin text-orange-500 mx-auto mb-3" />
          <p className="text-gray-600">AI sedang mengenali hidangan anda...</p>
        </div>
      )}

      {!loading && (
        <div className="space-y-6">
          {(showManualEntry ? Array.from({ length: 4 }, (_, i) => ({
            slot: `menu_${i + 1}`,
            name: '',
            description: '',
            price: 0,
            photoUrl: '',
          })) : dishes).map((dish, i) => {
            const photo = menuPhotos.find(p => p.slot === dish.slot)
            const isSlotLoading = loadingSlots.has(dish.slot)

            return (
              <div
                key={dish.slot}
                className="bg-white rounded-xl border border-gray-200 p-4 md:p-6 shadow-sm"
              >
                <div className="flex gap-4">
                  {/* Photo thumbnail */}
                  {photo && (
                    <div className="w-20 h-20 md:w-24 md:h-24 rounded-lg overflow-hidden flex-shrink-0">
                      <img
                        src={photo.preview || photo.url}
                        alt={dish.name || 'Menu photo'}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}

                  <div className="flex-1 space-y-3">
                    {isSlotLoading ? (
                      <div className="flex items-center gap-2 text-gray-500">
                        <Loader2 size={16} className="animate-spin" />
                        <span className="text-sm">Mengenali...</span>
                      </div>
                    ) : (
                      <>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">
                            Nama Hidangan (BM)
                          </label>
                          <input
                            type="text"
                            value={showManualEntry ? (dishes[i]?.name || '') : dish.name}
                            onChange={e => {
                              if (showManualEntry && !dishes[i]) {
                                const newDishes = [...dishes]
                                while (newDishes.length <= i) {
                                  newDishes.push({ slot: `menu_${newDishes.length + 1}`, name: '', description: '', price: 0, photoUrl: '' })
                                }
                                newDishes[i] = { ...newDishes[i], name: e.target.value }
                                setLocalDishes(newDishes)
                              } else {
                                updateDish(i, 'name', e.target.value)
                              }
                            }}
                            placeholder="cth. Nasi Lemak Ayam Goreng"
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-orange-300 focus:border-orange-400 outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">
                            Keterangan
                          </label>
                          <input
                            type="text"
                            value={showManualEntry ? (dishes[i]?.description || '') : dish.description}
                            onChange={e => {
                              if (showManualEntry && !dishes[i]) {
                                const newDishes = [...dishes]
                                while (newDishes.length <= i) {
                                  newDishes.push({ slot: `menu_${newDishes.length + 1}`, name: '', description: '', price: 0, photoUrl: '' })
                                }
                                newDishes[i] = { ...newDishes[i], description: e.target.value }
                                setLocalDishes(newDishes)
                              } else {
                                updateDish(i, 'description', e.target.value)
                              }
                            }}
                            placeholder="cth. Nasi wangi dengan ayam goreng rangup"
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-orange-300 focus:border-orange-400 outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-500 mb-1">
                            Harga (RM)
                          </label>
                          <input
                            type="number"
                            value={showManualEntry ? (dishes[i]?.price || '') : dish.price}
                            onChange={e => {
                              const val = parseFloat(e.target.value) || 0
                              if (showManualEntry && !dishes[i]) {
                                const newDishes = [...dishes]
                                while (newDishes.length <= i) {
                                  newDishes.push({ slot: `menu_${newDishes.length + 1}`, name: '', description: '', price: 0, photoUrl: '' })
                                }
                                newDishes[i] = { ...newDishes[i], price: val }
                                setLocalDishes(newDishes)
                              } else {
                                updateDish(i, 'price', val)
                              }
                            }}
                            placeholder="12"
                            className="w-32 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-orange-300 focus:border-orange-400 outline-none"
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {!isSlotLoading && photo && (
                  <div className="mt-2 flex items-center gap-1 text-xs text-orange-600">
                    <Sparkles size={12} />
                    <span>Dicadangkan oleh AI</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between items-center mt-8">
        <button
          onClick={() => router.push('/onboarding/upload')}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          <ArrowLeft size={18} />
          Kembali
        </button>

        <button
          onClick={handleContinue}
          disabled={loading}
          className="px-6 py-3 bg-orange-500 text-white font-semibold rounded-xl hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Seterusnya — Pilih Gaya
        </button>
      </div>
    </>
  )
}
