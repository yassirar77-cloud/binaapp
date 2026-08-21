const features = [
  {
    num: '01',
    title: 'AI yang faham Bahasa Melayu',
    body: "Cakap macam bercakap dengan kawan: 'Kedai mamak, ada nasi kandar, roti canai, buka 24 jam.' Dalam 60 saat, AI siapkan website penuh dengan menu, gambar auto, dan butang pesanan. Tiada coding, tiada template boring.",
  },
  {
    num: '02',
    title: 'Tempahan melalui WhatsApp',
    body: 'Setiap website ada butang WhatsApp. Pelanggan buat tempahan terus ke WhatsApp kedai anda. Tiada orang tengah, tiada komisen.',
  },
  {
    num: '03',
    title: 'GPS penghantar langsung',
    body: 'Tugaskan penghantar sendiri. Pelanggan boleh lihat GPS langsung di peta. Tak perlu lagi soal "bila nak sampai?"',
  },
  {
    num: '04',
    title: 'Zon penghantaran tersendiri',
    body: 'Anda tetapkan kawasan dan yuran penghantaran sendiri. Shah Alam RM 5. KL RM 8. Ikut peraturan anda, bukan orang lain.',
  },
]

export default function LandingFeatures() {
  return (
    <section id="ciri" className="bg-oat-200 py-20 lg:py-28 px-8">
      <div className="max-w-[1200px] mx-auto">

        {/* Eyebrow */}
        <div className="font-geist text-xs tracking-[.12em] uppercase text-clay-600 font-semibold mb-3">
          — Ciri-ciri
        </div>

        {/* Section headline — serif display */}
        <h2 className="font-display font-medium text-3xl sm:text-4xl lg:text-[52px] leading-[1.08] tracking-[-0.02em] text-carbon-900 mb-14 max-w-[760px]">
          Semua yang restoran perlu.<br />
          Takde yang anda tak perlu.
        </h2>

        {/* Feature cards — 1 col on mobile, 2 cols on desktop */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {features.map((f) => (
            <div
              key={f.num}
              className="bg-oat-50 rounded-2xl p-8 border border-oat-400/60 shadow-card-warm hover:shadow-lift-warm hover:-translate-y-0.5 transition-all duration-200"
            >
              <div className="font-geist-mono text-[11px] tracking-[.12em] text-clay-500 mb-5">
                {f.num}
              </div>
              <h3 className="font-display font-medium text-xl sm:text-2xl lg:text-[26px] tracking-[-0.01em] text-carbon-900 mb-2.5">
                {f.title}
              </h3>
              <p className="font-geist text-[15px] leading-relaxed text-carbon-400">
                {f.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
