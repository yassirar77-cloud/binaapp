/**
 * BinaApp Privacy Policy v3.0 — Bahasa Malaysia (prevailing version)
 *
 * Source-of-truth content for the BM Privacy Policy. Consumed by the
 * policy rendering components built in Step 3e. Per s23
 * (`prevailingLanguage`), the BM version controls if there is any
 * conflict with the EN translation built in Step 3d.
 *
 * Effective: 21 Mei 2026. Supersedes v2.0 (31 Januari 2025) and v1.0.
 *
 * Maintenance notes:
 * - When updating, bump `version`, update `lastUpdated`, append a new
 *   changelog entry. Do NOT silently edit historical changelog rows.
 * - Word count drives `estimatedReadingMinutes` (200 wpm BM average).
 * - Tables (AI vendors, retention) live as structured arrays on the
 *   relevant section; the renderer maps them to HTML tables.
 */

export type PIIRisk = 'warning' | 'safe';

export type AIVendorRow = {
  feature: string;
  vendor: string;
  region: string;
  dataSent: string;
  piiRisk: PIIRisk;
  piiNote: string;
  consentStatus: string;
};

export type RetentionRow = {
  dataType: string;
  period: string;
};

export type PolicySection = {
  id: string;
  title: string;
  content: string;
  aiVendorTable?: AIVendorRow[];
  retentionTable?: RetentionRow[];
};

export type ChangelogEntry = {
  version: string;
  date: string;
  changes: string[];
};

export type PolicyContact = {
  company: string;
  ssm: string;
  dpoEmail: string;
  supportEmail: string;
  pdpDeptPhone: string;
  pdpDeptWebsite: string;
};

export type PrivacyPolicy = {
  version: string;
  effectiveDate: string;
  lastUpdated: string;
  estimatedReadingMinutes: number;
  executiveSummary: { title: string; content: string };
  introduction: { title: string; content: string };
  sections: PolicySection[];
  changelog: ChangelogEntry[];
  contact: PolicyContact;
  prevailingLanguage: { title: string; content: string };
};

