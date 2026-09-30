/**
 * The TikTok composer rules — straight from TikTok's Content Sharing
 * Guidelines for Direct Post — checked without a browser.
 */
import { describe, expect, it } from 'vitest';
import {
  EMPTY_DRAFT,
  brandedContentDisabled,
  checkDraft,
  declarationText,
  describeStatus,
  errorFromBody,
  privacyOptionDisabled,
  privacyOptions,
  toPostRequest,
  type CreatorInfo,
  type PostDraft,
  type TikTokPost,
} from './tiktok';

const LIMITS = { video_title_max: 2200, photo_title_max: 90, photo_description_max: 4000, max_photos: 35 };

const INFO: CreatorInfo = {
  creator_avatar_url: null,
  creator_username: 'binaapp.my',
  creator_nickname: 'BinaApp',
  privacy_level_options: ['PUBLIC_TO_EVERYONE', 'MUTUAL_FOLLOW_FRIENDS', 'SELF_ONLY'],
  comment_disabled: false,
  duet_disabled: true,
  stitch_disabled: false,
  max_video_post_duration_sec: 600,
  audited: false,
};

const draft = (over: Partial<PostDraft> = {}): PostDraft => ({ ...EMPTY_DRAFT, ...over });

describe('privacy dropdown', () => {
  it('lists only the options creator_info returned, in canonical order', () => {
    expect(privacyOptions(INFO)).toEqual(['PUBLIC_TO_EVERYONE', 'MUTUAL_FOLLOW_FRIENDS', 'SELF_ONLY']);
    expect(privacyOptions({ ...INFO, privacy_level_options: ['SELF_ONLY', 'FOLLOWER_OF_CREATOR'] })).toEqual([
      'FOLLOWER_OF_CREATOR',
      'SELF_ONLY',
    ]);
    expect(privacyOptions(null)).toEqual([]);
  });

  it('has no default selection', () => {
    expect(EMPTY_DRAFT.privacy_level).toBeNull();
    expect(checkDraft(draft(), INFO, LIMITS, true).problems).toContain('Choose who can view this post.');
  });

  it('greys out "Only you" while Branded content is ticked, and vice versa', () => {
    const d = draft({ disclose_commercial: true, branded_content: true });
    expect(privacyOptionDisabled('SELF_ONLY', d)).toBe(true);
    expect(privacyOptionDisabled('PUBLIC_TO_EVERYONE', d)).toBe(false);
    expect(brandedContentDisabled(draft({ privacy_level: 'SELF_ONLY' }))).toBe(true);
    expect(brandedContentDisabled(draft({ privacy_level: 'PUBLIC_TO_EVERYONE' }))).toBe(false);
  });
});

describe('interaction toggles', () => {
  it('start off and map to TikTok disable_* fields', () => {
    expect(EMPTY_DRAFT.allow_comment).toBe(false);
    expect(EMPTY_DRAFT.allow_duet).toBe(false);
    expect(EMPTY_DRAFT.allow_stitch).toBe(false);
    const body = toPostRequest(draft({ privacy_level: 'SELF_ONLY', allow_comment: true }));
    expect(body.disable_comment).toBe(false);
    expect(body.disable_duet).toBe(true);
    expect(body.disable_stitch).toBe(true);
  });
});

