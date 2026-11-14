/**
 * Search landing pages at /bina/<slug>.
 *
 * One page per thing a Malaysian business owner actually searches for
 * ("website restoran", "sistem order whatsapp", ...). Every page has its own
 * copy, features and questions — these are not one template with the noun
 * swapped, which search engines treat as doorway pages.
 *
 * Every claim here must be true of the product today. Prices: Permulaan
 * RM 5/bulan, Bisnes RM 49/bulan (see LandingPricing).
 */

export interface SeoFeature {
  title: string
  body: string
}

export interface SeoFaq {
  q: string
  a: string
}

export interface SeoPage {
  slug: string
  /** <title> — keep under ~60 characters. */
  title: string
  /** Meta description — keep under ~155 characters. */
  description: string
  eyebrow: string
  h1: string
  intro: string
  features: SeoFeature[]
  steps: string[]
  faqs: SeoFaq[]
  /** Short label used in footers and "related" links. */
  label: string
}

const COMMON_STEPS = [
  'Daftar akaun percuma dengan e-mel anda.',
  'Ceritakan kedai anda dalam Bahasa Melayu atau Manglish: nama, apa yang dijual, lokasi, waktu buka.',
  'AI bina website penuh dalam kira-kira 60 saat. Semak, tukar warna atau teks jika perlu.',
  'Terbitkan dengan RM 5 sebulan dan kongsi link namakedai.binaapp.my kepada pelanggan.',
]