export const privacyPolicyBM: PrivacyPolicy = {
  version: '3.0',
  effectiveDate: '21 Mei 2026',
  lastUpdated: '21 Mei 2026',
  estimatedReadingMinutes: 32,

  executiveSummary: {
    title: 'Ringkasan 1-Minit',
    content: `Ringkasan ini adalah untuk rujukan pantas sahaja dan **bukan** menggantikan Polisi penuh di bawah. Sila baca seksyen-seksyen yang berkaitan untuk butiran lengkap.

- **Siapa kami:** BinaApp ialah platform pembina laman web AI untuk perniagaan makanan dan minuman (F&B) di Malaysia, dimiliki dan dikendalikan oleh **Ezy Work Asia Solution** (No. SSM: 002944700-D).
- **Data apa kami kumpul:** Data akaun anda (emel, nama perniagaan, nombor telefon), data penggunaan dashboard, data pesanan customer yang anda input, data lokasi GPS penghantar semasa penghantaran aktif, dan rekod transaksi langganan.
- **Untuk apa:** Untuk menyediakan perkhidmatan platform anda — menjana laman web, memproses pesanan, menyokong penghantaran, mengeluarkan invois langganan, dan menyediakan sokongan pelanggan.
- **Kepada siapa kami dedahkan:** Pembekal infrastruktur (Supabase, Render), pemproses pembayaran langganan (ToyyibPay), dan pembekal AI (Stability AI, DeepSeek, Qwen/Alibaba Cloud, Anthropic Claude). Kami **tidak menjual** data anda kepada sesiapa.
- **Apa kami TIDAK proses:** Kami **tidak memproses pembayaran customer untuk pesanan makanan** (COD = tunai terus kepada penghantar; QR statik = pemindahan bank terus kepada merchant). Kami juga **tidak mengakses mesej WhatsApp** anda — pautan WhatsApp adalah deep-link sahaja.
- **Hak anda:** Anda mempunyai hak akses, pembetulan, penarikan persetujuan, pemadaman, mudah alih, dan hadkan pemprosesan di bawah PDPA 2010. Hubungi admin@binaapp.my.
- **Komitmen masa depan:** Dalam tempoh 60 hari dari tarikh berkuat kuasa, kami akan melancarkan (a) UI persetujuan khusus per-ciri untuk fungsi AI yang mengandungi PII customer, (b) banner kuki pada laman web restoran yang dijana, dan (c) sokongan untuk pengepala HTTP Do-Not-Track.`,
  },

  introduction: {
    title: '1. Pengenalan',
    content: `Selamat datang ke Polisi Privasi BinaApp ("**Polisi**"). BinaApp ("**kami**", "**kita**", "**BinaApp**") ialah platform pembina laman web yang dipacu oleh kecerdasan buatan ("**AI**") untuk perniagaan makanan dan minuman ("**F&B**") di Malaysia. Platform ini dimiliki dan dikendalikan oleh **Ezy Work Asia Solution** (No. SSM: 002944700-D), sebuah perniagaan berdaftar di Malaysia.

Polisi ini menerangkan bagaimana kami mengumpul, menggunakan, mendedahkan, menyimpan, dan melindungi data peribadi anda apabila anda:

- Mendaftar dan menggunakan akaun merchant BinaApp;
- Menggunakan dashboard BinaApp untuk mengurus perniagaan F&B anda;
- Menggunakan ciri-ciri AI untuk menjana laman web, imej, atau analisis;
- Berinteraksi dengan BinaBot atau pasukan sokongan kami;
- Melayari laman web yang dihos oleh BinaApp bagi pihak merchant (contohnya, [namaperniagaan].binaapp.my).

Kami komited untuk mematuhi **Akta Perlindungan Data Peribadi 2010** ("**PDPA 2010**") Malaysia dan tujuh prinsip yang termaktub di dalamnya:

1. Prinsip Am;
2. Prinsip Notis dan Pilihan;
3. Prinsip Pendedahan;
4. Prinsip Keselamatan;
5. Prinsip Penyimpanan;
6. Prinsip Integriti Data;
7. Prinsip Akses.

Polisi ini berkuat kuasa pada **21 Mei 2026** dan menggantikan semua versi terdahulu, termasuk Versi 2.0 (bertarikh 31 Januari 2025) dan Versi 1.0 (awal 2024). Lihat seksyen Riwayat Perubahan pada penghujung Polisi ini untuk butiran perubahan antara versi.

**Sila baca Polisi ini dengan teliti.** Dengan mendaftar akaun BinaApp, menggunakan perkhidmatan kami, atau melayari laman web yang dihos oleh BinaApp, anda mengakui bahawa anda telah membaca, memahami, dan bersetuju dengan terma-terma Polisi ini. Jika anda tidak bersetuju, sila berhenti menggunakan perkhidmatan kami.`,
  },

  sections: [
    {
      id: 'pendaftaran-akaun',
      title: '2. Bila Anda Mendaftar Akaun BinaApp (Merchant)',
      content: `Apabila anda mendaftar akaun merchant BinaApp, kami mengumpul maklumat berikut:

**Data yang dikumpul:**
- Alamat emel
- Kata laluan (disimpan dalam bentuk yang dicincang menggunakan algoritma keselamatan industri — kami **tidak** dapat melihat kata laluan teks asal anda)
- Nama penuh
- Nama perniagaan
- Nombor telefon
- Nombor pendaftaran SSM (pilihan, jika dimasukkan)
- Logo perniagaan (pilihan, jika dimuat naik)

**Tujuan pengumpulan:**
- Untuk mengenal pasti anda sebagai pemilik akaun;
- Untuk membenarkan log masuk yang selamat;
- Untuk berkomunikasi dengan anda mengenai akaun, langganan, dan kemas kini perkhidmatan;
- Untuk memulihkan akses jika anda terlupa kata laluan;
- Untuk mengeluarkan invois langganan dan resit.

**Asas undang-undang (PDPA 2010):**
- Persetujuan eksplisit anda yang diberi semasa pendaftaran;
- Pemprosesan yang perlu untuk pelaksanaan kontrak perkhidmatan dengan anda.

**Di mana data disimpan:**
- Pangkalan data Supabase (penyedia infrastruktur PostgreSQL berasaskan awan) di wilayah Asia Tenggara (Singapura) dan/atau wilayah Malaysia, mengikut konfigurasi tetapan platform.
- Sandaran yang disulitkan disimpan dalam jangka masa yang sama.

**Berapa lama disimpan:**
- Sepanjang tempoh akaun anda aktif;
- Selama 30 hari selepas penamatan akaun (untuk pemulihan kecemasan), kemudian dipadam secara kekal.

Anda boleh mengemas kini maklumat akaun anda pada bila-bila masa melalui dashboard BinaApp. Untuk pemadaman akaun penuh, sila lihat seksyen Hak Anda di bawah.`,
    },

    {
      id: 'penggunaan-dashboard',
      title: '3. Bila Anda Menggunakan Dashboard BinaApp',
      content: `Apabila anda log masuk dan menggunakan dashboard BinaApp, kami mengumpul data penggunaan tertentu untuk memastikan platform berfungsi, mengukur penggunaan kuota, dan mengesan isu teknikal.

**Data yang dikumpul:**
- Alamat IP (untuk pengesahan sesi dan keselamatan)
- Jenis pelayar (browser) dan sistem operasi
- Jenis peranti (mudah alih, tablet, desktop)
- Tarikh dan masa log masuk
- Halaman dashboard yang dilawati
- Tindakan yang dilakukan (contohnya: menjana laman web, mengemas kini menu, memuat naik foto)
- Kiraan penggunaan kuota (bilangan laman web yang dijana, bilangan imej AI, bilangan penghantar yang ditambah, dan sebagainya)

**Tujuan pengumpulan:**
- Untuk memastikan sesi anda selamat dan tidak diceroboh;
- Untuk mengukur penggunaan terhadap had langganan anda;
- Untuk mengesan dan menyiasat ralat teknikal;
- Untuk memperbaiki pengalaman pengguna platform secara keseluruhan.

**Pendedahan penting — kami TIDAK menggunakan SDK analitis pihak ketiga:**

BinaApp **tidak** menggunakan Google Analytics, PostHog, Plausible, Mixpanel, Amplitude, Sentry (untuk analitis), Hotjar, FullStory, atau mana-mana SDK analitis tingkah laku pihak ketiga lain pada dashboard merchant kami. Semua data telemetri penggunaan dikumpul dan disimpan dalam infrastruktur Supabase kami sahaja.

**Asas undang-undang:**
- Kepentingan sah untuk operasi platform yang selamat dan berfungsi;
- Pemprosesan yang perlu untuk pelaksanaan kontrak perkhidmatan.

**Tempoh penyimpanan:** 90 hari untuk log penggunaan terperinci; data agregat (tanpa pengenalan) boleh disimpan lebih lama untuk tujuan statistik dalaman.`,
    },

    {
      id: 'pesanan-customer',
      title: '4. Bila Merchant Menerima Pesanan',
      content: `Apabila customer membuat pesanan pada laman web restoran anda atau anda merekodkan pesanan secara manual dalam dashboard, BinaApp menyimpan data pesanan tersebut bagi pihak anda. **Anda, sebagai merchant, adalah pengawal data (data controller) untuk data customer anda.** BinaApp bertindak sebagai pemproses data (data processor) untuk anda.

**Data yang disimpan untuk setiap pesanan:**
- Nama customer
- Nombor telefon customer
- Alamat penghantaran (jika berkenaan)
- Item-item yang dipesan
- Jumlah pesanan
- Arahan khas (jika ada)
- Nota pesanan
- Status pesanan (baru, sedang disediakan, dalam penghantaran, selesai)
- Tarikh dan masa pesanan

**Tujuan pengumpulan:**
- Untuk membolehkan anda menguruskan pesanan customer;
- Untuk membolehkan penghantar menghubungi customer semasa penghantaran;
- Untuk menyimpan rekod transaksi anda;
- Untuk membolehkan customer menyemak status pesanan mereka.

**Klausa "data peribadi individu lain":**

Apabila anda memasukkan atau memuat naik data customer ke dalam platform BinaApp, **anda mengesahkan bahawa anda telah mendapat persetujuan yang sewajarnya daripada customer tersebut** untuk mengumpul dan memproses data peribadi mereka di bawah PDPA 2010. Anda bertanggungjawab sepenuhnya untuk:

- Memaklumkan customer tentang pengumpulan data mereka;
- Menyediakan polisi privasi anda sendiri (jika berkenaan, contohnya untuk perniagaan rantaian);
- Memastikan customer mempunyai hak akses dan pembetulan data mereka;
- Mengendalikan permintaan pemadaman data customer.

BinaApp menyediakan infrastruktur teknikal untuk anda menguruskan data ini, tetapi tidak bertindak sebagai pengawal data utama untuk data customer anda.

**Di mana disimpan:** Pangkalan data Supabase (Singapura/Malaysia).

**Tempoh penyimpanan:** Sehingga 7 tahun selepas tarikh pesanan, mengikut keperluan rekod perakaunan Malaysia. Anda boleh meminta pemadaman data customer tertentu pada bila-bila masa melalui dashboard.`,
    },

    {
      id: 'rider-penghantaran',
      title: '5. Bila Rider Melaksanakan Penghantaran',
      content: `BinaApp menyediakan sistem penghantaran pilihan yang boleh anda aktifkan untuk perniagaan anda. Apabila penghantar (rider) anda menggunakan sistem ini, data berikut dikumpul:

**Data penghantar (rider) yang diuruskan oleh merchant:**
- Nama penghantar
- Nombor telefon
- Nombor plat kenderaan (jika dimasukkan)
- Foto profil (pilihan)

Penghantar **didaftarkan dan diuruskan oleh anda sebagai merchant** dalam dashboard BinaApp. Hubungan kontraktual antara anda dan penghantar adalah di luar skop perkhidmatan BinaApp.

**Status penghantar — pendedahan penting:**

Penghantar yang anda daftarkan adalah **kontraktor bebas yang terikat dengan anda sebagai merchant**, dan **bukan** pekerja, ejen, atau wakil BinaApp. BinaApp menyediakan alat perisian untuk anda menguruskan operasi penghantaran sahaja; semua tanggungjawab pekerja, insurans, gaji, dan kewajipan undang-undang berkaitan penghantar adalah tanggungjawab anda sebagai merchant.

**Data GPS penghantar:**
- Koordinat lokasi (latitud dan longitud) dikumpul **hanya semasa penghantaran aktif** (selepas penghantar menerima tugasan sehingga penghantaran ditandakan selesai);
- Data lokasi dikemas kini setiap beberapa saat untuk membolehkan customer dan merchant menjejaki status penghantaran;
- Penjejakan GPS **dihentikan** sebaik sahaja penghantaran selesai atau dibatalkan.

**Foto bukti penghantaran (delivery photo verifier):**
- Apabila penghantar memuat naik foto sebagai bukti penghantaran selesai, foto tersebut dihantar kepada model AI Qwen (di Singapura, melalui Alibaba Cloud International) untuk pengesahan automatik (contohnya, mengesan bungkusan atau pintu rumah);
- ⚠️ **Risiko PII:** Foto boleh mengandungi muka customer, plat nombor kenderaan, atau elemen identifikasi lain. Sila lihat seksyen AI di bawah untuk butiran lanjut.

**Tujuan pengumpulan:**
- Untuk membolehkan koordinasi penghantaran masa nyata;
- Untuk membolehkan customer menjejaki pesanan mereka;
- Untuk menyediakan bukti penghantaran kepada merchant.

**Tempoh penyimpanan:**
- Data GPS: 30 hari selepas penghantaran selesai;
- Foto bukti penghantaran: 30 hari selepas penghantaran selesai.`,
    },

    {
      id: 'ai-features',
      title: '6. Bila Anda Berinteraksi dengan Ciri AI BinaApp',
      content: `BinaApp menggunakan beberapa pembekal AI pihak ketiga untuk menyediakan ciri-ciri seperti penjanaan laman web, penjanaan imej, analisis aduan, balasan automatik, dan pengesahan foto. Apabila anda menggunakan ciri-ciri ini, data yang berkaitan dihantar kepada pembekal AI tersebut untuk diproses.

Jadual berikut menyenaraikan setiap ciri AI, pembekal yang digunakan, wilayah pemprosesan, jenis data yang dihantar, risiko PII (Personal Identifiable Information / data peribadi), dan status persetujuan semasa.

**Nota mengenai status persetujuan:** Beberapa ciri AI yang mengandungi PII customer pada masa ini beroperasi atas asas notis sahaja (anda diberitahu melalui Polisi ini bahawa data dihantar kepada AI). Dalam tempoh 60 hari dari tarikh berkuat kuasa Polisi ini (lihat seksyen Komitmen 60 Hari), kami akan melancarkan UI persetujuan eksplisit per-ciri untuk fungsi-fungsi ini.

**Nota mengenai Anthropic Claude (analisis emel sokongan):** Sebelum kandungan emel dihantar kepada Anthropic, alamat emel pengirim dicincang (di-hash secara satu hala) supaya alamat emel asal tidak dapat diketahui semula. Selain itu, di bawah kontrak komersial standard, **Anthropic tidak menggunakan data customer mereka untuk melatih model Claude**.

**Nota mengenai pembekal AI di luar Malaysia:** Penggunaan ciri-ciri AI ini melibatkan pemindahan data merentas sempadan ke Amerika Syarikat, Republik Rakyat China, dan Singapura. Sila lihat seksyen Pemindahan Data Merentas Sempadan untuk butiran perlindungan yang digunakan.

Jika anda tidak selesa dengan pemprosesan AI untuk mana-mana ciri tertentu, anda boleh:
- Mengelakkan menggunakan ciri tersebut (contohnya, tidak menggunakan analisis aduan AI dan menguruskan aduan secara manual);
- Menghubungi kami di admin@binaapp.my untuk membincangkan pilihan alternatif.`,
      aiVendorTable: [
        {
          feature: 'Penjanaan Laman Web',
          vendor: 'DeepSeek',
          region: 'Republik Rakyat China',
          dataSent: 'Penerangan perniagaan, nama, lokasi, jenis masakan yang dimasukkan oleh anda',
          piiRisk: 'warning',
          piiNote: 'Berisiko jika anda memasukkan PII customer dalam penerangan',
          consentStatus: 'Persetujuan tersirat semasa memulakan penjanaan',
        },
        {
          feature: 'Penjanaan Imej Menu / Hero',
          vendor: 'Stability AI',
          region: 'Amerika Syarikat',
          dataSent: 'Prompt teks visual sahaja (contohnya: "nasi lemak dengan sambal")',
          piiRisk: 'safe',
          piiNote: 'Tiada PII dihantar — hanya penerangan visual',
          consentStatus: 'Persetujuan tersirat semasa meminta imej',
        },
        {
          feature: 'Analisis Aduan / Pertikaian',
          vendor: 'DeepSeek',
          region: 'Republik Rakyat China',
          dataSent: 'Teks aduan customer, sejarah pesanan berkaitan, butiran transaksi',
          piiRisk: 'warning',
          piiNote: 'Boleh mengandungi PII customer (nama, nombor telefon dalam teks aduan)',
          consentStatus: 'Notis sahaja — UI persetujuan eksplisit akan dilancarkan dalam tempoh 60 hari',
        },
        {
          feature: 'Balasan AI dalam Chat',
          vendor: 'DeepSeek',
          region: 'Republik Rakyat China',
          dataSent: 'Konteks perbualan customer-merchant, mesej customer terkini',
          piiRisk: 'warning',
          piiNote: 'Mengandungi PII customer dalam konteks perbualan',
          consentStatus: 'Notis sahaja — UI persetujuan eksplisit akan dilancarkan dalam tempoh 60 hari',
        },
        {
          feature: 'BinaBot (Chatbot Sokongan Merchant)',
          vendor: 'DeepSeek',
          region: 'Republik Rakyat China',
          dataSent: 'Soalan anda dan konteks akaun merchant',
          piiRisk: 'warning',
          piiNote: 'Boleh mengandungi PII jika anda menyertakan butiran customer dalam soalan',
          consentStatus: 'Persetujuan tersirat semasa berinteraksi dengan BinaBot',
        },
        {
          feature: 'Pengesahan Foto Penghantaran',
          vendor: 'Qwen (Alibaba Cloud International)',
          region: 'Singapura',
          dataSent: 'Imej foto bukti penghantaran yang dimuat naik oleh penghantar',
          piiRisk: 'warning',
          piiNote: 'Boleh mengandungi muka customer, plat nombor, atau elemen identifikasi lain',
          consentStatus: 'Notis sahaja — UI persetujuan eksplisit akan dilancarkan dalam tempoh 60 hari',
        },
        {
          feature: 'Analisis Emel Sokongan',
          vendor: 'Anthropic Claude',
          region: 'Amerika Syarikat',
          dataSent: 'Kandungan teks emel; alamat emel pengirim dicincang (sanitized) sebelum dihantar',
          piiRisk: 'safe',
          piiNote: 'Alamat emel dicincang; Anthropic tidak melatih model atas data customer per kontrak komersial',
          consentStatus: 'Notis (digunakan untuk operasi sokongan dalaman)',
        },
        {
          feature: 'Chatbot Merchant (yang dilayan customer pada laman web)',
          vendor: 'DeepSeek',
          region: 'Republik Rakyat China',
          dataSent: 'Soalan customer kepada merchant, konteks akaun merchant',
          piiRisk: 'warning',
          piiNote: 'Boleh mengandungi PII customer dalam soalan mereka',
          consentStatus: 'Notis sahaja — UI persetujuan eksplisit akan dilancarkan dalam tempoh 60 hari',
        },
      ],
    },

    {
      id: 'sokongan',
      title: '7. Bila Anda Menghubungi Sokongan Kami',
      content: `Apabila anda menghubungi pasukan sokongan BinaApp atau berinteraksi dengan BinaBot, kami mengumpul dan memproses data komunikasi tersebut untuk membantu menyelesaikan pertanyaan anda.

**Saluran sokongan dan data yang dikumpul:**

**(a) BinaBot (chatbot dalam dashboard):**
- Mesej anda, konteks akaun merchant, dan sejarah perbualan;
- Dihantar kepada DeepSeek (di Republik Rakyat China) untuk menjana balasan AI;
- Lihat jadual di seksyen 6 untuk butiran risiko PII dan status persetujuan.

**(b) Emel sokongan (support.team@binaapp.my, admin@binaapp.my):**
- Kandungan emel anda, alamat emel pengirim, dan sebarang lampiran;
- Kandungan emel dianalisis menggunakan Anthropic Claude untuk mempercepat klasifikasi dan tindak balas;
- **Sebelum dihantar kepada Claude, alamat emel pengirim dicincang (di-hash)** supaya alamat asal tidak dapat diketahui semula daripada data yang dihantar.

**(c) Sembang langsung (jika ada):**
- Kandungan perbualan dan masa interaksi.

**Tujuan pengumpulan:**
- Untuk menyelesaikan pertanyaan atau aduan anda;
- Untuk memperbaiki kualiti sokongan;
- Untuk melatih staf sokongan dalaman (data tanpa pengenalan).

**Tempoh penyimpanan:**
- Sejarah perbualan BinaBot: 90 hari;
- Emel sokongan: sehingga 2 tahun untuk tujuan jejak audit dan rujukan;
- Log sembang langsung: 90 hari.

**Pendedahan penting:** Anthropic mempunyai kontrak komersial standard dengan pelanggan perusahaan yang **menghalang penggunaan data input customer untuk melatih model Claude**. Ini bermakna kandungan emel anda yang dihantar kepada Claude **tidak digunakan untuk melatih model AI mereka**.`,
    },

    {
      id: 'pembayaran-langganan',
      title: '8. Bila Anda Membuat Pembayaran Langganan',
      content: `BinaApp mengenakan yuran langganan bulanan untuk akses kepada platform (contohnya, pelan Starter RM 5/bulan, Basic RM 29/bulan, Pro RM 49/bulan, atau yang setara). Pembayaran langganan ini diproses melalui **ToyyibPay**, pemproses pembayaran yang diluluskan oleh Bank Negara Malaysia.

**Data yang diproses untuk pembayaran langganan:**
- Nama dan alamat emel anda (dihantar kepada ToyyibPay untuk pengeluaran resit);
- Amaun transaksi dan butiran langganan;
- ID transaksi yang dikembalikan oleh ToyyibPay.

**Apa yang BinaApp TIDAK simpan:**
- **Nombor kad kredit / debit** anda;
- **Nombor CVV / CVC**;
- **Tarikh tamat tempoh kad**;
- **Maklumat akaun bank** yang digunakan untuk pemindahan.

Semua butiran pembayaran sensitif dikendalikan dan disimpan oleh ToyyibPay (pemproses pembayaran yang mematuhi PCI-DSS) dan tidak pernah disimpan dalam sistem BinaApp.

**Apa yang BinaApp simpan:**
- ID transaksi (untuk rujukan);
- Tarikh pembayaran;
- Amaun yang dibayar;
- Status langganan (aktif, tamat tempoh, dibatalkan);
- Resit elektronik (PDF/HTML).

**Tujuan pengumpulan:**
- Untuk mengaktifkan dan mengekalkan langganan anda;
- Untuk mengeluarkan resit dan invois;
- Untuk mematuhi keperluan rekod perakaunan dan cukai Malaysia.

**Tempoh penyimpanan:** 7 tahun (mengikut keperluan undang-undang perakaunan dan cukai Malaysia).

**Asas undang-undang:** Pemprosesan yang perlu untuk pelaksanaan kontrak langganan dengan anda; pematuhan kepada kewajipan undang-undang (rekod cukai).`,
    },

    {
      id: 'non-processing-makanan',
      title: '9. Pendedahan Penting — BinaApp TIDAK Memproses Pembayaran Pesanan Makanan Customer',
      content: `**Ini adalah pendedahan penting yang ingin kami jelaskan secara eksplisit:**

BinaApp memproses pembayaran **langganan merchant** sahaja (lihat seksyen 8). BinaApp **tidak memproses, menerima, atau menyimpan** sebarang butiran pembayaran customer untuk pesanan makanan yang dibuat melalui laman web restoran anda.

**Bagaimana customer membayar untuk pesanan makanan:**

**(a) COD (Bayar Tunai semasa Penghantaran):**
- Customer membayar **tunai secara langsung kepada penghantar** apabila pesanan tiba;
- Tiada wang melalui sistem BinaApp;
- BinaApp tidak menyimpan rekod butiran pembayaran tunai ini (hanya status pesanan: dibayar / belum dibayar).

**(b) Pemindahan QR Statik:**
- Merchant memuat naik imej kod QR pembayaran mereka sendiri (contohnya, QR DuitNow atau QR bank) kepada dashboard;
- Customer mengimbas QR ini dan membuat pemindahan **secara langsung kepada akaun bank merchant**;
- Wang tidak melalui sistem BinaApp pada bila-bila masa;
- BinaApp tidak mempunyai akses kepada akaun bank merchant atau rekod pemindahan tersebut;
- Merchant bertanggungjawab untuk mengesahkan pembayaran (contohnya, dengan menyemak resit bank customer atau notifikasi pemindahan).

**Apa yang BinaApp simpan untuk pesanan makanan:**
- Status pesanan (baru, dibayar, dalam penghantaran, selesai);
- Amaun pesanan;
- Kaedah pembayaran yang dipilih oleh customer (COD atau QR);
- Bukan butiran pembayaran sebenar.

**Implikasi penting:**
- Sebarang pertikaian pembayaran antara customer dan merchant (contohnya, customer tidak membayar, atau membuat pemindahan ke akaun salah) **adalah antara customer dan merchant**, bukan BinaApp;
- BinaApp tidak dapat memulakan bayaran balik untuk pesanan makanan kerana kami tidak pernah memegang wang tersebut;
- Untuk bayaran balik pesanan makanan, customer perlu berbincang secara langsung dengan merchant.`,
    },

    {
      id: 'whatsapp-deeplink',
      title: '10. Pendedahan Penting — Pautan WhatsApp adalah Deep-Link Sahaja',
      content: `Laman web restoran yang dijana oleh BinaApp mungkin mengandungi butang atau pautan "Hubungi via WhatsApp" yang membenarkan customer menghubungi merchant melalui WhatsApp.

**Bagaimana ia berfungsi:**

Butang ini ialah **deep-link** kepada aplikasi WhatsApp (contohnya, \`https://wa.me/60123456789\`). Apabila customer mengklik butang ini:

1. Aplikasi WhatsApp dibuka di peranti customer (jika dipasang);
2. Perbualan baru dengan nombor telefon merchant dibuka;
3. Customer boleh menaip mesej dan menghantarnya.

**Apa yang BinaApp TIDAK lakukan:**
- BinaApp **tidak mengakses, menyimpan, atau membaca** mesej WhatsApp anda;
- BinaApp **tidak mengintegrasikan dengan WhatsApp Business API** atau mana-mana API mesej WhatsApp lain;
- BinaApp **tidak menerima notifikasi** apabila mesej dihantar atau dibaca;
- BinaApp **tidak menyimpan kandungan perbualan** antara customer dan merchant di WhatsApp.

Pautan deep-link hanyalah satu cara untuk memudahkan customer menghubungi merchant. Setelah perbualan dipindahkan ke WhatsApp, ia adalah komunikasi peribadi antara customer dan merchant yang ditadbir oleh polisi privasi WhatsApp (Meta Platforms, Inc.) dan bukan BinaApp.

**Apa yang BinaApp simpan:**
- Nombor telefon WhatsApp anda (sebagai merchant) yang anda masukkan dalam tetapan laman web — ini diperlukan untuk menjana pautan deep-link tersebut.

**Pengguna luar Malaysia yang menggunakan laman web:** Jika customer di luar Malaysia mengklik butang WhatsApp, pemindahan komunikasi tersebut ditadbir oleh polisi privasi WhatsApp dan tidak melibatkan BinaApp.`,
    },

    {
      id: 'visitor-tracker',
      title: '11. Bila Pelawat Melayari Laman Web Restoran Anda',
      content: `Apabila pelawat melayari laman web restoran yang dihos oleh BinaApp (contohnya, \`namaperniagaan.binaapp.my\`), kami mengumpul data analitis pertama-pihak (first-party) untuk menyediakan papan pemuka analitis kepada anda sebagai merchant.

**Data yang dikumpul:**
- Alamat IP pelawat (dipendekkan untuk privasi);
- String User-Agent pelayar;
- Jenis peranti (mudah alih, tablet, desktop);
- Keluarga pelayar dan sistem operasi;
- URL rujukan (referrer) — laman web yang pelawat datang daripadanya;
- Laluan halaman yang dilawati (\`/menu\`, \`/about\`, dll.);
- Tarikh dan masa lawatan;
- ID pelawat tanpa nama yang dijana secara tempatan (cincangan IP + User-Agent, atau ID localStorage \`bina_visitor\`).

**Tujuan pengumpulan:**
- Untuk menyediakan statistik lalu lintas laman web kepada merchant;
- Untuk mengukur populariti halaman tertentu;
- Untuk memahami corak peranti dan pelayar pelawat;
- Untuk membantu merchant memperbaiki kandungan dan reka bentuk laman web.

**Apa yang TIDAK dikumpul:**
- Nama, emel, atau nombor telefon pelawat (melainkan pelawat memilih untuk memasukkannya melalui borang pesanan);
- Lokasi GPS yang tepat;
- Aktiviti pelayaran di laman web lain;
- Data pengiklanan atau profil pemasaran.

**Di mana data disimpan:**
- Pangkalan data Supabase (Singapura/Malaysia), dalam akaun BinaApp untuk merchant berkenaan;
- Data analitis dipaparkan kepada merchant melalui dashboard mereka sahaja;
- Data **tidak dijual, dikongsi, atau dipindahkan** kepada pengiklan atau pihak ketiga lain.

**Pendedahan penting — pelawat tidak diberi notis langsung pada masa ini:**

Pada masa ini, laman web restoran yang dijana **tidak memaparkan banner kuki atau notis penjejakan** kepada pelawat. Pelawat mungkin tidak menyedari bahawa data lawatan mereka dikumpul. Kami **komited untuk melancarkan banner notis pelawat dan sokongan untuk pengepala HTTP Do-Not-Track dalam tempoh 60 hari** dari tarikh berkuat kuasa Polisi ini (lihat seksyen Komitmen 60 Hari).

**Pilihan opt-out merchant:**

Sebagai merchant, anda boleh **mematikan penjejakan analitis pelawat** untuk laman web anda pada bila-bila masa melalui tetapan dalam dashboard ("Edit Laman Web" → toggle "Aktifkan analitis pelawat"). Apabila dimatikan:

- Skrip penjejakan dikeluarkan dari kod HTML laman web pada penerbitan seterusnya;
- Permintaan analitis sedia ada daripada laman web yang telah diterbitkan akan ditolak oleh pelayan kami;
- Tiada data lawatan baru akan direkodkan untuk laman web anda.

**Tempoh penyimpanan:** Sepanjang akaun merchant aktif (data ialah aset analitis perniagaan merchant). Apabila akaun ditamatkan, data dipadam mengikut polisi pengekalan akaun.`,
    },

    {
      id: 'notis-pengguna-akhir',
      title: '12. Notis kepada Pengguna Akhir (Pelawat Laman Web)',
      content: `**Seksyen ini ditujukan kepada anda jika anda adalah pelawat (customer) yang melayari laman web seperti \`[namaperniagaan].binaapp.my\` — bukan merchant yang memiliki akaun BinaApp.**

**Penjelasan pengehosan:**

Laman web yang anda lawati ialah laman web yang **dihos oleh BinaApp bagi pihak merchant** (perniagaan F&B yang anda berurus niaga dengannya). Walaupun laman web ini berakhir dengan \`.binaapp.my\`, ia adalah laman web perniagaan merchant tersebut, dan bukan laman web BinaApp.

**Hubungan kontraktual:**

Apabila anda membuat pesanan melalui laman web ini:

- **Kontrak jual beli adalah antara anda dan merchant tersebut**, bukan BinaApp;
- BinaApp menyediakan platform teknikal untuk membolehkan merchant menjalankan operasi mereka, tetapi BinaApp **bukan pihak kepada urus niaga jual beli** antara anda dan merchant;
- Sebarang isu berkaitan kualiti makanan, masa penghantaran, bayaran balik, atau aduan perkhidmatan perlu dirujuk **secara langsung kepada merchant**.

**Data peribadi anda:**

Apabila anda membuat pesanan atau menghubungi merchant melalui laman web ini, data peribadi anda (nama, nombor telefon, alamat, butiran pesanan) dikumpul oleh BinaApp **bagi pihak merchant**. Merchant ialah pengawal data utama untuk data anda. BinaApp bertindak sebagai pemproses data untuk merchant.

**Hak anda:**

- Untuk akses, pembetulan, atau pemadaman data peribadi anda yang dipegang oleh merchant, sila hubungi merchant secara langsung;
- Jika merchant tidak memberi respons, anda boleh menghubungi BinaApp di admin@binaapp.my dan kami akan memudahkan permintaan anda kepada merchant;
- Anda juga mempunyai hak untuk membuat aduan kepada Jabatan Perlindungan Data Peribadi Malaysia (lihat seksyen Hubungi Kami / Aduan).

**Polisi privasi merchant:**

Merchant mungkin mempunyai polisi privasi tersendiri yang mengawal pengumpulan dan penggunaan data anda. Jika merchant tidak menyediakannya, Polisi ini terpakai sebagai polisi privasi asas untuk operasi platform.

**Analitis lawatan:**

Lawatan anda ke laman web ini dijejaki untuk tujuan analitis perniagaan merchant. Sila lihat seksyen 11 untuk butiran data yang dikumpul. Pada masa ini tiada banner notis langsung dipaparkan; kami akan melancarkan banner notis dan sokongan Do-Not-Track dalam tempoh 60 hari.`,
    },

    {
      id: 'cookies',
      title: '13. Kuki dan Teknologi Penjejakan',
      content: `BinaApp menggunakan kuki (cookies) dan teknologi penyimpanan tempatan (localStorage) yang terhad untuk operasi platform yang berfungsi. Kami mengklasifikasikan teknologi ini dalam tiga kategori:

**(a) Kuki Penting (Strictly Necessary):**

Kuki ini diperlukan untuk operasi asas platform dan tidak boleh dimatikan tanpa menjejaskan fungsi platform.

- **Kuki sesi Supabase Auth:** Mengekalkan log masuk anda sebagai merchant. Tamat tempoh apabila anda log keluar atau selepas tempoh tidak aktif yang ditetapkan;
- **Kuki keselamatan CSRF:** Melindungi terhadap serangan pemalsuan permintaan silang tapak.

**(b) Kuki Pilihan (Preferences):**

Kuki ini menyimpan pilihan anda untuk pengalaman yang lebih baik.

- **Pilihan tema:** Cerah / gelap;
- **Pilihan bahasa:** BM / EN;
- **Pilihan paparan dashboard:** Susun atur kad, susunan jadual.

**(c) Penyimpanan Tempatan Analitis (First-Party):**

- **\`bina_visitor\` (localStorage):** ID pelawat tanpa nama yang dijana secara tempatan pada peranti pelawat laman web restoran. Digunakan untuk membezakan pelawat berulang daripada pelawat baru dalam analitis merchant. Boleh dikosongkan pada bila-bila masa dengan mengosongkan cache pelayar.

**Pendedahan penting — TIADA SDK analitis pihak ketiga:**

Kami **tidak menggunakan** mana-mana perkhidmatan analitis tingkah laku pihak ketiga, termasuk tetapi tidak terhad kepada:

- Google Analytics
- Google Tag Manager
- Facebook Pixel
- PostHog
- Plausible
- Mixpanel
- Amplitude
- Hotjar
- FullStory
- Microsoft Clarity
- Sentry (untuk analitis pengguna)

Semua data telemetri dikumpul dan disimpan dalam infrastruktur Supabase kami sahaja sebagai data pertama-pihak.

**Mengurus kuki:**

Anda boleh mengurus atau memadam kuki melalui tetapan pelayar anda. Sila ambil perhatian bahawa mematikan kuki penting akan menjejaskan keupayaan anda untuk log masuk dan menggunakan platform.

Untuk pelawat laman web restoran: pada masa ini tiada banner pengurusan kuki ditunjukkan. Kami akan melancarkan banner dengan pilihan kuki dalam tempoh 60 hari (lihat seksyen Komitmen 60 Hari).`,
    },

    {
      id: 'tempoh-penyimpanan',
      title: '14. Tempoh Penyimpanan Data',
      content: `Kami menyimpan data peribadi anda hanya selama yang diperlukan untuk tujuan pengumpulan asal, atau seperti yang dikehendaki oleh undang-undang Malaysia (contohnya, keperluan rekod perakaunan 7 tahun).

Jadual berikut meringkaskan tempoh pengekalan untuk pelbagai jenis data:

(Sila lihat jadual tempoh pengekalan di bawah.)

**Selepas tempoh pengekalan:**
- Data dipadam secara kekal daripada pangkalan data aktif;
- Sandaran yang disulitkan yang mengandungi data tersebut kekal selama tempoh kitaran sandaran (30 hari) sebelum ditulis ganti;
- Data yang dipadam tidak boleh dipulihkan selepas tempoh sandaran tamat.

**Pengecualian:**
- Data yang berkaitan dengan pertikaian undang-undang yang berterusan, siasatan, atau audit boleh disimpan lebih lama mengikut keperluan undang-undang;
- Data agregat dan tanpa pengenalan (contohnya, statistik penggunaan keseluruhan platform) boleh disimpan selama-lamanya untuk tujuan analitis dalaman.`,
      retentionTable: [
        {
          dataType: 'Akaun merchant (aktif)',
          period: 'Sepanjang langganan aktif + 30 hari selepas penamatan',
        },
        {
          dataType: 'Rekod pesanan customer',
          period: '7 tahun (keperluan rekod perakaunan Malaysia)',
        },
        {
          dataType: 'Mesej chat merchant-customer',
          period: '90 hari',
        },
        {
          dataType: 'Data GPS penghantar',
          period: '30 hari selepas penghantaran selesai',
        },
        {
          dataType: 'Rekod transaksi pembayaran langganan',
          period: '7 tahun (keperluan rekod cukai Malaysia)',
        },
        {
          dataType: 'Sandaran data yang dipadam',
          period: '30 hari selepas pemadaman akaun',
        },
        {
          dataType: 'Log permintaan AI (input dan output)',
          period: '90 hari',
        },
        {
          dataType: 'Foto pengesahan penghantaran',
          period: '30 hari selepas penghantaran selesai',
        },
        {
          dataType: 'Imej QR pembayaran merchant',
          period: 'Sepanjang akaun aktif',
        },
        {
          dataType: 'Rekod penggunaan kuota',
          period: '90 hari',
        },
        {
          dataType: 'Rekod pembelian addon',
          period: '7 tahun',
        },
        {
          dataType: 'ID pelawat localStorage (`bina_visitor`)',
          period: 'Sehingga pelawat mengosongkan cache pelayar',
        },
      ],
    },

    {
      id: 'hak-pdpa',
      title: '15. Hak Anda di Bawah PDPA 2010',
      content: `Di bawah Akta Perlindungan Data Peribadi 2010 (PDPA 2010), anda mempunyai hak-hak berikut berkenaan data peribadi anda yang dipegang oleh BinaApp:

**(a) Hak Akses (Right of Access)**

Anda berhak untuk meminta salinan data peribadi anda yang kami pegang, dan untuk diberitahu tentang tujuan pemprosesan dan kelas pihak ketiga yang mungkin menerima data tersebut.

**(b) Hak Pembetulan (Right of Correction)**

Jika data peribadi anda yang kami pegang tidak tepat, tidak lengkap, atau ketinggalan zaman, anda berhak untuk meminta pembetulan atau kemas kini.

**(c) Hak Penarikan Persetujuan (Right to Withdraw Consent)**

Anda boleh menarik balik persetujuan anda untuk pemprosesan data peribadi anda pada bila-bila masa. Sila ambil perhatian bahawa penarikan persetujuan mungkin menjejaskan keupayaan kami untuk menyediakan perkhidmatan kepada anda.

**(d) Hak Pemadaman (Right to Deletion)**

Anda boleh meminta supaya data peribadi anda dipadam, tertakluk kepada keperluan undang-undang untuk pengekalan (contohnya, rekod cukai mesti disimpan selama 7 tahun).

**(e) Hak Mudah Alih (Right to Data Portability)**

Anda boleh meminta untuk menerima data peribadi anda dalam format yang berstruktur, lazim digunakan, dan boleh dibaca oleh mesin (contohnya, JSON atau CSV), dan untuk memindahkannya kepada pengawal data lain.

**(f) Hak Hadkan Pemprosesan (Right to Restrict Processing)**

Anda boleh meminta supaya pemprosesan data peribadi anda dihadkan dalam keadaan tertentu — contohnya, semasa kami menyiasat aduan tentang ketepatan data anda.

**Cara membuat permintaan:**

Hantarkan emel kepada **admin@binaapp.my** dengan format berikut:

- **Subjek:** \`PDPA Request - [Jenis Permintaan]\` (contohnya: \`PDPA Request - Access\`, \`PDPA Request - Deletion\`)
- **Sertakan:** Nama penuh anda, alamat emel berdaftar akaun, dan butiran khusus permintaan anda.

**Tempoh respons:**

Kami akan memberi respons kepada permintaan anda dalam **tempoh 21 hari** dari tarikh kami menerima permintaan lengkap (mengikut Seksyen 7 PDPA 2010). Jika permintaan adalah kompleks atau memerlukan pengesahan tambahan, kami mungkin memerlukan masa tambahan dan akan memaklumkan anda.

**Pengesahan identiti:**

Untuk melindungi data anda, kami mungkin meminta pengesahan identiti tambahan sebelum memproses permintaan (contohnya, mengesahkan ID pesanan terkini atau butiran akaun lain).

**Yuran:**

Permintaan akses pertama dalam tempoh 12 bulan adalah **percuma**. Permintaan susulan dalam tempoh yang sama boleh dikenakan yuran pemprosesan yang munasabah, mengikut yang dibenarkan oleh PDPA 2010.

**Aduan:**

Jika anda tidak berpuas hati dengan respons kami, anda boleh membuat aduan kepada Jabatan Perlindungan Data Peribadi Malaysia (lihat seksyen Hubungi Kami / Aduan).`,
    },

    {
      id: 'pemindahan-merentas-sempadan',
      title: '16. Pemindahan Data Merentas Sempadan',
      content: `Sesetengah data peribadi anda mungkin dipindahkan ke luar Malaysia untuk diproses oleh pembekal infrastruktur dan AI kami. Pemindahan ini dilaksanakan mengikut **Seksyen 129 PDPA 2010** dan Notis Komisioner Perlindungan Data Peribadi (PDP) yang berkaitan.

**Wilayah pemprosesan dan pembekal:**

**(a) Malaysia:**
- Infrastruktur utama BinaApp;
- Sandaran data tertentu;
- Pemprosesan pembayaran langganan oleh ToyyibPay.

**(b) Singapura:**
- Supabase (pangkalan data dan storan) — wilayah Asia Tenggara;
- Render (pelayan aplikasi belakang) — wilayah Asia Tenggara;
- Qwen (Alibaba Cloud International) — pengesahan foto penghantaran AI.

**(c) Amerika Syarikat:**
- Stability AI — penjanaan imej AI;
- Anthropic Claude — analisis emel sokongan;
- Vercel / Render (jika digunakan untuk pengehosan frontend global).

**(d) Republik Rakyat China:**
- DeepSeek — penjanaan laman web AI, analisis aduan, balasan chat AI, BinaBot.

**Perlindungan yang digunakan:**

Untuk setiap pemindahan merentas sempadan, kami memastikan sekurang-kurangnya satu daripada berikut terpakai:

- **Persetujuan anda:** Anda memberikan persetujuan eksplisit untuk pemindahan (contohnya, semasa menggunakan ciri AI tertentu);
- **Pelaksanaan kontrak:** Pemindahan diperlukan untuk pelaksanaan kontrak perkhidmatan dengan anda;
- **Klausa Kontrak Standard:** Pembekal kami terikat oleh kontrak yang mengandungi peruntukan perlindungan data yang setara dengan PDPA 2010;
- **Pematuhan vendor:** Pembekal-pembekal kami mengekalkan sijil atau pengesahan pematuhan industri yang relevan (contohnya, ISO 27001, SOC 2, GDPR).

**Risiko pemindahan merentas sempadan:**

Anda harus sedar bahawa undang-undang perlindungan data di wilayah penerima mungkin berbeza daripada PDPA 2010. Sebagai contoh:

- Data yang diproses di Amerika Syarikat tertakluk kepada undang-undang AS, termasuk akses berpotensi oleh agensi penguatkuasaan AS;
- Data yang diproses di Republik Rakyat China tertakluk kepada undang-undang siber China, termasuk Undang-Undang Keselamatan Siber (Cybersecurity Law) dan Undang-Undang Perlindungan Maklumat Peribadi (PIPL).

Dengan menggunakan ciri-ciri AI BinaApp yang melibatkan pembekal pihak ketiga ini, anda mengakui dan bersetuju dengan pemindahan merentas sempadan tersebut.

**Hak untuk membantah:**

Jika anda mempunyai kebimbangan khusus tentang pemindahan merentas sempadan, sila hubungi kami di admin@binaapp.my. Kami akan berusaha untuk menyediakan alternatif di mana mungkin (contohnya, mengelakkan penggunaan ciri AI tertentu).`,
    },

    {
      id: 'kanak-kanak',
      title: '17. Kanak-Kanak',
      content: `**Pengguna BinaApp (merchant) mestilah berumur 18 tahun ke atas.**

Platform BinaApp adalah perkhidmatan perniagaan-ke-perniagaan (B2B) yang ditujukan kepada pemilik perniagaan F&B yang sah di sisi undang-undang. Kami **tidak** menerima pendaftaran daripada individu di bawah umur 18 tahun sebagai merchant.

Jika kami mendapati bahawa akaun merchant telah didaftarkan oleh individu di bawah 18 tahun, kami akan menamatkan akaun tersebut dan memadam semua data berkaitan dengan akaun itu.

**Data customer di bawah 18 tahun:**

Sebagai merchant, jika anda memuat naik atau merekodkan data customer yang berumur di bawah 18 tahun (contohnya, customer muda yang membuat pesanan), **anda bertanggungjawab untuk mendapatkan keizinan ibu bapa atau penjaga sah** sebelum mengumpul atau memproses data tersebut, sebagaimana dikehendaki oleh PDPA 2010 dan undang-undang perlindungan kanak-kanak Malaysia yang berkaitan.

BinaApp menyediakan infrastruktur teknikal tetapi tidak boleh menentukan umur customer anda. Tanggungjawab untuk pematuhan keperluan keizinan kanak-kanak terletak pada anda sebagai pengawal data.

**Pelawat di bawah 18 tahun pada laman web restoran:**

Pelawat di bawah 18 tahun mungkin melayari laman web restoran yang dijana oleh BinaApp. Kami tidak mengumpul data pengenalan langsung tentang pelawat melalui analitis pertama-pihak (lihat seksyen 11). Walau bagaimanapun, jika pelawat di bawah 18 tahun memilih untuk memasukkan data peribadi mereka (contohnya, melalui borang pesanan), data tersebut dipegang oleh merchant dan tertakluk kepada tanggungjawab merchant untuk pematuhan keperluan keizinan kanak-kanak.

Jika anda mengetahui bahawa anak anda telah memberikan data peribadi melalui laman web yang dihos oleh BinaApp, sila hubungi merchant secara langsung untuk meminta pemadaman, atau hubungi kami di admin@binaapp.my dan kami akan memudahkan permintaan tersebut.`,
    },

    {
      id: 'data-pihak-ketiga',
      title: '18. Data Pihak Ketiga yang Dimuat Naik oleh Merchant',
      content: `Sebagai merchant, anda mungkin memuat naik atau memasukkan data peribadi tentang individu lain ke dalam platform BinaApp dalam pelbagai konteks, termasuk:

- **Data customer:** Nama, nombor telefon, alamat customer yang anda rekod untuk pesanan;
- **Data penghantar:** Nama, nombor telefon, butiran kenderaan penghantar yang anda daftarkan;
- **Data kakitangan:** Jika anda menambah pengguna tambahan (cawangan, kakitangan) kepada akaun merchant anda.

**Pengakuan anda sebagai pengawal data:**

Apabila anda memasukkan data peribadi individu lain ke dalam BinaApp, **anda mengesahkan dan menjamin bahawa:**

1. Anda mempunyai asas undang-undang yang sah (contohnya, persetujuan, kontrak, atau kewajipan undang-undang) untuk memproses data peribadi tersebut;
2. Anda telah memaklumkan individu berkenaan tentang pengumpulan data mereka, tujuan pemprosesan, dan kelas pihak ketiga yang mungkin menerima data (termasuk BinaApp sebagai pemproses data dan pembekal AI yang tersenarai dalam seksyen 6);
3. Anda telah menyediakan polisi privasi anda sendiri (jika berkenaan) kepada individu tersebut;
4. Anda akan menjawab permintaan akses, pembetulan, atau pemadaman daripada individu tersebut secara tepat pada masanya.

**Peranan BinaApp:**

BinaApp bertindak sebagai **pemproses data** untuk data peribadi yang anda muat naik. Kami:

- Menyimpan dan memproses data tersebut bagi pihak anda mengikut arahan anda;
- Tidak menggunakan data tersebut untuk tujuan kami sendiri (kecuali untuk operasi platform yang diperlukan, seperti kuota dan analitis penggunaan);
- Akan memudahkan permintaan PDPA daripada individu tersebut, tetapi keputusan akhir tentang permintaan adalah tanggungjawab anda sebagai pengawal data.

**Indemniti:**

Anda bersetuju untuk membayar ganti rugi dan melindungi BinaApp daripada sebarang tuntutan, denda, atau kerugian yang timbul daripada pelanggaran kewajipan anda di bawah PDPA 2010 atau undang-undang perlindungan data lain berkaitan dengan data pihak ketiga yang anda muat naik. Butiran lanjut tentang indemniti adalah dalam Terma Perkhidmatan.

**Pemadaman selepas penamatan akaun:**

Apabila akaun merchant anda ditamatkan, kami akan memadam semua data customer dan data pihak ketiga lain yang anda muat naik mengikut polisi pengekalan kami (lihat seksyen 14), tertakluk kepada keperluan undang-undang untuk pengekalan rekod tertentu.`,
    },

    {
      id: 'algorithmic-decision',
      title: '19. Pembuatan Keputusan Algoritmik (AI)',
      content: `BinaApp menggunakan AI untuk membantu dalam pembuatan keputusan tertentu, terutamanya dalam aliran kerja aduan dan pertikaian customer. Seksyen ini menerangkan hak anda berkenaan keputusan yang dibuat oleh sistem AI kami.

**Apakah keputusan AI yang mempengaruhi anda:**

**(a) Analisis dan cadangan aduan:**
- Apabila customer mengemukakan aduan melalui sistem chat atau borang aduan, AI (DeepSeek) menganalisis aduan dan mencadangkan tindakan: bayaran balik penuh, bayaran balik separa, atau tolak;
- Cadangan ini dipaparkan kepada anda sebagai merchant untuk semakan dan kelulusan;
- **Anda sebagai merchant membuat keputusan akhir** sama ada untuk menerima cadangan AI atau membuat keputusan manual.

**(b) Klasifikasi emel sokongan:**
- Emel sokongan masuk diklasifikasikan oleh AI (Anthropic Claude) untuk diarahkan kepada pasukan yang sesuai;
- Tiada keputusan automatik yang menjejaskan anda secara langsung — hanya laluan pentadbiran.

**(c) Pengesahan foto penghantaran:**
- AI (Qwen) menganalisis foto bukti penghantaran untuk mengesahkan unsur-unsur tertentu (contohnya, bungkusan kelihatan, pintu rumah);
- Kegagalan pengesahan tidak menghalang penghantaran ditandakan selesai — ia hanya membendera untuk semakan merchant.

**Hak anda untuk semakan manual:**

Anda mempunyai hak untuk meminta semakan manual oleh manusia bagi mana-mana keputusan yang dipengaruhi oleh sistem AI kami. Untuk meminta semakan manual:

- Hantarkan emel kepada **admin@binaapp.my** dengan subjek \`AI Decision Review - [Butiran Ringkas]\`;
- Sertakan butiran khusus keputusan yang anda ingin disemak dan sebab anda meminta semakan.

**Tempoh tindak balas:**

Kami akan menjawab permintaan semakan dalam **tempoh masa yang munasabah** berdasarkan kerumitan kes. Kami tidak menjanjikan SLA tertentu untuk semakan manual.

**Telus tentang had AI:**

Sila ambil perhatian bahawa sistem AI tidak sempurna dan boleh membuat kesilapan. Kami menggalakkan anda untuk:
- Sentiasa menyemak cadangan AI sebelum menerimanya;
- Membendera kesilapan AI kepada kami supaya kami boleh memperbaiki sistem;
- Menggunakan pertimbangan profesional anda sendiri sebagai pemilik perniagaan.`,
    },

    {
      id: 'komitmen-60-hari',
      title: '20. Komitmen 60 Hari',
      content: `Kami komited untuk memperbaiki amalan privasi kami secara berterusan. Dalam tempoh **60 hari** dari tarikh berkuat kuasa Polisi ini (iaitu, sebelum atau pada **20 Julai 2026**), kami akan melancarkan perubahan berikut:

**(a) UI Persetujuan Eksplisit untuk Ciri AI yang Mengandungi PII**

Pada masa ini, beberapa ciri AI beroperasi atas asas notis sahaja (anda diberitahu melalui Polisi ini bahawa data dihantar kepada pembekal AI). Kami akan melancarkan dialog persetujuan eksplisit per-ciri untuk:

- Analisis aduan / pertikaian (DeepSeek);
- Balasan AI dalam chat customer-merchant (DeepSeek);
- Pengesahan foto penghantaran (Qwen);
- Chatbot merchant yang dilayan customer (DeepSeek).

Anda akan diminta untuk memberi persetujuan eksplisit sekali bagi setiap ciri, dengan pilihan untuk menarik balik persetujuan pada bila-bila masa melalui tetapan dashboard.

**(b) Banner Notis Kuki pada Laman Web Restoran yang Dijana**

Pelawat laman web restoran yang dihos oleh BinaApp akan diberi notis yang jelas tentang penjejakan analitis pertama-pihak (\`bina_visitor\`), dengan pilihan untuk menerima atau menolak penjejakan.

**(c) Sokongan untuk Pengepala HTTP Do-Not-Track (DNT)**

Pelayan analitis kami akan menghormati pengepala HTTP \`DNT: 1\` yang dihantar oleh pelayar pelawat. Apabila pengepala ini hadir, permintaan analitis akan ditolak tanpa rekod.

**Status kemas kini:**

Status pelaksanaan komitmen-komitmen ini akan dikemas kini dalam seksyen Riwayat Perubahan apabila masing-masing dilancarkan. Jika kami menghadapi kelewatan, kami akan mengemas kini Polisi ini untuk menjelaskan status baru.

**Kenapa kami menjadikan ini sebagai komitmen formal:**

Kami percaya privasi pengguna adalah keutamaan jangka panjang. Daripada melancarkan ciri-ciri ini tanpa kejelasan masa, kami komited secara terbuka kepada tarikh akhir supaya anda dapat memegang kami bertanggungjawab. Jika anda tidak melihat ciri-ciri ini dilancarkan dalam tempoh yang dijanjikan, sila hubungi kami di admin@binaapp.my.`,
    },

    {
      id: 'perubahan-polisi',
      title: '21. Perubahan kepada Polisi Ini',
      content: `BinaApp berhak untuk mengemas kini Polisi ini dari semasa ke semasa untuk mencerminkan perubahan dalam:

- Amalan pengumpulan data kami;
- Ciri-ciri baru atau pembekal pihak ketiga;
- Keperluan undang-undang dan kawal selia;
- Maklum balas pengguna dan amalan terbaik industri.

**Pemberitahuan perubahan:**

Apabila kami membuat perubahan **material** kepada Polisi (contohnya, perubahan dalam pembekal AI, pengumpulan jenis data baru, atau perubahan dalam tempoh pengekalan), kami akan memberitahu anda melalui:

- Emel kepada alamat emel berdaftar akaun anda; dan/atau
- Notis dalam dashboard BinaApp; dan/atau
- Pemberitahuan dalam aplikasi pada log masuk seterusnya.

Untuk perubahan kecil (contohnya, pembetulan tatabahasa, penjelasan teks), kami akan mengemas kini Polisi tanpa pemberitahuan langsung tetapi akan mencatatkan perubahan dalam seksyen Riwayat Perubahan.

**Tarikh berkuat kuasa:**

Versi terkini Polisi akan menyatakan tarikh berkuat kuasa pada bahagian atas dokumen. Sebarang perubahan akan berkuat kuasa pada tarikh tersebut, melainkan dinyatakan sebaliknya.

**Persetujuan berterusan:**

Penggunaan berterusan perkhidmatan BinaApp selepas perubahan kepada Polisi ini berkuat kuasa membentuk persetujuan anda kepada terma baru. Jika anda tidak bersetuju dengan perubahan, sila berhenti menggunakan perkhidmatan kami dan hubungi kami untuk memulakan proses pemadaman akaun.

**Riwayat versi:**

Lihat seksyen Riwayat Perubahan pada penghujung Polisi ini untuk butiran perubahan antara versi.`,
    },

    {
      id: 'hubungi-kami',
      title: '22. Hubungi Kami / Aduan',
      content: `**Untuk pertanyaan privasi atau permintaan PDPA:**

**Pegawai Perlindungan Data (DPO) BinaApp**
Emel: **admin@binaapp.my**

Sila gunakan emel ini untuk:
- Permintaan akses, pembetulan, pemadaman, mudah alih, atau hadkan pemprosesan;
- Penarikan persetujuan;
- Pertanyaan tentang amalan privasi kami;
- Aduan tentang pengendalian data anda.

**Untuk sokongan teknikal am:**

Emel: **support.team@binaapp.my**

**Maklumat syarikat:**

Ezy Work Asia Solution
No. SSM: 002944700-D
(Alamat surat-menyurat akan disediakan dalam kemas kini akan datang.)

**Untuk membuat aduan kepada pihak berkuasa:**

Jika anda tidak berpuas hati dengan respons kami terhadap aduan privasi anda, atau jika anda percaya kami telah melanggar PDPA 2010, anda mempunyai hak untuk membuat aduan kepada:

**Jabatan Perlindungan Data Peribadi (JPDP) Malaysia**
- Talian Aduan: **1-300-88-2400**
- Laman web: **www.pdp.gov.my**
- Saluran rasmi untuk aduan PDPA di Malaysia.

**Tempoh tindak balas:**

Kami komited untuk memberi tindak balas kepada semua pertanyaan privasi dalam **tempoh 21 hari** dari tarikh penerimaan, mengikut Seksyen 7 PDPA 2010. Untuk permintaan yang lebih kompleks, kami akan memaklumkan jika masa tambahan diperlukan.`,
    },

    {
      id: 'bahasa-muktamad',
      title: '23. Bahasa Muktamad',
      content: `Polisi ini disediakan dalam dua bahasa: **Bahasa Malaysia (BM)** dan **Bahasa Inggeris (EN)**.

**Versi Bahasa Malaysia Polisi ini adalah versi muktamad dan berkuat kuasa.**

Sekiranya terdapat sebarang percanggahan, perbezaan tafsiran, atau ketidakselarasan antara versi Bahasa Malaysia dan terjemahan Bahasa Inggeris, **versi Bahasa Malaysia akan diguna pakai dan mengatasi versi Bahasa Inggeris**.

Versi Bahasa Inggeris disediakan sebagai kemudahan terjemahan sahaja, untuk membantu pengguna yang lebih selesa dengan Bahasa Inggeris memahami terma-terma. Ia tidak membentuk dokumen undang-undang berasingan.

Sebarang versi terjemahan lain (jika dilancarkan pada masa hadapan, contohnya Bahasa Cina atau Tamil) juga adalah untuk kemudahan sahaja, dan versi Bahasa Malaysia tetap mengatasi.`,
    },

    {
      id: 'persetujuan',
      title: '24. Persetujuan',
      content: `Dengan:

- Mendaftar akaun merchant BinaApp;
- Log masuk dan menggunakan dashboard BinaApp;
- Menggunakan ciri-ciri AI kami;
- Melayari laman web yang dihos oleh BinaApp; atau
- Berinteraksi dengan platform kami dalam apa jua cara,

**anda mengakui bahawa:**

1. Anda telah membaca dan memahami Polisi Privasi ini dalam keseluruhannya;
2. Anda bersetuju dengan pengumpulan, penggunaan, pendedahan, penyimpanan, dan pemindahan data peribadi anda seperti yang diterangkan dalam Polisi ini;
3. Anda bersetuju dengan pemindahan data merentas sempadan kepada pembekal AI dan infrastruktur kami di Singapura, Amerika Syarikat, dan Republik Rakyat China;
4. Anda mengakui hak anda di bawah PDPA 2010 dan tahu cara menjalankan hak tersebut;
5. Jika anda adalah merchant, anda mengesahkan tanggungjawab anda sebagai pengawal data untuk data customer dan data pihak ketiga lain yang anda muat naik.

Jika anda **tidak bersetuju** dengan mana-mana terma dalam Polisi ini, anda mesti:

- Berhenti menggunakan perkhidmatan BinaApp dengan segera;
- Hubungi kami di admin@binaapp.my untuk memulakan proses pemadaman akaun anda dan data berkaitan.`,
    },

    {
      id: 'riwayat-perubahan',
      title: '25. Riwayat Perubahan / Version History',
      content: `Berikut adalah sejarah versi Polisi Privasi BinaApp. Sila lihat senarai changelog di bawah untuk butiran perubahan antara versi.

**Cara membaca changelog:**

Setiap kemas kini versi disenaraikan dengan nombor versi, tarikh, dan ringkasan perubahan material. Perubahan kecil seperti pembetulan tatabahasa atau penjelasan teks tidak disenaraikan secara individu.

**Versi semasa:** v3.0 (21 Mei 2026)

**Versi terdahulu boleh diminta** dengan menghubungi admin@binaapp.my jika anda ingin meninjau versi sebelumnya.`,
    },
  ],

  changelog: [
    {
      version: '3.0',
      date: '21 Mei 2026',
      changes: [
        'Penstrukturan semula lengkap mengikut model berasaskan tujuan (purpose-based), inspirasi foodpanda Malaysia;',
        'Penambahan ringkasan 1-minit (executive summary) di permulaan;',
        'Penambahan jadual terperinci pembekal AI (8 ciri × vendor, wilayah, data, risiko PII, status persetujuan);',
        'Pendedahan eksplisit bahawa BinaApp TIDAK memproses pembayaran pesanan makanan customer (Seksyen 9);',
        'Pendedahan eksplisit bahawa pautan WhatsApp adalah deep-link sahaja (Seksyen 10);',
        'Seksyen baru tentang penjejakan pelawat laman web restoran (Seksyen 11) dan toggle opt-out per-website untuk merchant;',
        'Seksyen baru "Notis kepada Pengguna Akhir" untuk pelawat laman web (Seksyen 12);',
        'Pendedahan eksplisit bahawa BinaApp tidak menggunakan SDK analitis pihak ketiga (tiada Google Analytics, PostHog, dll.);',
        'Jadual tempoh pengekalan data yang menyeluruh (Seksyen 14, 12 baris);',
        'Restrukturisasi hak PDPA mengikut model foodpanda (6 hak khusus, Seksyen 15);',
        'Pendedahan terperinci pemindahan merentas sempadan dengan setiap pembekal dan wilayah (Seksyen 16);',
        'Penjelasan tanggungjawab merchant untuk data customer di bawah 18 tahun (Seksyen 17);',
        'Klausa baru tentang data pihak ketiga yang dimuat naik oleh merchant (Seksyen 18);',
        'Pendedahan pembuatan keputusan algoritmik AI dengan hak semakan manual (Seksyen 19);',
        'Komitmen 60-hari formal untuk UI persetujuan AI, banner kuki, dan sokongan DNT (Seksyen 20);',
        'Penambahan klausa bahasa muktamad yang menetapkan BM sebagai versi yang mengatasi (Seksyen 23);',
        'Penambahan butiran Ezy Work Asia Solution dengan No. SSM 002944700-D;',
        'Kemas kini DPO emel kepada admin@binaapp.my;',
        'Pembuangan rujukan kepada pembekal AI lapuk (GLM dialih keluar daripada platform);',
        'Pembuangan rujukan kepada pemproses pembayaran lapuk (FPX placeholder dialih keluar daripada platform).',
      ],
    },
    {
      version: '2.0',
      date: '31 Januari 2025',
      changes: [
        'Penambahan pendedahan tentang penggunaan AI generatif;',
        'Penambahan butiran sistem penghantaran;',
        'Pengemaskinian senarai pemproses pembayaran;',
        'Pengemaskinian butiran kontak.',
      ],
    },
    {
      version: '1.0',
      date: 'Awal 2024',
      changes: ['Versi awal Polisi Privasi pada pelancaran BinaApp.'],
    },
  ],

  contact: {
    company: 'Ezy Work Asia Solution',
    ssm: '002944700-D',
    dpoEmail: 'admin@binaapp.my',
    supportEmail: 'support.team@binaapp.my',
    pdpDeptPhone: '1-300-88-2400',
    pdpDeptWebsite: 'www.pdp.gov.my',
  },

  prevailingLanguage: {
    title: 'Bahasa Muktamad',
    content: `Versi Bahasa Malaysia Polisi ini adalah versi muktamad. Sekiranya terdapat percanggahan antara versi Bahasa Malaysia dan terjemahan Bahasa Inggeris, versi Bahasa Malaysia akan diguna pakai.`,
  },
};
