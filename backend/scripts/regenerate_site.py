#!/usr/bin/env python3
"""Regenerate a site through the deployed API with a fixture menu, then
verify the result against the fixture.

Usage (after the menu-fidelity branch is deployed):

    python scripts/regenerate_site.py --fixture tests/fixtures/ayam_gepuk_panglima_menu.json \
        --api https://binaapp-backend.onrender.com --user-id <owner uuid> --email <owner email> \
        [--hero-url <cloudinary url>] [--logo-url <cloudinary url>] [--out /tmp/regen.html]

It POSTs /api/generate/start with the fixture's items (categories kept),
polls /api/generate/status/<job_id> until the job completes, saves the
HTML and runs scripts/verify_site_menu.py's checks on it. It never
publishes: publishing to the live subdomain is a separate, deliberate
step in the create page.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_site_menu import verify  # noqa: E402

DESCRIPTION = (
    "Ayam Gepuk Panglima ialah restoran ayam gepuk di Kota Bayu Emas, Klang. Resepi Panglima — ayam goreng rangup "
    "digepuk atas sambal pedas buatan sendiri, dihidang dengan nasi putih panas, tauhu, tempe, kubis dan timun. "
    "Slogan kami: Makin Pedas, Rasa Makin Padu.\n\nPilih tahap kepedasan anda: Level 1 (Spicy), Level 2 (Hot) atau "
    "Level 3 (Extra Hot).\n\nSet bermula RM12.50. Signature kami ialah Set Panglima Signature — paling lengkap dengan "
    "tauhu, tempe, kubis goreng dan telur mata. Ada juga Set Panglima Krispy, set sotong & udang krispy, sambal gajus, "
    "minuman special Bali Blues & Es Jeruk, serta menu kanak-kanak.\n\nMakan di kedai: FREE refill nasi & sambal. "
    "Take away: caj tambahan RM2.00.\n\nSesuai untuk makan tengah hari, keluarga dan geng kerja sekitar Kota Bayu Emas "
    "& Klang. Cari kedai kuning terang dengan signboard Ayam Gepuk Panglima!\n\n"
    "Alamat: No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor.\nWhatsApp: 012-697 3105"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--api", default="https://binaapp-backend.onrender.com")
    # The backend takes the merchant from this token (the user_id/email in
    # the body are ignored): log in as the merchant, or as an admin, and pass
    # the access token. BINAAPP_TOKEN in the environment works too.
    ap.add_argument("--token", default=os.getenv("BINAAPP_TOKEN", ""), help="Bearer token of the account to build as")
    ap.add_argument("--hero-url", default="")
    ap.add_argument("--logo-url", default="")
    ap.add_argument("--out", default="regenerated.html")
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    items = [{"name": i["name"], "price": i["price"], "category": i.get("category", "")} for i in fixture["menu_items"]]
    body = {
        "description": DESCRIPTION,
        "business_description": DESCRIPTION,
        "business_name": fixture["business_name"],
        "business_type": "food",
        "language": "ms",
        "whatsapp_number": "0126973105",
        "address": "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor",
        "features": {"whatsapp": True, "googleMap": True, "priceList": True, "operatingHours": True, "gallery": True,
                     "contactForm": False, "socialMedia": False, "deliverySystem": False},
        "menu_items": items,
        "gallery_metadata": [{"url": "", "name": i["name"], "price": i["price"]} for i in items],
        "images": ([{"url": args.hero_url, "name": "Hero Image"}] if args.hero_url else None),
        "image_choice": "upload" if args.hero_url else "ai",
        "color_mode": "light",
        "design_style": "bold",
        "logo": args.logo_url or None,
        "multi_style": False,
    }
    if not args.token:
        print("a --token (or BINAAPP_TOKEN) is required: /api/generate/start builds as the token's account")
        return 2
    with httpx.Client(timeout=60) as client:
        r = client.post(f"{args.api}/api/generate/start", json=body, headers={"Authorization": f"Bearer {args.token}"})
        r.raise_for_status()
        job_id = r.json()["job_id"]
        print(f"job {job_id} started")
        deadline = time.time() + args.timeout
        while time.time() < deadline:
            time.sleep(10)
            st = client.get(f"{args.api}/api/generate/status/{job_id}").json()
            print(f"  {st.get('status')} {st.get('progress')}%")
            if st.get("status") in ("completed", "failed"):
                break
        if st.get("status") != "completed":
            print("generation did not complete:", st.get("error"))
            return 2
        html = st.get("html") or ""
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"saved {len(html)} chars to {args.out}")
    print(json.dumps(st.get("validation") or {}, indent=1)[:2000])
    report = verify(html, fixture)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