describe('commercial content disclosure', () => {
  it('is off by default and sends no brand toggles', () => {
    expect(EMPTY_DRAFT.disclose_commercial).toBe(false);
    const body = toPostRequest(draft({ privacy_level: 'PUBLIC_TO_EVERYONE', your_brand: true }));
    expect(body.brand_organic_toggle).toBe(false);
    expect(body.brand_content_toggle).toBe(false);
  });

  it('blocks posting until Your brand or Branded content is picked', () => {
    const d = draft({ privacy_level: 'PUBLIC_TO_EVERYONE', disclose_commercial: true });
    expect(checkDraft(d, INFO, LIMITS, true).problems).toContain(
      'You need to indicate if your content promotes yourself, a third party, or both.',
    );
    expect(checkDraft({ ...d, your_brand: true }, INFO, LIMITS, true).ok).toBe(true);
  });

  it('never lets branded content go out as Only you', () => {
    const d = draft({ privacy_level: 'SELF_ONLY', disclose_commercial: true, branded_content: true });
    expect(checkDraft(d, INFO, LIMITS, true).problems).toContain('Branded content visibility cannot be set to private.');
  });

  it('picks the right declaration sentence', () => {
    expect(declarationText(draft()).text).toBe("By posting, you agree to TikTok's Music Usage Confirmation.");
    expect(declarationText(draft({ disclose_commercial: true, your_brand: true })).brandedPolicy).toBe(false);
    expect(declarationText(draft({ disclose_commercial: true, branded_content: true })).text).toBe(
      "By posting, you agree to TikTok's Branded Content Policy and Music Usage Confirmation.",
    );
    expect(declarationText(draft({ disclose_commercial: true, your_brand: true, branded_content: true })).brandedPolicy).toBe(true);
  });
});

describe('limits', () => {
  it('caps captions in UTF-16 units and checks duration against creator_info', () => {
    const ok = draft({ privacy_level: 'SELF_ONLY', title: '😀'.repeat(1100) });
    expect(checkDraft(ok, INFO, LIMITS, true).ok).toBe(true);
    const long = draft({ privacy_level: 'SELF_ONLY', title: '😀'.repeat(1101) });
    expect(checkDraft(long, INFO, LIMITS, true).ok).toBe(false);
    const tooLong = draft({ privacy_level: 'SELF_ONLY', duration_sec: 601 });
    expect(checkDraft(tooLong, INFO, LIMITS, true).problems[0]).toMatch(/up to 600s/);
  });

  it('inbox uploads need media but no privacy choice', () => {
    expect(checkDraft(draft({ mode: 'inbox' }), INFO, LIMITS, true).ok).toBe(true);
    expect(checkDraft(draft({ mode: 'inbox' }), INFO, LIMITS, false).ok).toBe(false);
  });
});

describe('status + errors', () => {
  const post = (over: Partial<TikTokPost>): TikTokPost => ({
    id: 'p1',
    mode: 'direct',
    media_type: 'video',
    title: null,
    status: 'processing',
    tiktok_status: null,
    fail_reason: null,
    error: null,
    publish_id: 'v_pub',
    uploaded_bytes: 0,
    total_bytes: 0,
    public_post_ids: null,
    privacy_level: 'SELF_ONLY',
    post_info: {},
    created_at: '',
    updated_at: '',
    finished_at: null,
    ...over,
  });

  it('describes each state for the admin', () => {
    expect(describeStatus(post({ status: 'uploading', uploaded_bytes: 5, total_bytes: 10 })).label).toBe(
      'Uploading to TikTok… 50%',
    );
    expect(describeStatus(post({ status: 'published' })).label).toBe('Posted (visible only to you)');
    expect(describeStatus(post({ status: 'published', privacy_level: 'PUBLIC_TO_EVERYONE' })).label).toBe('Posted (Everyone)');
    expect(describeStatus(post({ status: 'failed', error: 'nope' }))).toEqual({ label: 'nope', tone: 'err' });
    expect(describeStatus(post({ status: 'sent_to_inbox' })).tone).toBe('ok');
  });

  it('unwraps FastAPI error envelopes', () => {
    const e = errorFromBody(422, { detail: { error: 'validation', message: 'Choose privacy.' } });
    expect(e.code).toBe('validation');
    expect(e.message).toBe('Choose privacy.');
    expect(errorFromBody(401, { detail: 'Session expired' }).message).toBe('Session expired');
    expect(errorFromBody(500, {}).message).toBe('Request failed (500)');
  });
});