export const SEO_PAGES: SeoPage[] = [
  {
    slug: 'website-restoran',
    label: 'Website restoran',
    title: 'Website Restoran dengan Menu & Order WhatsApp | BinaApp',
    description:
      'Bina website restoran dalam 60 saat: menu bergambar, pesanan terus ke WhatsApp, QR meja dan lokasi Google Maps. RM 5 sebulan, tiada komisen.',
    eyebrow: 'Untuk restoran',
    h1: 'Website restoran siap dalam 60 saat, RM 5 sebulan',
    intro:
      'Pelanggan mencari menu, harga dan waktu buka sebelum mereka datang. BinaApp membina website restoran anda daripada penerangan ringkas: menu bergambar, butang pesanan WhatsApp, peta lokasi dan waktu operasi, semuanya dalam satu halaman yang laju di telefon.',
    features: [
      {
        title: 'Menu bergambar dengan harga',
        body: 'Susun hidangan mengikut kategori, dengan saiz dan tambahan. Tiada gambar? AI boleh hasilkan gambar hidangan secara percuma.',
      },
      {
        title: 'Pesanan masuk terus ke WhatsApp',
        body: 'Pelanggan pilih hidangan dalam troli, tekan hantar, dan pesanan lengkap sampai di WhatsApp restoran anda.',
      },
      {
        title: 'QR untuk setiap meja',
        body: 'Cetak poster QR dalam warna website anda. Pelanggan imbas di meja dan pesan tanpa menunggu pelayan.',
      },
      {
        title: 'Lokasi dan waktu buka yang jelas',
        body: 'Peta Google Maps, nombor telefon dan lencana "Buka sekarang / Tutup" yang dikira daripada waktu operasi anda.',
      },
    ],
    steps: COMMON_STEPS,
    faqs: [
      {
        q: 'Berapa kos website restoran dengan BinaApp?',
        a: 'RM 5 sebulan untuk pelan Permulaan: satu website, subdomain percuma, gambar AI dan pesanan WhatsApp. Membina dan melihat pratonton adalah percuma; bayaran hanya diperlukan untuk menerbitkan.',
      },
      {
        q: 'Adakah BinaApp ambil komisen setiap pesanan?',
        a: 'Tidak. Anda bayar yuran bulanan tetap sahaja. Pesanan dan bayaran pelanggan terus kepada anda.',
      },
      {
        q: 'Saya tidak pandai IT. Boleh guna?',
        a: 'Boleh. Anda hanya menaip tentang kedai anda seperti bersembang. Menukar harga atau menu selepas itu dibuat dari telefon.',
      },
      {
        q: 'Boleh saya terus guna GrabFood atau Foodpanda?',
        a: 'Boleh. Website sendiri sesuai untuk pelanggan tetap yang sudah kenal kedai anda, supaya pesanan mereka tidak dikenakan komisen platform.',
      },
    ],
  },
  {
    slug: 'website-kedai-makan',
    label: 'Website kedai makan & warung',
    title: 'Website Kedai Makan & Warung, RM 5 Sebulan | BinaApp',
    description:
      'Website untuk kedai makan, warung dan gerai: senarai menu, harga, lokasi dan butang WhatsApp. Taip dalam Bahasa Melayu, siap dalam 60 saat.',
    eyebrow: 'Untuk kedai makan, warung dan gerai',
    h1: 'Website kedai makan anda, tanpa upah pereka',
    intro:
      'Warung nasi lemak, gerai burger atau kedai makan kampung juga layak ada website sendiri. Dengan BinaApp anda tidak perlu komputer, pereka atau kontrak: taip tentang kedai anda di telefon dan website terus siap, dengan link yang boleh dikongsi di WhatsApp dan Facebook.',
    features: [
      {
        title: 'Faham Bahasa Melayu dan Manglish',
        body: 'Tulis seperti anda bercakap: "kedai nasi lemak kat Shah Alam, buka pagi sampai tengah hari". AI faham dan susun kandungannya.',
      },
      {
        title: 'Satu link untuk semua',
        body: 'Letak link namakedai.binaapp.my di bio TikTok, Facebook dan status WhatsApp. Pelanggan nampak menu, harga dan lokasi tanpa bertanya.',
      },
      {
        title: 'Bahan cetak percuma',
        body: 'Menu A4, poster QR, kad setia "beli 9 percuma 1" dan poster cuti, semuanya dijana daripada maklumat kedai anda.',
      },
      {
        title: 'Gambar makanan daripada AI',
        body: 'Belum sempat ambil gambar? AI hasilkan gambar hidangan yang sepadan dengan menu anda, tanpa caj tambahan.',
      },
    ],
    steps: COMMON_STEPS,
    faqs: [
      {
        q: 'Kedai saya kecil sahaja. Berbaloi ke ada website?',
        a: 'Pelanggan baharu biasanya mencari menu dan lokasi dahulu. Satu link yang menjawab kedua-duanya mengurangkan soalan berulang di WhatsApp dan memudahkan orang datang.',
      },
      {
        q: 'Perlu komputer untuk bina website?',
        a: 'Tidak. Semuanya boleh dibuat dari telefon, termasuk menukar harga dan menu.',
      },
      {
        q: 'Ada kontrak atau caj tersembunyi?',
        a: 'Tiada kontrak. Bayaran RM 5 dibuat bulan ke bulan dan tiada komisen ke atas jualan anda.',
      },
      {
        q: 'Macam mana pelanggan buat pesanan?',
        a: 'Mereka pilih hidangan di website dan tekan butang pesan. Pesanan dihantar sebagai mesej WhatsApp kepada anda.',
      },
    ],
  },
  {
    slug: 'website-kafe',
    label: 'Website kafe',
    title: 'Website Kafe yang Cantik dalam 60 Saat | BinaApp',
    description:
      'Website kafe dengan reka bentuk sendiri: pilih mood, warna dan fon, tunjuk menu kopi dan pastri, terima pesanan WhatsApp. RM 5 sebulan.',
    eyebrow: 'Untuk kafe dan kedai kopi',
    h1: 'Website kafe yang nampak seperti jenama anda',
    intro:
      'Kafe dijual dengan suasana. BinaApp mereka website mengikut arahan anda sendiri, contohnya "gelap dan mewah dengan aksen emas" atau "cerah, minimalis, ala Jepun", kemudian mengisi menu, waktu buka dan lokasi supaya pelanggan terus tahu apa yang menanti.',
    features: [
      {
        title: 'Beri arahan kepada pereka AI',
        body: 'Terangkan mood yang anda mahu. AI memilih palet warna, pasangan fon dan susun atur yang sepadan sebelum membina halaman.',
      },
      {
        title: 'Tukar rupa serta-merta',
        body: 'Studio Reka Bentuk menyediakan 12 palet dan 28 pasangan fon, mod cerah atau gelap. Menukar warna adalah percuma dan segera.',
      },
      {
        title: 'Gaya doodle kartun',
        body: 'Untuk kafe yang santai, pilih gaya lakaran tangan dengan ilustrasi kartun bagi minuman dan pastri anda.',
      },
      {
        title: 'Poster untuk Instagram dan kaunter',
        body: 'Poster cerita 1080×1920 dengan QR, poster Wi-Fi dan poster ulasan Google dijana dalam warna kafe anda.',
      },
    ],
    steps: COMMON_STEPS,
    faqs: [
      {
        q: 'Boleh saya tentukan sendiri reka bentuk website kafe?',
        a: 'Boleh. Tulis arahan reka bentuk dalam ayat anda sendiri dan AI menjadikannya keutamaan. Selepas itu anda boleh menukar palet dan fon bila-bila masa.',
      },
      {
        q: 'Website ini sesuai dibuka dari Instagram?',
        a: 'Ya. Halaman dibina untuk telefon dahulu dan link pendeknya sesuai untuk bio Instagram dan TikTok.',
      },
      {
        q: 'Boleh pelanggan pesan untuk ambil sendiri?',
        a: 'Boleh. Pelanggan menyusun pesanan di website dan menghantarnya ke WhatsApp kafe anda untuk disahkan.',
      },
      {
        q: 'Berapa harganya?',
        a: 'RM 5 sebulan untuk pelan Permulaan. Membina dan pratonton adalah percuma.',
      },
    ],
  },
  {
    slug: 'website-bakeri',
    label: 'Website bakeri & kek',
    title: 'Website Bakeri & Tempahan Kek Online | BinaApp',
    description:
      'Website untuk bakeri dan peniaga kek dari rumah: katalog kek dengan harga, tempahan terus ke WhatsApp dan link mudah dikongsi. RM 5 sebulan.',
    eyebrow: 'Untuk bakeri dan peniaga kek dari rumah',
    h1: 'Katalog kek dan tempahan dalam satu link',
    intro:
      'Menjawab "ada kek apa, berapa harga?" berulang kali memakan masa. Dengan website BinaApp, pelanggan melihat semua kek, saiz dan harga sendiri, kemudian menghantar tempahan yang lengkap ke WhatsApp anda.',
    features: [
      {
        title: 'Katalog dengan saiz dan pilihan',
        body: 'Senaraikan setiap kek dengan pilihan saiz dan tambahan seperti topper atau perisa, lengkap dengan harga masing-masing.',
      },
      {
        title: 'Tempahan yang lengkap',
        body: 'Pesanan tiba di WhatsApp dengan item, saiz dan jumlah, jadi anda tidak perlu bertanya semula satu demi satu.',
      },
      {
        title: 'Baucar dan kad setia',
        body: 'Cetak baucar diskaun dan kad setia untuk diselit dalam kotak kek supaya pelanggan kembali.',
      },
      {
        title: 'Poster cuti',
        body: 'Tutup tempahan seketika? Jana poster "kami bercuti" dengan tarikh buka semula untuk dikongsi.',
      },
    ],
    steps: COMMON_STEPS,
    faqs: [
      {
        q: 'Saya berniaga dari rumah tanpa kedai. Boleh guna?',
        a: 'Boleh. Anda tidak perlukan premis. Website berfungsi sebagai katalog dan saluran tempahan anda.',
      },
      {
        q: 'Boleh tunjuk harga berbeza ikut saiz kek?',
        a: 'Boleh. Setiap item menyokong varian saiz dan tambahan dengan harga sendiri.',
      },
      {
        q: 'Macam mana pelanggan bayar?',
        a: 'Tempahan dihantar ke WhatsApp anda dan anda menguruskan bayaran dengan pelanggan seperti biasa. BinaApp tidak mengambil komisen.',
      },
      {
        q: 'Berapa kos bulanan?',
        a: 'RM 5 sebulan. Tiada kontrak dan tiada caj setiap tempahan.',
      },
    ],
  },
  {
    slug: 'website-salon',
    label: 'Website salon & tempahan',
    title: 'Website Salon dengan Tempahan Slot Online | BinaApp',
    description:
      'Website untuk salon, barber dan spa: senarai servis dengan harga, halaman tempahan slot ikut waktu operasi, dan butang WhatsApp. RM 5 sebulan.',
    eyebrow: 'Untuk salon, barber dan spa',
    h1: 'Website salon dengan tempahan slot',
    intro:
      'Pelanggan mahu tahu servis, harga dan bila anda ada kekosongan. BinaApp membina website salon anda dan menyediakan halaman tempahan di mana pelanggan memilih servis dan slot masa mengikut waktu operasi yang anda tetapkan.',
    features: [
      {
        title: 'Senarai servis dan harga',
        body: 'Paparkan setiap servis dengan tempoh dan harga supaya pelanggan tahu apa yang dijangka sebelum datang.',
      },
      {
        title: 'Tempahan ikut slot',
        body: 'Tetapkan waktu operasi, panjang slot dan bilangan pelanggan bagi setiap slot. Slot yang penuh tidak lagi ditawarkan.',
      },
      {
        title: 'Kad perniagaan dengan QR',
        body: 'Cetak kad perniagaan 10 sehelai dengan QR ke website anda untuk diberi kepada pelanggan.',
      },
      {
        title: 'Ulasan Google',
        body: 'Poster QR "beri kami 5 bintang" untuk kaunter memudahkan pelanggan yang berpuas hati meninggalkan ulasan.',
      },
    ],
    steps: COMMON_STEPS,
    faqs: [
      {
        q: 'Boleh pelanggan tempah slot sendiri?',
        a: 'Boleh. Halaman tempahan menunjukkan slot yang masih kosong berdasarkan waktu operasi dan kapasiti yang anda tetapkan.',
      },
      {
        q: 'BinaApp hanya untuk kedai makan?',
        a: 'Tidak. Ia paling banyak digunakan oleh perniagaan makanan, tetapi salon, barber, spa dan perniagaan servis lain juga disokong.',
      },
      {
        q: 'Boleh saya hadkan bilangan pelanggan setiap slot?',
        a: 'Boleh. Kapasiti setiap slot ditetapkan oleh anda.',
      },
      {
        q: 'Berapa harganya?',
        a: 'RM 5 sebulan untuk pelan Permulaan. Membina dan pratonton adalah percuma.',
      },
    ],
  },
  {
    slug: 'sistem-order-whatsapp',
    label: 'Sistem order WhatsApp',
    title: 'Sistem Order WhatsApp untuk Kedai Makan | BinaApp',
    description:
      'Terima pesanan tersusun di WhatsApp: pelanggan pilih menu dalam troli, pesanan lengkap sampai sebagai satu mesej. Tiada komisen, RM 5 sebulan.',
    eyebrow: 'Pesanan melalui WhatsApp',
    h1: 'Sistem order WhatsApp tanpa komisen',
    intro:
      'Mengambil pesanan melalui chat biasa mudah tersilap: item tertinggal, kuantiti salah, alamat ditanya dua kali. BinaApp memberi pelanggan menu dengan troli, kemudian menghantar pesanan yang sudah lengkap ke WhatsApp anda sebagai satu mesej.',
    features: [
      {
        title: 'Troli, bukan taip manual',
        body: 'Pelanggan memilih item, saiz dan tambahan daripada menu. Jumlah dikira secara automatik.',
      },
      {
        title: 'Satu mesej yang lengkap',
        body: 'Pesanan tiba dengan senarai item, kuantiti dan jumlah, sedia untuk anda sahkan.',
      },
      {
        title: 'QR "imbas untuk pesan"',
        body: 'Cetak QR pesanan WhatsApp, termasuk satu bagi setiap meja untuk makan di kedai.',
      },
      {
        title: 'Kod baucar dan mata setia',
        body: 'Cipta kod baucar untuk promosi dan beri mata setia kepada pelanggan yang kerap memesan.',
      },
    ],
    steps: COMMON_STEPS,
    faqs: [
      {
        q: 'Perlu WhatsApp Business API?',
        a: 'Tidak. Pesanan dihantar ke nombor WhatsApp biasa atau WhatsApp Business anda melalui link pesanan.',
      },
      {
        q: 'Ada caj setiap pesanan?',
        a: 'Tiada. Hanya yuran bulanan tetap RM 5. Tiada komisen ke atas jualan.',
      },
      {
        q: 'Boleh guna untuk makan di kedai?',
        a: 'Boleh. Letak QR di setiap meja; pesanan yang masuk menyatakan nombor meja.',
      },
      {
        q: 'Bagaimana dengan penghantaran?',
        a: 'Pelan Bisnes (RM 49 sebulan) menambah zon penghantaran, papan pemuka pesanan dan penjejakan GPS untuk rider anda sendiri.',
      },
    ],
  },
  {
    slug: 'delivery-tanpa-komisen',
    label: 'Delivery tanpa komisen',
    title: 'Sistem Delivery Sendiri Tanpa Komisen | BinaApp',
    description:
      'Urus penghantaran dengan rider sendiri: zon dan caj penghantaran, papan pemuka pesanan, penjejakan GPS masa nyata. RM 49 sebulan, tiada komisen.',
    eyebrow: 'Untuk restoran yang ada rider sendiri',
    h1: 'Sistem delivery sendiri, RM 49 sebulan, tiada komisen',
    intro:
      'Jika anda sudah ada rider, komisen platform penghantaran ialah kos yang boleh dielakkan untuk pelanggan tetap. Pelan Bisnes BinaApp memberi anda sistem penghantaran penuh di bawah jenama sendiri, dengan satu harga bulanan yang tetap.',
    features: [
      {
        title: 'Zon dan caj penghantaran',
        body: 'Lukis kawasan penghantaran di atas peta dan tetapkan caj bagi setiap zon.',
      },
      {
        title: 'Papan pemuka pesanan',
        body: 'Lihat setiap pesanan daripada diterima hingga dihantar, dan berbual dengan pelanggan dari tempat yang sama.',
      },
      {
        title: 'Rider sendiri dengan GPS',
        body: 'Rider menggunakan aplikasi web di telefon mereka. Anda dan pelanggan boleh menjejak penghantaran secara masa nyata.',
      },
      {
        title: 'Pelanggan milik anda',
        body: 'Pesanan datang terus kepada anda, jadi senarai pelanggan dan hubungan dengan mereka kekal dengan kedai anda.',
      },
    ],
    steps: [
      'Bina dan terbitkan website kedai anda dengan menu.',
      'Naik taraf ke pelan Bisnes dan lukis zon penghantaran anda.',
      'Daftarkan rider anda; mereka log masuk ke aplikasi rider di telefon.',
      'Terima pesanan, tugaskan rider dan jejak penghantaran dari papan pemuka.',
    ],
    faqs: [
      {
        q: 'Berapa ramai rider boleh didaftarkan?',
        a: 'Pelan Bisnes merangkumi 10 rider. Slot tambahan boleh dibeli jika perlu.',
      },
      {
        q: 'Adakah BinaApp menyediakan rider?',
        a: 'Tidak. Sistem ini untuk kedai yang mempunyai rider sendiri. Ia menggantikan aplikasi dan komisen, bukan tenaga penghantar.',
      },
      {
        q: 'Betul tiada komisen langsung?',
        a: 'Ya. Anda membayar RM 49 sebulan tanpa mengira jumlah pesanan.',
      },
      {
        q: 'Boleh pelanggan jejak pesanan mereka?',
        a: 'Boleh. Pelanggan mendapat halaman jejakan yang menunjukkan status pesanan dan kedudukan rider.',
      },
    ],
  },
  {
    slug: 'menu-qr',
    label: 'Menu QR untuk meja',
    title: 'Menu QR Kod untuk Restoran & Kafe | BinaApp',
    description:
      'Menu digital dengan QR untuk setiap meja: pelanggan imbas, lihat menu bergambar dan pesan. Poster QR sedia cetak. RM 5 sebulan.',
    eyebrow: 'Menu digital',
    h1: 'Menu QR untuk setiap meja',
    intro:
      'Menu bercetak perlu dicetak semula setiap kali harga berubah. Dengan menu QR BinaApp, pelanggan mengimbas kod di meja dan melihat menu terkini di telefon mereka, dan anda menukar harga dalam beberapa saat.',
    features: [
      {
        title: 'Satu kod bagi setiap meja',
        body: 'Setiap QR membawa nombor mejanya, jadi pesanan yang masuk terus menunjukkan dari meja mana.',
      },
      {
        title: 'Poster sedia cetak',
        body: 'Poster A4 dijana dalam warna website anda. Cetak, potong dan letak di meja.',
      },
      {
        title: 'Harga sentiasa terkini',
        body: 'Tukar harga atau tanda item habis dari telefon; menu di semua meja berubah serentak.',
      },
      {
        title: 'Menu bercetak pun ada',
        body: 'Perlukan salinan kertas? Jana menu A4 sedia cetak daripada data menu yang sama.',
      },
    ],
    steps: COMMON_STEPS,
    faqs: [
      {
        q: 'Perlu pelanggan muat turun aplikasi?',
        a: 'Tidak. Mengimbas QR membuka menu terus dalam pelayar telefon.',
      },
      {
        q: 'Boleh pelanggan pesan dari meja?',
        a: 'Boleh. Mereka memilih hidangan dan menghantar pesanan, yang tiba bersama nombor meja.',
      },
      {
        q: 'QR perlu dicetak semula bila menu berubah?',
        a: 'Tidak. Kod yang sama sentiasa membuka menu terkini.',
      },
      {
        q: 'Berapa kosnya?',
        a: 'Menu QR termasuk dalam pelan Permulaan, RM 5 sebulan.',
      },
    ],
  },
]

export function getSeoPage(slug: string): SeoPage | undefined {
  return SEO_PAGES.find((p) => p.slug === slug)
}

/** Other pages to link to from a given page (internal links for crawlers and readers). */
export function relatedSeoPages(slug: string, limit = 4): SeoPage[] {
  return SEO_PAGES.filter((p) => p.slug !== slug).slice(0, limit)
}
