'use client'

import { useState } from 'react'

interface MenuItem {
  name: string
  price: string
  description: string
}

export default function MenuDesigner() {
  const [businessName, setBusinessName] = useState('')
  const [menuItems, setMenuItems] = useState<MenuItem[]>([
    { name: '', price: '', description: '' }
  ])
  const [size, setSize] = useState('A4')
  const [loading, setLoading] = useState(false)
  const [pdfUrl, setPdfUrl] = useState('')

  function addMenuItem() {
    setMenuItems([...menuItems, { name: '', price: '', description: '' }])
  }

  function updateMenuItem(index: number, field: keyof MenuItem, value: string) {
    const updated = [...menuItems]
    updated[index][field] = value
    setMenuItems(updated)
  }

  async function generateMenu() {
    if (!businessName || menuItems.length === 0) {
      alert('Please enter business name and at least one menu item')
      return
    }

    setLoading(true)

    try {
      const res = await fetch('http://localhost:8000/api/generate-menu', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business_name: businessName,
          items: menuItems,
          size: size,
          style: 'modern'
        })
      })

      const data = await res.json()

      if (data.success) {
        setPdfUrl(data.pdf_url)
      } else {
        alert('Menu generation failed: ' + data.error)
      }
    } catch (error) {
      console.error('Error:', error)
      alert('Failed to generate menu')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '36px', marginBottom: '10px' }}>🍽️ Menu Designer</h1>
      <p style={{ color: '#666', marginBottom: '40px', fontSize: '16px' }}>
        Create professional print-ready menus for your restaurant
      </p>

      {/* Business Name */}
      <div style={{ marginBottom: '30px' }}>
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold', fontSize: '16px' }}>
          Business Name:
        </label>
        <input
          value={businessName}
          onChange={(e) => setBusinessName(e.target.value)}
          placeholder="e.g. Kedai Nasi Kandar Khulafa"
          style={{
            width: '100%',
            padding: '12px',
            fontSize: '16px',
            border: '2px solid #ddd',
            borderRadius: '8px'
          }}
        />
      </div>

      {/* Menu Size */}
      <div style={{ marginBottom: '30px' }}>
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold', fontSize: '16px' }}>
          Menu Size:
        </label>
        <select
          value={size}
          onChange={(e) => setSize(e.target.value)}
          style={{
            padding: '12px',
            fontSize: '16px',
            border: '2px solid #ddd',
            borderRadius: '8px',
            width: '100%'
          }}
        >
          <option value="A4">A4 (210mm x 297mm) - Table Menu</option>
          <option value="A5">A5 (148mm x 210mm) - Small Menu</option>
          <option value="banner">Banner (3ft x 2ft) - Shop Display</option>
        </select>
      </div>

      {/* Menu Items */}
      <div style={{ marginBottom: '30px' }}>
        <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold', fontSize: '16px' }}>
          Menu Items:
        </label>

        {menuItems.map((item, index) => (
          <div key={index} style={{
            padding: '20px',
            background: '#f9fafb',
            borderRadius: '8px',
            marginBottom: '15px'
          }}>
            <h4 style={{ marginBottom: '15px', color: '#667eea' }}>Item {index + 1}</h4>

            <input
              placeholder="Item Name (e.g. Nasi Ayam)"
              value={item.name}
              onChange={(e) => updateMenuItem(index, 'name', e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                marginBottom: '10px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            />

            <input
              placeholder="Price (e.g. 8.00)"
              value={item.price}
              onChange={(e) => updateMenuItem(index, 'price', e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                marginBottom: '10px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            />

            <textarea
              placeholder="Description (optional)"
              value={item.description}
              onChange={(e) => updateMenuItem(index, 'description', e.target.value)}
              style={{
                width: '100%',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                height: '60px',
                fontSize: '14px',
                fontFamily: 'inherit'
              }}
            />
          </div>
        ))}

        <button
          onClick={addMenuItem}
          style={{
            padding: '10px 20px',
            background: '#667eea',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: 'bold',
            fontSize: '14px'
          }}
        >
          + Add Item
        </button>
      </div>

      {/* Generate Button */}
      <button
        onClick={generateMenu}
        disabled={loading}
        style={{
          width: '100%',
          padding: '15px',
          fontSize: '18px',
          background: loading ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '10px',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontWeight: 'bold'
        }}
      >
        {loading ? '⏳ Generating Menu...' : '✨ Generate Menu PDF'}
      </button>

      {/* Result */}
      {pdfUrl && (
        <div style={{
          marginTop: '40px',
          padding: '30px',
          background: '#f0fdf4',
          borderRadius: '15px',
          border: '2px solid #86efac'
        }}>
          <h2 style={{ color: '#166534', marginBottom: '20px', fontSize: '24px' }}>
            🎉 Menu Generated Successfully!
          </h2>

          <a
            href={pdfUrl}
            download
            target="_blank"
            style={{
              display: 'inline-block',
              padding: '15px 30px',
              background: '#16a34a',
              color: 'white',
              textDecoration: 'none',
              borderRadius: '8px',
              fontWeight: 'bold',
              fontSize: '16px'
            }}
          >
            📥 Download PDF Menu
          </a>

          <p style={{ marginTop: '20px', color: '#15803d', fontSize: '14px' }}>
            💡 Tip: Print this at your local print shop for ~RM3-5
          </p>
        </div>
      )}
    </div>
  )
}
