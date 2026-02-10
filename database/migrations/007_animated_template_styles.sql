-- Migration: Add template_style column to websites table
-- Stores the selected animated template style key (e.g., 'particle-globe', 'aurora')
-- for the hero section animation on the restaurant's public website.

ALTER TABLE websites ADD COLUMN IF NOT EXISTS template_style TEXT DEFAULT 'default';

-- Create a lookup table for animated template definitions
CREATE TABLE IF NOT EXISTS website_templates (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  name_ms TEXT NOT NULL,
  style_key TEXT NOT NULL UNIQUE,
  categories TEXT[] NOT NULL DEFAULT '{}',
  is_premium BOOLEAN DEFAULT false,
  description TEXT,
  description_ms TEXT,
  preview_config JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Seed the 9 animated template styles
INSERT INTO website_templates (name, name_ms, style_key, categories, is_premium, description, description_ms) VALUES
  ('Particle Globe', 'Glob Zarah', 'particle-globe', ARRAY['premium', 'gelap'], true, '3D rotating particle sphere', 'Sfera zarah 3D berputar'),
  ('Gradient Wave', 'Gelombang Gradien', 'gradient-wave', ARRAY['gelap', 'ceria'], false, 'Purple/blue/pink gradient waves', 'Gelombang gradien ungu/biru/merah jambu'),
  ('Floating Food', 'Makanan Terapung', 'floating-food', ARRAY['gelap', 'ceria'], false, 'Floating food emoji in glass cards', 'Emoji makanan terapung dalam kad kaca'),
  ('Neon Grid', 'Grid Neon', 'neon-grid', ARRAY['gelap', 'premium'], true, 'Perspective CSS grid with neon glow', 'Grid CSS perspektif dengan cahaya neon'),
  ('Morphing Blob', 'Blob Berubah', 'morphing-blob', ARRAY['gelap', 'minimal'], false, 'Organic blob shape morphing', 'Bentuk organik berubah'),
  ('Matrix Code', 'Kod Matrix', 'matrix-code', ARRAY['gelap'], false, 'Falling code rain', 'Hujan kod jatuh'),
  ('Aurora Borealis', 'Aurora', 'aurora', ARRAY['premium', 'gelap', 'ceria'], true, 'Aurora bands with twinkling stars', 'Jalur aurora dengan bintang berkelip'),
  ('Spotlight', 'Sorotan', 'spotlight', ARRAY['gelap', 'minimal'], false, 'Moving spotlight with icon circles', 'Sorotan bergerak dengan bulatan ikon'),
  ('Parallax Layers', 'Lapisan Paralaks', 'parallax-layers', ARRAY['premium', 'ceria'], true, 'Floating circles with parallax animation', 'Bulatan terapung dengan animasi paralaks')
ON CONFLICT (style_key) DO NOTHING;

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_websites_template_style ON websites(template_style);
CREATE INDEX IF NOT EXISTS idx_website_templates_style_key ON website_templates(style_key);
