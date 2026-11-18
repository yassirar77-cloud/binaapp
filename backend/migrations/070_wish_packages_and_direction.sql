-- Migration 070: mysyg.com wishes — video length packages and the sender's
-- own direction
--
-- wan3.0-video is billed per second of output, so the clip's length is now
-- something the sender chooses and pays for:
--
--   package        which package was bought ('ringkas' 10 s, 'manis' 20 s,
--                  'sinematik' 30 s — see PACKAGES in services/wishes.py).
--                  Free text on purpose: the set of packages is code, and a
--                  CHECK here would have to change with every new one.
--   video_seconds  the length that package meant AT PURCHASE. Rendered from
--                  this, not from today's package table, so a later change
--                  to a package never shortens a clip someone already paid
--                  for.
--
-- And the sender may say what should happen in the clip:
--
--   video_direction  their own words, as typed (shown back to them only).
--   video_scene      the screened English scene made from those words
--                    (services/wish_direction.py). This, and nothing else
--                    the sender wrote, is what reaches the video model.
--
-- Existing wishes are 'ringkas' with NULL seconds (the code falls back to
-- the package's length) and no direction: nothing about them changes.

ALTER TABLE public.wishes
    ADD COLUMN IF NOT EXISTS package         TEXT NOT NULL DEFAULT 'ringkas',
    ADD COLUMN IF NOT EXISTS video_seconds   INTEGER,
    ADD COLUMN IF NOT EXISTS video_direction TEXT,
    ADD COLUMN IF NOT EXISTS video_scene     TEXT;

ALTER TABLE public.wishes DROP CONSTRAINT IF EXISTS wishes_video_seconds_check;
ALTER TABLE public.wishes
    ADD CONSTRAINT wishes_video_seconds_check
    CHECK (video_seconds IS NULL OR video_seconds BETWEEN 2 AND 30);

ALTER TABLE public.wishes DROP CONSTRAINT IF EXISTS wishes_video_direction_check;
ALTER TABLE public.wishes
    ADD CONSTRAINT wishes_video_direction_check
    CHECK (video_direction IS NULL OR char_length(video_direction) <= 200);
