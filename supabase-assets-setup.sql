-- BinaApp Assets Storage Bucket Setup
-- Run this in your Supabase SQL Editor

-- Create assets bucket for user uploads (logo, images, fonts)
INSERT INTO storage.buckets (id, name, public)
VALUES ('assets', 'assets', true)
ON CONFLICT (id) DO NOTHING;

-- Allow authenticated users to upload to assets bucket
CREATE POLICY "Authenticated users can upload assets"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'assets');

-- Allow authenticated users to update their own assets
CREATE POLICY "Users can update own assets"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'assets');

-- Allow authenticated users to delete their own assets
CREATE POLICY "Users can delete own assets"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'assets');

-- Allow public read access to all assets
CREATE POLICY "Public read access for assets"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'assets');

-- Verify setup
SELECT id, name, public FROM storage.buckets WHERE id = 'assets';
