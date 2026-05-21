/**
 * BinaApp Terms of Service v3.0 — Bahasa Malaysia (prevailing version)
 *
 * Source-of-truth content for the BM Terms of Service. Consumed by the
 * terms rendering components built in Step 3e. Per s24
 * (`prevailingLanguage`), the BM version controls if there is any
 * conflict with the EN translation built in Step 3d.
 *
 * Effective: 21 Mei 2026. Supersedes v2.0 (31 Januari 2025) and v1.0.
 *
 * Maintenance notes:
 * - When updating, bump `version`, update `lastUpdated`, append a new
 *   changelog entry. Do NOT silently edit historical changelog rows.
 * - Word count drives `estimatedReadingMinutes` (200 wpm BM average).
 * - Tables (tier pricing, addons, quota, third-party services) live as
 *   structured arrays on the relevant section; the renderer maps them
 *   to HTML tables.
 *
 * Type structure intentionally duplicates the privacy-policy types
 * rather than importing from a shared file — kept self-contained per
 * Step 3c guidance. If a third legal doc is added later, refactor
 * shared types out at that point.
 */

export type TierRow = {
  tier: string;
  price: string;
  features: string[];
};

export type AddonRow = {
  addonType: string;
  price: string;
  expiry: string;
  refundPolicy: string;
};

export type QuotaRow = {
  limitType: string;
  free: string;
  starter: string;
  basic: string;
  pro: string;
};

export type ThirdPartyRow = {
  service: string;
  region: string;
  purpose: string;
  policyUrl: string;
};

export type TermsSection = {
  id: string;
  title: string;
  content: string;
  tierTable?: TierRow[];
  addonTable?: AddonRow[];
  quotaTable?: QuotaRow[];
  thirdPartyTable?: ThirdPartyRow[];
};

export type ChangelogEntry = {
  version: string;
  date: string;
  changes: string[];
};

export type LegalContact = {
  company: string;
  ssm: string;
  dpoEmail: string;
  supportEmail: string;
  generalEmail: string;
  pdpDeptPhone: string;
  pdpDeptWebsite: string;
};

export type TermsOfService = {
  version: string;
  effectiveDate: string;
  lastUpdated: string;
  estimatedReadingMinutes: number;
  executiveSummary: { title: string; content: string };
  businessModelCallout: { title: string; content: string };
  introduction: { title: string; content: string };
  sections: TermsSection[];
  changelog: ChangelogEntry[];
  contact: LegalContact;
  prevailingLanguage: { title: string; content: string };
};

export const termsBM: TermsOfService = {
  version: '3.0',
  effectiveDate: '21 Mei 2026',
  lastUpdated: '21 Mei 2026',
  estimatedReadingMinutes: 43,

  executiveSummary: {
    title: 'Ringkasan 1-Minit',
    content: `Ringkasan ini adalah untuk rujukan pantas sahaja dan **bukan** menggantikan Terma penuh di bawah. Sila baca seksyen-seksyen yang berkaitan untuk butiran lengkap.

- **Apa BinaApp ialah:** Platform SaaS pembina laman web AI untuk perniagaan F&B di Malaysia. **Bukan** platform penghantaran makanan, **bukan** rangkaian restoran, **bukan** majikan rider.
- **Pelan langganan:** Free (RM 0, tera air & mod pratonton), Starter (RM 5/bulan), Basic (RM 29/bulan), Pro (RM 49/bulan). Pembaharuan auto setiap bulan, boleh batal bila-bila masa, tiada refund pro-rata mid-cycle.
- **Addon:** Slot tambahan untuk had tertentu (laman web, AI hero, AI imej, slot rider, zon penghantaran). Sah selama 365 hari. Belum digunakan boleh direfund dalam 7 hari pembelian.
- **Apa anda bertanggungjawab:** Kandungan menu, ketepatan harga, keselamatan makanan, lesen perniagaan (SSM, halal, food handling), kewajipan kepada rider yang anda lantik, dan integriti data customer yang anda muat naik.
- **Apa BinaApp TIDAK bertanggungjawab:** Kualiti makanan, masa penghantaran, perselisihan customer-merchant, halusinasi AI yang tidak disemak, pembayaran customer yang tidak sampai melalui QR statik, dan tindakan rider semasa penghantaran.
- **Liabiliti:** Dihadkan kepada fi langganan 12 bulan (atau RM 100 untuk pengguna Pelan Free).
- **Pertikaian:** Tertakluk kepada undang-undang Malaysia. Mahkamah Kuala Lumpur mempunyai bidang kuasa eksklusif.
- **Privasi:** Pengumpulan dan pemprosesan data peribadi ditadbir oleh Polisi Privasi BinaApp (\`/polisi-privasi\`).`,
  },

  businessModelCallout: {
    title: 'Memahami Model Perniagaan BinaApp',
    content: `**Sila baca seksyen ini terlebih dahulu — ia membentuk asas pemahaman terma-terma seterusnya.**

**Apa BinaApp ialah:**

- Platform SaaS (Software-as-a-Service / Perisian-sebagai-Perkhidmatan) yang menyediakan alat untuk perniagaan F&B di Malaysia membina dan mengurus laman web mereka sendiri;
- Penyedia infrastruktur teknikal untuk dashboard merchant, sistem pesanan, pengurusan menu, dan operasi penghantaran;
- Pembekal pipeline AI untuk penjanaan kandungan (laman web, imej, balasan automatik, analisis aduan).

**Apa BinaApp BUKAN:**

- **BUKAN** platform penghantaran makanan (food delivery platform) seperti foodpanda, GrabFood, atau ShopeeFood;
- **BUKAN** rangkaian restoran, francais, atau pemegang inventori;
- **BUKAN** dapur awan (cloud kitchen) atau operator dapur;
- **BUKAN** pemproses pembayaran untuk pesanan makanan customer (kami hanya memproses pembayaran **langganan merchant** melalui ToyyibPay);
- **BUKAN** majikan, agensi pekerjaan, atau pengantara undang-undang untuk rider — rider adalah kontraktor bebas yang dilantik oleh merchant.

**Implikasi penting yang anda perlu fahami:**

- **Kontrak jual beli adalah antara customer dan merchant**, bukan dengan BinaApp. Customer membuat pembelian daripada merchant.
- **Wang pesanan makanan tidak melalui BinaApp pada bila-bila masa.** Pembayaran COD (Cash on Delivery) dibuat tunai terus kepada rider; pembayaran QR statik dipindahkan terus ke akaun bank merchant.
- **Sebarang aduan tentang kualiti makanan, ketepatan pesanan, masa penghantaran, atau perkhidmatan customer perlu dirujuk terus kepada merchant** — BinaApp tidak mempunyai kuasa untuk menyelesaikan pertikaian tersebut.
- **Rider yang menggunakan aplikasi web progresif \`/rider\` BinaApp adalah kontraktor bebas merchant** — BinaApp tidak menyediakan insurans, EPF, SOCSO, atau apa-apa hak pekerja kepada rider.

Dengan pemahaman ini sebagai asas, Terma-terma berikut menerangkan hak dan tanggungjawab setiap pihak.`,
  },

  introduction: {
    title: 'Pendahuluan',
    content: `Terma Perkhidmatan ini ("**Terma**") ialah perjanjian undang-undang antara anda ("**anda**", "**pengguna**", "**merchant**") dan **Ezy Work Asia Solution** (No. SSM: 002944700-D) yang menjalankan perniagaan sebagai "**BinaApp**" ("**kami**", "**kita**", "**BinaApp**").

Terma ini mengawal akses dan penggunaan anda kepada platform BinaApp, termasuk dashboard merchant, laman web yang dijana (dihos di subdomain \`*.binaapp.my\`), aplikasi web progresif untuk rider, sistem pesanan, dan semua perkhidmatan berkaitan yang disediakan oleh BinaApp ("**Perkhidmatan**").

Terma ini berkuat kuasa pada **21 Mei 2026** dan menggantikan semua versi terdahulu, termasuk Versi 2.0 (bertarikh 31 Januari 2025) dan Versi 1.0 (awal 2024). Lihat seksyen Riwayat Perubahan untuk butiran perubahan antara versi.

**Dengan mendaftar akaun, menggunakan Perkhidmatan, atau mengklik butang "Saya bersetuju" semasa pendaftaran, anda mengakui bahawa anda telah membaca, memahami, dan bersetuju untuk terikat dengan Terma ini.** Jika anda tidak bersetuju, sila berhenti menggunakan Perkhidmatan.`,
  },

  sections: [
    {
      id: 'penerangan-perkhidmatan',
      title: '1. Penerangan Perkhidmatan',
      content: `BinaApp ialah platform **Perisian-sebagai-Perkhidmatan (Software-as-a-Service / "SaaS")** yang dimiliki dan dikendalikan oleh **Ezy Work Asia Solution** (No. SSM: 002944700-D), sebuah perniagaan berdaftar di Malaysia.

Platform BinaApp menyediakan alat perisian berasaskan awan untuk membolehkan pemilik perniagaan F&B di Malaysia:

- **Menjana laman web restoran** melalui pipeline AI (penjanaan HTML, imej hero, imej menu);
- **Mengurus menu digital** dengan editor kandungan;
- **Menyediakan sistem pesanan dalam talian** dengan pelbagai kaedah pembayaran (COD, QR statik);
- **Menguruskan operasi penghantaran** melalui sistem pengirim (dispatcher) dan aplikasi web progresif untuk rider, termasuk penjejakan GPS dan pengesahan foto;
- **Berinteraksi dengan customer** melalui sistem chat dan resolusi aduan terbantu-AI;
- **Mengakses analitis pelawat** untuk memahami trafik laman web.

**Pendedahan penting — apa BinaApp ialah, dan apa ia bukan:**

BinaApp adalah **penyedia infrastruktur teknikal sahaja**. BinaApp **bukan**:

- Platform penghantaran makanan (food delivery platform);
- Rangkaian restoran atau pemegang francais;
- Penjual makanan, pemegang inventori, atau operator dapur;
- Pemproses pembayaran untuk pesanan makanan customer;
- Majikan, agensi pekerjaan, atau pengantara untuk rider.

Hubungan kontraktual untuk pesanan makanan ialah antara **customer dan merchant**. BinaApp menyediakan infrastruktur teknikal sahaja untuk memudahkan operasi tersebut. Sila lihat seksyen "Memahami Model Perniagaan BinaApp" di atas untuk pemahaman lengkap.`,
    },

    {
      id: 'definisi',
      title: '2. Definisi',
      content: `Dalam Terma ini, melainkan konteks menentukan sebaliknya:

- **"Addon"** bermaksud unit kuota tambahan yang dibeli secara berasingan daripada pelan langganan asas — contohnya, slot laman web tambahan, kredit imej AI tambahan, atau slot rider tambahan. Addon mempunyai tempoh sahlaku **365 hari** dari tarikh pembelian.

- **"AI" atau "Kecerdasan Buatan"** bermaksud sistem dan model pembelajaran mesin yang digunakan oleh BinaApp untuk menjana atau menganalisis kandungan, termasuk yang disediakan oleh pembekal pihak ketiga. Lihat **Polisi Privasi seksyen 6** untuk butiran lengkap pembekal AI yang digunakan.

- **"BinaApp"**, **"kami"**, **"kita"** bermaksud platform BinaApp, dimiliki dan dikendalikan oleh Ezy Work Asia Solution (No. SSM: 002944700-D).

- **"Customer" atau "Pelanggan"** bermaksud individu yang melayari laman web restoran yang dihos oleh BinaApp dan/atau membuat pesanan dengan merchant melalui laman web tersebut. Customer **bukan** pihak kontrak langsung dengan BinaApp.

- **"Kuota"** bermaksud had penggunaan yang dikuatkuasakan untuk setiap pelan langganan, contohnya bilangan laman web yang dibenarkan, item menu, imej AI sebulan, slot rider, atau zon penghantaran.

- **"Langganan"** bermaksud perkhidmatan berulang yang anda daftar dengan BinaApp, merangkumi Pelan Free, Starter, Basic, atau Pro.

- **"Merchant"**, **"anda"**, **"pengguna"** bermaksud pemilik perniagaan F&B (atau wakil yang diberi kuasa bagi perniagaan tersebut) yang mendaftar dan menggunakan akaun BinaApp.

- **"Pelan Free"** bermaksud pelan asas RM 0 dengan ciri-ciri terhad — tera air pada laman web, mod pratonton, dan kuota minimum.

- **"Penyedia AI" atau "Pembekal AI"** bermaksud syarikat pihak ketiga yang menyediakan model AI yang digunakan oleh BinaApp, termasuk **Stability AI**, **DeepSeek**, **Qwen (Alibaba Cloud International)**, dan **Anthropic**. Lihat Polisi Privasi seksyen 6 untuk butiran lengkap.

- **"Polisi Privasi"** bermaksud Polisi Privasi BinaApp yang terkini, boleh diakses di \`/polisi-privasi\`.

- **"QR Statik"** bermaksud imej kod QR pembayaran yang dimuat naik oleh merchant ke dashboard mereka — contohnya, QR DuitNow atau QR bank — yang dipaparkan kepada customer untuk memudahkan pemindahan pembayaran terus kepada akaun bank merchant. **BinaApp memaparkan imej sahaja dan tidak memproses pembayaran tersebut.**

- **"Rider" atau "Penghantar"** bermaksud individu yang dilantik oleh merchant untuk melaksanakan penghantaran pesanan customer. **Rider adalah kontraktor bebas yang terikat dengan merchant; rider BUKAN pekerja, ejen, kontraktor, atau wakil BinaApp.** BinaApp hanya menyediakan alat perisian untuk koordinasi penghantaran (dispatcher dashboard, PWA rider, penjejakan GPS).

- **"Subdomain"** bermaksud alamat web dengan format \`[namaperniagaan].binaapp.my\` yang diberikan kepada merchant sebagai lesen terhad untuk mengehoskan laman web restoran mereka.

- **"Terma"** bermaksud dokumen Terma Perkhidmatan ini, sebagaimana dikemas kini dari semasa ke semasa.`,
    },

    {
      id: 'kelayakan-akaun',
      title: '3. Kelayakan & Akaun',
      content: `**Syarat kelayakan untuk mendaftar:**

Untuk mendaftar dan menggunakan akaun BinaApp, anda mestilah:

- Berumur **sekurang-kurangnya 18 tahun**;
- Mempunyai kapasiti undang-undang untuk membentuk kontrak yang sah di sisi undang-undang Malaysia;
- Memiliki perniagaan F&B yang sah, atau merupakan wakil yang diberi kuasa bagi perniagaan tersebut dengan kebenaran membentuk kontrak bagi pihaknya;
- Tidak pernah disekat atau ditamatkan daripada platform BinaApp sebelum ini.

**Pendaftaran akaun:**

- Anda mesti menyediakan maklumat yang **tepat, lengkap, dan terkini** semasa pendaftaran;
- Anda bertanggungjawab untuk mengemas kini maklumat akaun jika ia berubah (contohnya, perubahan nombor telefon, perubahan butiran perniagaan);
- BinaApp boleh menolak permohonan pendaftaran tanpa memberikan sebab.

**Kelayakan akaun & keselamatan:**

- Anda bertanggungjawab untuk mengekalkan **kerahsiaan kata laluan** akaun anda;
- Anda **tidak boleh berkongsi kelayakan log masuk** dengan pihak yang tidak diizinkan;
- Anda bertanggungjawab untuk **semua aktiviti** yang berlaku di bawah akaun anda, sama ada diizinkan oleh anda atau tidak;
- Anda mesti **memaklumkan BinaApp dengan serta-merta** jika anda mengesyaki sebarang akses tidak diizinkan kepada akaun anda dengan menghantar emel kepada **admin@binaapp.my**.

**Hak BinaApp untuk menolak atau menamatkan:**

BinaApp berhak untuk menolak permohonan pendaftaran atau menamatkan akaun sedia ada jika:

- Maklumat yang diberikan adalah palsu, mengelirukan, atau tidak lengkap;
- Pengguna tidak memenuhi syarat kelayakan;
- Aktiviti pengguna melanggar Terma ini, Polisi Privasi, atau undang-undang Malaysia yang berkaitan.

**Berbilang akaun:**

Setiap perniagaan boleh mempunyai satu akaun utama. Penggunaan berbilang akaun untuk mengelakkan kuota atau mengaburi identiti perniagaan boleh menyebabkan penamatan semua akaun berkaitan.`,
    },

    {
      id: 'pelan-langganan',
      title: '4. Pelan Langganan & Pengebilan',
      content: `**4.1 Pelan Tersedia**

BinaApp menawarkan pelan langganan berikut. Sila lihat jadual pelan di bawah untuk butiran ciri-ciri setiap pelan.

Pelan Free membolehkan anda meneroka platform tanpa komitmen bayaran, tetapi dengan had kuota minimum dan **tera air "Dikuasakan oleh BinaApp"** pada laman web yang dijana. Pelan berbayar membuka kuota yang lebih tinggi dan menghilangkan tera air (kecuali jika anda secara eksplisit memilih untuk mengekalkannya).

**Harga boleh berubah:** Kami berhak untuk meminda harga pelan dari semasa ke semasa. Sebarang perubahan harga akan diberitahu kepada anda **sekurang-kurangnya 30 hari sebelum perubahan berkuat kuasa** melalui emel kepada alamat berdaftar akaun anda. Anda boleh memilih untuk membatalkan langganan sebelum perubahan harga berkuat kuasa tanpa penalti.

**4.2 Pembaharuan Auto (Auto-Renewal)**

- Langganan **diperbaharui secara automatik** setiap bulan pada tarikh yang sama dengan tarikh pendaftaran asal anda;
- Caj pembaharuan dikenakan melalui ToyyibPay menggunakan kaedah pembayaran yang anda telah konfigurasikan;
- Anda boleh **mematikan pembaharuan auto** pada bila-bila masa melalui tetapan dashboard. Apabila dimatikan, langganan anda akan tamat pada penghujung tempoh bil semasa, dan akaun akan diturunkan kepada Pelan Free (atau dipadam selepas tempoh penyimpanan, lihat seksyen 16).

**4.3 Kegagalan Pembayaran**

Jika pembayaran pembaharuan gagal (contohnya, baki tidak mencukupi, kad tamat tempoh), kitaran berikut akan berlaku:

- **Hari 1:** Percubaan semula automatik;
- **Hari 3:** Notifikasi peringatan dihantar kepada emel berdaftar anda;
- **Hari 7:** Akaun digantung — akses dashboard dihadkan, laman web yang diterbitkan kekal langsung tetapi dengan banner "Akaun digantung";
- **Hari 30:** Akaun **dipadam secara kekal** dan semua data berkaitan dipadam (tertakluk kepada tempoh sandaran 30 hari, lihat Polisi Privasi seksyen 14).

Untuk mengelakkan pemadaman, sila kemas kini kaedah pembayaran anda atau hubungi **support.team@binaapp.my** dalam tempoh 30 hari dari kegagalan pembayaran pertama.

**4.4 Addon**

Addon ialah unit kuota tambahan yang anda boleh beli secara berasingan untuk mengatasi had pelan langganan asas. Sila lihat jadual addon di bawah untuk jenis-jenis yang tersedia dan harganya.

**Polisi sahlaku & refund addon:**

- Addon adalah sah selama **365 hari** dari tarikh pembelian;
- Selepas tamat tempoh, **addon yang belum digunakan akan luput dan tidak boleh direfund**;
- **Addon yang telah digunakan (consumed) tidak boleh direfund** dalam apa-apa keadaan;
- **Addon yang belum digunakan boleh direfund dalam tempoh 7 hari** dari pembelian dengan menghantar emel ke **admin@binaapp.my** dengan subjek \`Refund Request - Addon\` dan butiran transaksi.

**Penggunaan addon:**

- Addon digabungkan dengan kuota pelan langganan anda secara **additive** (contohnya, jika pelan anda membenarkan 10 imej AI sebulan dan anda membeli 1 addon ai_image, anda mempunyai 11 imej untuk bulan itu);
- Addon **tidak diperbaharui secara automatik** — anda perlu membeli semula apabila tamat tempoh.

**4.5 Kuota & Penguatkuasaan**

Setiap pelan mempunyai had kuota khusus. Sila lihat jadual kuota di bawah untuk butiran had setiap pelan.

**Khusus untuk slot rider — semantik addon:**

Pelan Free, Starter, dan Basic mempunyai kuota slot rider **sifar** secara lalai. Untuk membenarkan rider, anda perlu membeli addon \`rider\` (RM 3 per slot, sah 365 hari). Pelan Pro mempunyai **10 slot rider asas** dan addon rider boleh dibeli untuk **menambah** lebih daripada 10 slot.

Formula adalah **additive**: kuota efektif rider = (had pelan asas) + (bilangan slot addon yang aktif).

**Tingkah laku apabila kuota habis:**

Apabila kuota mencapai had, fungsi yang berkaitan akan **disekat**. Anda mempunyai tiga pilihan:

- **(a) Tunggu sehingga set semula bulanan** — kuota bulanan (AI hero, AI imej) diset semula pada tarikh kitaran bil anda;
- **(b) Beli addon** untuk had tertentu (lihat seksyen 4.4);
- **(c) Naik taraf langganan** kepada pelan yang lebih tinggi.

**Pengukuran kuota:**

- Kuota bulanan (AI hero, AI imej) dikira berdasarkan bulan kalendar tempatan Malaysia (GMT+8);
- Kuota statik (laman web, item menu, slot rider, zon) dikira berdasarkan jumlah aktif pada bila-bila masa.`,
      tierTable: [
        {
          tier: 'Free',
          price: 'RM 0/bulan',
          features: [
            'Tera air "Dikuasakan oleh BinaApp" pada laman web',
            'Mod pratonton untuk eksperimen platform',
            '1 laman web',
            '20 item menu (per web)',
            '3 imej AI hero / bulan',
            '10 imej AI menu / bulan',
            '0 zon penghantaran (addon diperlukan)',
            '0 slot rider (addon diperlukan)',
            'Sokongan komuniti sahaja',
          ],
        },
        {
          tier: 'Starter',
          price: 'RM 5/bulan',
          features: [
            'Tanpa tera air',
            '1 laman web',
            '20 item menu (per web)',
            '1 imej AI hero / bulan',
            '5 imej AI menu / bulan',
            '1 zon penghantaran',
            '0 slot rider (addon diperlukan)',
            'Sokongan emel (respons 48-72 jam waktu perniagaan)',
          ],
        },
        {
          tier: 'Basic',
          price: 'RM 29/bulan',
          features: [
            'Tanpa tera air',
            '5 laman web',
            'Item menu tanpa had (per web)',
            '10 imej AI hero / bulan',
            '30 imej AI menu / bulan',
            '5 zon penghantaran',
            '0 slot rider (addon diperlukan)',
            'Sokongan emel (respons 24-48 jam waktu perniagaan)',
          ],
        },
        {
          tier: 'Pro',
          price: 'RM 49/bulan',
          features: [
            'Tanpa tera air',
            'Laman web tanpa had',
            'Item menu tanpa had',
            'Imej AI hero tanpa had',
            'Imej AI menu tanpa had',
            'Zon penghantaran tanpa had',
            '10 slot rider asas (addon untuk extend)',
            'Sokongan keutamaan (respons 12-24 jam waktu perniagaan)',
          ],
        },
      ],
      addonTable: [
        {
          addonType: 'ai_image (Imej AI Menu Tambahan)',
          price: 'RM 1 per kredit',
          expiry: '365 hari dari pembelian',
          refundPolicy: 'Belum digunakan: refund dalam 7 hari • Sudah digunakan: tiada refund',
        },
        {
          addonType: 'ai_hero (Imej AI Hero Tambahan)',
          price: 'RM 2 per kredit',
          expiry: '365 hari dari pembelian',
          refundPolicy: 'Belum digunakan: refund dalam 7 hari • Sudah digunakan: tiada refund',
        },
        {
          addonType: 'website (Slot Laman Web Tambahan)',
          price: 'RM 5 per slot',
          expiry: '365 hari dari pembelian',
          refundPolicy: 'Belum digunakan: refund dalam 7 hari • Sudah digunakan: tiada refund',
        },
        {
          addonType: 'rider (Slot Rider Tambahan)',
          price: 'RM 3 per slot',
          expiry: '365 hari dari pembelian',
          refundPolicy: 'Belum digunakan: refund dalam 7 hari • Sudah digunakan: tiada refund',
        },
        {
          addonType: 'zone (Slot Zon Penghantaran Tambahan)',
          price: 'RM 2 per slot',
          expiry: '365 hari dari pembelian',
          refundPolicy: 'Belum digunakan: refund dalam 7 hari • Sudah digunakan: tiada refund',
        },
      ],
      quotaTable: [
        {
          limitType: 'Bilangan laman web',
          free: '1',
          starter: '1',
          basic: '5',
          pro: 'Tanpa had',
        },
        {
          limitType: 'Item menu (per laman web)',
          free: '20',
          starter: '20',
          basic: 'Tanpa had',
          pro: 'Tanpa had',
        },
        {
          limitType: 'Imej AI hero / bulan',
          free: '3',
          starter: '1',
          basic: '10',
          pro: 'Tanpa had',
        },
        {
          limitType: 'Imej AI menu / bulan',
          free: '10',
          starter: '5',
          basic: '30',
          pro: 'Tanpa had',
        },
        {
          limitType: 'Zon penghantaran',
          free: '0 (addon diperlukan)',
          starter: '1',
          basic: '5',
          pro: 'Tanpa had',
        },
        {
          limitType: 'Slot rider',
          free: '0 (addon diperlukan)',
          starter: '0 (addon diperlukan)',
          basic: '0 (addon diperlukan)',
          pro: '10 (addon untuk extend)',
        },
      ],
    },

    {
      id: 'pembatalan-refund',
      title: '5. Pembatalan & Refund Langganan',
      content: `**Pembatalan langganan:**

Anda boleh membatalkan langganan pada **bila-bila masa** melalui tetapan dashboard ("Akaun" → "Langganan" → "Batal Langganan") atau dengan menghantar emel kepada **support.team@binaapp.my**.

**Kesan pembatalan:**

- Langganan kekal aktif **sehingga penghujung tempoh bil semasa** yang telah dibayar;
- Selepas tempoh tersebut, akaun anda akan **diturunkan kepada Pelan Free** (atau dipadam selepas tempoh penyimpanan jika anda memilih pemadaman penuh, lihat seksyen 16);
- Tidak ada **refund pro-rata mid-cycle** — jika anda membatalkan pada hari ke-15 daripada kitaran 30 hari, anda kekal mempunyai akses sehingga hari ke-30 tetapi tidak menerima refund untuk 15 hari yang baki;
- Data merchant anda kekal terjamin selama **30 hari selepas penurunan kepada Pelan Free** atau pemadaman akaun (sebagai sandaran kecemasan), kemudian dipadam secara kekal.

**Refund untuk langganan:**

Sebagai polisi umum, **tidak ada refund untuk fi langganan yang telah dibayar**, kecuali:

- **Bil silap (billing error)** yang disahkan — kami akan memulangkan caj yang salah;
- **Pelanggaran material Terma ini oleh BinaApp** yang menjejaskan keupayaan anda untuk menggunakan Perkhidmatan secara material — refund pro-rata mungkin diberikan mengikut budi bicara kami;
- **Kewajipan undang-undang** yang menghendaki kami mengeluarkan refund.

Untuk meminta refund, hantarkan emel kepada **admin@binaapp.my** dengan subjek \`Refund Request - Subscription\` beserta butiran transaksi dan alasan permintaan dalam tempoh **7 hari** dari pembayaran.

**Refund untuk addon:**

Sila lihat seksyen 4.4 untuk polisi refund addon (rangkaian: belum digunakan + dalam 7 hari = refund; sudah digunakan = tiada refund; tamat 365 hari = tiada refund).

**Refund untuk pesanan makanan:**

**BinaApp tidak memproses pembayaran customer untuk pesanan makanan** (lihat callout model perniagaan di atas). Oleh itu:

- **Refund untuk pesanan makanan adalah polisi merchant sendiri** — BinaApp tiada kuasa untuk memulakan refund tersebut;
- Customer yang ingin meminta refund untuk pesanan makanan perlu **menghubungi merchant secara terus**;
- Untuk pesanan COD: refund melibatkan customer dan merchant secara terus (tunai);
- Untuk pesanan QR statik: refund melibatkan customer dan merchant melalui pemindahan bank;
- BinaApp boleh menyediakan **catatan pesanan dan log chat** sebagai bukti kepada mana-mana pihak yang relevan jika diminta, tetapi tidak boleh mengeluarkan refund sendiri.`,
    },

    {
      id: 'tanggungjawab-pengguna',
      title: '6. Tanggungjawab Pengguna (Aktiviti Larangan)',
      content: `Anda bersetuju untuk **tidak**, dan tidak akan membenarkan mana-mana pihak ketiga untuk, melakukan mana-mana aktiviti berikut semasa menggunakan Perkhidmatan:

**(a) Pelanggaran teknikal:**

- Melakukan **reverse engineering, decompile, disassemble**, atau cuba mendapatkan kod sumber Perkhidmatan;
- Menjalankan **automated scraping, crawling, atau bot** untuk mengekstrak data daripada platform tanpa kebenaran bertulis;
- **Mengaburi atau memintas** sistem kuota, had kadar (rate limits), atau langkah keselamatan;
- **Memuat naik malware, virus, worm, trojan, atau kod berbahaya** lain kepada platform.

**(b) Pelanggaran komersial:**

- **Menjual semula, menyub-lesen, atau menyewa** akses kepada Perkhidmatan kepada pihak ketiga tanpa perjanjian bertulis dengan BinaApp;
- **Berkongsi kelayakan akaun** dengan individu yang tidak diizinkan;
- Menggunakan Perkhidmatan untuk **menyediakan perkhidmatan kompetitif** yang menyalin atau mereplikasi fungsi BinaApp;
- Mendaftar **berbilang akaun** untuk mengelakkan kuota atau mengaburi identiti perniagaan.

**(c) Pelanggaran kandungan:**

- Menggunakan Perkhidmatan untuk menjual atau mempromosikan produk yang **tidak halal atau haram** di Malaysia, termasuk: alkohol (kepada pengguna Muslim), produk khinzir (kepada premis halal), judi, dadah terlarang, atau produk yang menyalahi undang-undang Malaysia;
- Memuat naik kandungan yang **palsu, mengelirukan, atau menipu** customer (contohnya, harga palsu, gambar produk yang menipu, ulasan palsu);
- Memuat naik kandungan yang **melanggar hak harta intelek** pihak ketiga (logo, gambar berhak cipta, tanda dagangan);
- Menggunakan Perkhidmatan untuk **spam, harassment, ancaman, atau penyalahgunaan** customer, rider, atau pengguna lain;
- Memuat naik kandungan yang **lucah, ganas, atau menyalahi peraturan kandungan** Malaysia.

**(d) Pelanggaran data:**

- Memuat naik data customer atau pihak ketiga **tanpa persetujuan yang sewajarnya** (sila lihat Polisi Privasi seksyen 18 untuk tanggungjawab anda);
- **Menyalahgunakan data customer** untuk tujuan yang tidak diizinkan (contohnya, menjual senarai customer kepada pengiklan tanpa persetujuan).

**(e) Pelanggaran kewangan:**

- Menggunakan Perkhidmatan untuk **pengubahan wang haram (money laundering)**, **penipuan**, atau aktiviti kewangan yang menyalahi undang-undang;
- Menyediakan **maklumat pembayaran palsu** atau menggunakan kad/akaun yang dicuri.

**Akibat pelanggaran:**

Pelanggaran mana-mana aktiviti larangan di atas boleh menyebabkan:

- **Amaran bertulis** untuk pelanggaran ringan;
- **Penggantungan akaun** untuk pelanggaran sederhana;
- **Penamatan akaun serta-merta tanpa refund** untuk pelanggaran serius atau berulang;
- **Pemulaan rujukan kepada pihak berkuasa Malaysia** untuk pelanggaran undang-undang;
- **Tuntutan undang-undang** untuk kerosakan yang dialami oleh BinaApp atau pihak ketiga.`,
    },

    {
      id: 'tanggungjawab-merchant',
      title: '7. Tanggungjawab Khusus Merchant',
      content: `Sebagai merchant yang menggunakan Perkhidmatan untuk perniagaan F&B anda, anda bertanggungjawab sepenuhnya untuk:

**(a) Ketepatan menu & harga:**

- Memastikan **kandungan menu, harga, dan deskripsi produk adalah tepat dan terkini**;
- Mengemas kini menu apabila item tidak tersedia (out of stock);
- Memastikan harga yang dipaparkan kepada customer adalah harga sebenar yang akan dikenakan.

**(b) Keselamatan & kualiti makanan:**

- Mematuhi **piawaian keselamatan makanan** Malaysia (Akta Makanan 1983, Peraturan-Peraturan Kebersihan Makanan 2009);
- Mengekalkan **standard kebersihan** dapur dan ruang penyediaan;
- Menyimpan dan menghantar makanan pada **suhu yang sesuai** untuk mengelakkan pencemaran;
- **BinaApp tidak menjalankan pemeriksaan kebersihan, kualiti, atau keselamatan makanan anda** — ini adalah tanggungjawab eksklusif anda sebagai merchant.

**(c) Lesen perniagaan:**

Anda bertanggungjawab untuk memperoleh dan mengekalkan semua lesen, permit, dan pendaftaran yang diperlukan untuk operasi perniagaan F&B di Malaysia, termasuk tetapi tidak terhad kepada:

- **Pendaftaran perniagaan SSM** (Suruhanjaya Syarikat Malaysia);
- **Lesen makanan dan minuman** pihak berkuasa tempatan (PBT);
- **Sijil halal JAKIM** (jika anda mempromosikan produk sebagai halal);
- **Sijil pengendalian makanan** untuk pekerja yang mengendalikan makanan;
- **Pendaftaran cukai (SST)** jika berkenaan.

BinaApp tidak akan mengesahkan atau memantau status lesen anda. Kami berhak untuk menggantung akaun jika kami mendapat aduan tentang operasi tanpa lesen.

**(d) Pemenuhan pesanan:**

- **Memenuhi pesanan customer dalam masa yang munasabah** sebagaimana yang dijanjikan pada laman web anda;
- **Berkomunikasi dengan customer** mengenai kelewatan, pembatalan, atau item tidak tersedia;
- **Mengendalikan aduan customer** secara profesional dan tepat pada masanya.

**(e) Integriti data customer:**

- **Memastikan ketepatan data customer** yang dimasukkan ke dalam platform;
- Mendapatkan **persetujuan yang sewajarnya** daripada customer sebelum memuat naik data peribadi mereka (sila lihat **Polisi Privasi seksyen 18** untuk butiran kewajipan anda sebagai pengawal data);
- **Menjawab permintaan PDPA daripada customer** dengan tepat pada masanya (akses, pembetulan, pemadaman data peribadi mereka).

**Merchant bertanggungjawab penuh untuk integriti data customer yang dimasukkan ke BinaApp.** BinaApp bertindak sebagai pemproses data sahaja.

**(f) Kewajipan kepada rider:**

Jika anda melantik rider untuk operasi penghantaran melalui sistem BinaApp:

- Anda bertanggungjawab untuk **kontrak undang-undang dengan rider** (sebagai kontraktor bebas atau pekerja, mengikut struktur yang anda pilih);
- Anda bertanggungjawab untuk **bayaran kepada rider** (BinaApp tidak memproses bayaran rider);
- Anda bertanggungjawab untuk **insurans, perlindungan keselamatan**, dan kewajipan undang-undang lain berkaitan rider (BinaApp tidak menyediakan insurans rider);
- Sila lihat seksyen 9 untuk butiran lanjut.`,
    },

    {
      id: 'notis-pengguna-akhir',
      title: '8. Notis kepada Pengguna Akhir (End-User Notice)',
      content: `**Seksyen ini adalah notis maklumat dan bukan kewajipan binding bagi customer.**

Customer yang melayari laman web restoran yang dihos oleh BinaApp (contohnya, \`[namaperniagaan].binaapp.my\`) adalah **bukan pihak kontrak langsung dengan BinaApp**.

**Hubungan kontraktual untuk pesanan makanan:**

- Apabila customer membuat pesanan, **kontrak jual beli adalah antara customer dan merchant**;
- **BinaApp menyediakan infrastruktur teknikal sahaja** — BinaApp bukan penjual, pengantara komersial, atau pihak kepada urus niaga jual beli;
- **Sebarang tuntutan, aduan, atau permintaan refund untuk pesanan makanan perlu dirujuk terus kepada merchant**, bukan BinaApp.

**Pengumpulan data customer:**

Apabila customer memasukkan data peribadi mereka melalui laman web (contohnya, nama, nombor telefon, alamat penghantaran), data tersebut dikumpul **bagi pihak merchant**. **Merchant ialah pengawal data utama** untuk data customer mereka, dan BinaApp bertindak sebagai pemproses data.

Sila lihat **Polisi Privasi seksyen 12** untuk butiran lengkap tentang pengumpulan data pelawat dan hak privasi customer.

**Hak customer:**

- Untuk hak akses, pembetulan, atau pemadaman data peribadi mereka, customer hendaklah menghubungi **merchant secara langsung**;
- Jika merchant tidak memberi respons, customer boleh menghubungi BinaApp di **admin@binaapp.my** dan kami akan memudahkan permintaan tersebut kepada merchant;
- Customer juga mempunyai hak untuk membuat aduan kepada **Jabatan Perlindungan Data Peribadi Malaysia** (1-300-88-2400, www.pdp.gov.my).

**Tujuan notis ini:**

Notis ini disediakan untuk menjelaskan model perniagaan BinaApp kepada customer. Ia **tidak membentuk obligasi kontraktual** yang boleh dikuatkuasakan oleh BinaApp terhadap customer. Customer **tidak perlu menerima Terma ini** untuk membuat pesanan makanan, kerana kontrak jual beli adalah dengan merchant, bukan BinaApp.`,
    },

    {
      id: 'disclaimer-penghantaran',
      title: '9. Disclaimer Operasi Penghantaran',
      content: `**Pendedahan penting tentang status rider:**

Rider yang menggunakan aplikasi web progresif \`/rider\` BinaApp untuk melaksanakan penghantaran adalah **kontraktor bebas yang dilantik oleh merchant**, dan **BUKAN**:

- Kakitangan BinaApp;
- Kontraktor BinaApp;
- Ejen atau wakil BinaApp;
- Pengantara antara BinaApp dan merchant.

**Apa BinaApp sediakan kepada rider:**

BinaApp hanya menyediakan **alat perisian teknikal** kepada rider untuk koordinasi penghantaran, iaitu:

- Aplikasi web progresif (\`/rider\`) untuk menerima tugasan penghantaran;
- Penjejakan GPS semasa penghantaran aktif (untuk dipaparkan kepada merchant dan customer);
- Antara muka untuk memuat naik foto bukti penghantaran;
- Saluran komunikasi dengan dispatcher merchant.

**Apa BinaApp TIDAK sediakan kepada rider:**

- **Insurans kemalangan, perubatan, atau jaminan kewangan** untuk rider;
- **Caruman EPF (KWSP), SOCSO, atau EIS**;
- **Gaji, komisen, bonus, atau apa-apa bayaran** kepada rider;
- **Latihan keselamatan jalan raya** atau persijilan rider;
- **Perlindungan undang-undang pekerja** seperti yang termaktub di bawah Akta Kerja 1955.

**Hubungan undang-undang rider:**

Hubungan undang-undang rider adalah **eksklusif dengan merchant yang melantik mereka**, dan tertakluk kepada perjanjian antara mereka (lisan atau bertulis). Merchant bertanggungjawab untuk:

- Membuat **kontrak yang sah** dengan rider (kontraktor bebas atau pekerja);
- Membayar **pampasan yang dipersetujui** kepada rider;
- Menyediakan **insurans yang sesuai** untuk rider (kemalangan, liabiliti pihak ketiga, dll.);
- Mematuhi **kewajipan undang-undang** Malaysia berkaitan dengan struktur pekerjaan yang dipilih (EPF/SOCSO jika pekerja, status kontraktor bebas yang betul jika berkenaan).

**Tanggungjawab atas tindakan rider:**

BinaApp **tidak bertanggungjawab** atas:

- Kemalangan, kecederaan, atau kematian rider semasa penghantaran;
- Kerosakan kepada kenderaan, harta benda, atau pihak ketiga akibat tindakan rider;
- Pelanggaran undang-undang trafik oleh rider;
- Kecurian, kemalangan, atau kelewatan pesanan oleh rider;
- Tindakan tidak profesional atau menyalahi undang-undang oleh rider.

**Liabiliti penuh untuk semua perkara di atas terletak pada merchant yang melantik rider, dan/atau rider sendiri sebagai kontraktor bebas, mengikut perjanjian mereka.**`,
    },

    {
      id: 'disclaimer-qr-statik',
      title: '10. Disclaimer QR Statik',
      content: `**Pendedahan penting tentang QR Statik:**

Jika merchant memilih untuk membenarkan pembayaran melalui **QR Statik** (kod QR pembayaran seperti DuitNow QR atau QR bank), merchant memuat naik imej QR ke dashboard mereka. Imej QR ini kemudian dipaparkan kepada customer pada laman web restoran atau pada skrin pesanan.

**Apa BinaApp lakukan dengan QR Statik:**

- **Memaparkan imej QR** kepada customer pada masa pesanan;
- Menyimpan imej QR dalam dashboard merchant untuk kemudahan akses.

**Apa BinaApp TIDAK lakukan dengan QR Statik:**

- **TIDAK mengesahkan ketulenan** kod QR (kami tidak mengimbas atau mengesahkan bahawa QR sebenarnya pergi ke akaun merchant);
- **TIDAK menjamin** bahawa pembayaran sampai kepada akaun bank merchant;
- **TIDAK memproses, menerima, atau memegang** wang pembayaran customer;
- **TIDAK merekod** butiran transaksi pembayaran (BinaApp hanya merekod status pesanan: dibayar / belum dibayar);
- **TIDAK mengeluarkan resit** untuk pembayaran customer (resit dikeluarkan oleh bank atau aplikasi pembayaran customer).

**Tanggungjawab merchant:**

- **Memastikan imej QR yang dimuat naik adalah QR sah** yang dimiliki oleh anda atau perniagaan anda;
- **Menyemak resit pembayaran customer** (contohnya, melalui notifikasi bank atau aplikasi pembayaran) sebelum mengesahkan status pesanan sebagai "dibayar";
- **Menyelesaikan sebarang pertikaian pembayaran** dengan customer secara terus.

**Disclaimer penuh:**

BinaApp **tidak bertanggungjawab** untuk:

- Customer membuat pemindahan ke **akaun salah** (contohnya, kerana QR ditukar atau diceroboh);
- Customer **mendakwa telah membayar** tetapi pemindahan tidak diterima oleh merchant;
- **Penipuan QR** oleh pihak ketiga (contohnya, QR palsu yang ditampal di atas QR sah);
- **Caj overdraft, yuran transaksi**, atau kos kewangan lain yang dialami oleh customer atau merchant.

Sebarang pertikaian pembayaran QR Statik adalah **antara customer dan merchant** dan diselesaikan secara terus antara mereka, atau melalui bank/penyedia pembayaran customer. BinaApp boleh membantu dengan menyediakan **catatan pesanan dan log chat** sebagai bukti, tetapi tidak boleh membuat keputusan pertikaian atau memulakan refund.`,
    },

    {
      id: 'disclaimer-ai',
      title: '11. Disclaimer Kandungan AI',
      content: `BinaApp menggunakan AI generatif dan AI analitis untuk menyediakan ciri-ciri seperti:

- Penjanaan HTML laman web;
- Penjanaan imej menu dan hero;
- Penjanaan teks balasan dalam chat customer-merchant;
- Analisis aduan dan cadangan tindakan refund;
- Pengesahan foto bukti penghantaran.

**Disclaimer penuh tentang kandungan AI:**

Kandungan yang dijana oleh AI disediakan **"sebagaimana adanya" (as-is)** tanpa jaminan ketepatan, kesesuaian, atau kebolehgunaan untuk tujuan tertentu. AI **boleh menghasilkan**:

- **Halusinasi (fakta palsu)** — contohnya, butiran perniagaan yang tidak tepat dalam HTML yang dijana;
- **Kandungan tidak sesuai budaya** — contohnya, imej atau teks yang tidak menghormati nilai-nilai tempatan Malaysia;
- **Bahasa yang tidak tepat** — contohnya, tatabahasa BM yang salah, penggunaan loghat yang tidak sesuai;
- **Cadangan refund yang tidak tepat** — analisis aduan AI hanya cadangan; keputusan akhir terletak pada merchant;
- **Foto bukti penghantaran yang tersalah disahkan** — AI boleh tersalah mengesahkan foto kabur atau foto yang tidak sah sebagai sah, atau sebaliknya.

**Tanggungjawab merchant:**

Merchant **bertanggungjawab penuh untuk menyemak dan meluluskan semua kandungan AI sebelum:**

- Menerbitkan laman web kepada customer;
- Menghantar mesej balasan kepada customer;
- Membuat keputusan refund berdasarkan cadangan AI;
- Mengesahkan penghantaran berdasarkan hasil pengesahan foto AI.

**Hak harta intelek kandungan AI:**

- BinaApp **tidak menjamin** bahawa kandungan yang dijana oleh AI **bebas daripada pelanggaran hak cipta pihak ketiga** — terutamanya untuk imej yang dijana, yang mungkin menyerupai karya berhak cipta sedia ada;
- Merchant **bertanggungjawab untuk pelanggaran hak cipta** yang timbul daripada penggunaan kandungan AI yang dijana;
- Untuk hak pemilikan kandungan AI, sila lihat seksyen 14.3.

**Pemindahan data kepada pembekal AI:**

Penggunaan ciri AI melibatkan pemindahan data kepada pembekal AI pihak ketiga (Stability AI, DeepSeek, Qwen, Anthropic). Lihat **Polisi Privasi seksyen 6 dan 16** untuk butiran pembekal, wilayah pemprosesan, dan risiko PII.

**Hak untuk menolak penggunaan AI:**

Jika anda tidak selesa dengan pemprosesan AI untuk mana-mana ciri tertentu, anda boleh:

- **Mengelakkan ciri tersebut** (contohnya, menguruskan aduan secara manual tanpa analisis AI);
- **Menghubungi kami** di admin@binaapp.my untuk membincangkan pilihan alternatif.`,
    },

    {
      id: 'pdpa-link',
      title: '12. Perlindungan Data Peribadi',
      content: `Pengumpulan, penggunaan, pendedahan, penyimpanan, dan pemprosesan data peribadi anda (sebagai merchant) dan data customer yang anda muat naik ke platform BinaApp ditadbir oleh **Polisi Privasi BinaApp**, yang boleh diakses di **\`/polisi-privasi\`**.

Dengan menggunakan Perkhidmatan, **anda bersetuju dengan terma-terma Polisi Privasi tersebut**, termasuk:

- Pendedahan data kepada pembekal AI pihak ketiga (Stability AI, DeepSeek, Qwen, Anthropic);
- Pemindahan data merentas sempadan kepada Singapura, Amerika Syarikat, dan Republik Rakyat China;
- Pengumpulan data analitis pertama-pihak (first-party) pada laman web yang dijana;
- Pemprosesan pembayaran langganan melalui ToyyibPay.

**Hak data subject anda di bawah PDPA 2010:**

Anda mempunyai hak akses, pembetulan, penarikan persetujuan, pemadaman, mudah alih, dan hadkan pemprosesan ke atas data peribadi anda. Hak-hak ini boleh dilaksanakan melalui kaedah yang dinyatakan dalam **Polisi Privasi seksyen 15**.

**Untuk pertanyaan privasi atau permintaan PDPA**, sila hantar emel kepada **admin@binaapp.my** dengan format yang dinyatakan dalam Polisi Privasi.

**Komitmen masa hadapan:**

BinaApp komited untuk meningkatkan amalan privasi melalui pelaksanaan UI persetujuan eksplisit untuk ciri-ciri AI yang mengandungi PII, banner kuki pada laman web restoran, dan sokongan untuk pengepala HTTP Do-Not-Track dalam tempoh **60 hari** dari tarikh berkuat kuasa Polisi Privasi (lihat **Polisi Privasi seksyen 20**).`,
    },

    {
      id: 'alat-perisian',
      title: '13. Alat Perisian & Ciri',
      content: `Perkhidmatan BinaApp merangkumi alat perisian dan ciri berikut:

**(a) Dashboard merchant:**
Antara muka utama untuk menguruskan akaun, langganan, laman web, menu, dan operasi.

**(b) Pipeline AI penjanaan kandungan:**
Penjanaan automatik laman web, imej, dan teks menggunakan empat pembekal AI utama. Lihat **Polisi Privasi seksyen 6** untuk butiran setiap pembekal.

**(c) Editor menu (\`/menu-designer\`):**
Alat untuk mereka bentuk dan menguruskan menu digital, termasuk kategori, item, harga, dan imej.

**(d) Sistem dispatcher penghantaran (\`/delivery\`):**
Antara muka untuk merchant menguruskan tugasan penghantaran kepada rider, melihat status penghantaran masa nyata, dan menyelesaikan isu.

**(e) Aplikasi web progresif rider (\`/rider\`):**
PWA yang dipasang pada peranti rider untuk menerima tugasan, mengemas kini status, memuat naik foto bukti penghantaran, dan berkomunikasi dengan dispatcher.

**(f) Penjejakan GPS:**
Sistem penjejakan lokasi rider semasa penghantaran aktif. Lihat **Polisi Privasi seksyen 5** untuk butiran pengumpulan data GPS.

**(g) Sistem chat customer-merchant:**
Saluran komunikasi terus antara customer dan merchant melalui antara muka chat dalam laman web restoran.

**(h) Sistem resolusi aduan berbantuan AI:**
Aliran kerja untuk menyelesaikan aduan customer, dengan cadangan tindakan (refund penuh, separa, atau tolak) yang dijana oleh AI untuk pertimbangan merchant.

**(i) Sistem addon:**
Pembelian unit kuota tambahan untuk laman web, imej AI, slot rider, dan zon penghantaran.

**(j) Analitis pelawat pertama-pihak:**
Penjejakan trafik laman web restoran untuk papan pemuka analitis merchant. Lihat **Polisi Privasi seksyen 11**.

**(k) BinaBot:**
Chatbot sokongan dalam dashboard untuk membantu merchant dengan soalan tentang platform.

**Kemas kini ciri:**

BinaApp boleh menambah, mengubah, atau mengeluarkan ciri dari semasa ke semasa. Ciri-ciri material baru atau pembuangan ciri akan dimaklumkan kepada anda mengikut seksyen 22 (Pindaan Terma).`,
    },

    {
      id: 'harta-intelek',
      title: '14. Hak Harta Intelek',
      content: `**14.1 Pemilikan Platform oleh BinaApp**

Semua hak harta intelek yang berkaitan dengan platform BinaApp, termasuk:

- **Kod sumber** (frontend, backend, infrastruktur);
- **Reka bentuk antara muka pengguna (UI/UX)**;
- **Tanda dagangan** "BinaApp" dan logo BinaApp;
- **Dokumentasi teknikal** dan bahan latihan;
- **Algoritma dan logik perniagaan**;
- **Pangkalan data template laman web** yang disediakan oleh BinaApp;

adalah milik eksklusif **Ezy Work Asia Solution** (operator BinaApp) atau diberi lesen kepada kami oleh pihak ketiga. Tiada hak diberikan kepada anda kecuali yang dinyatakan secara eksplisit dalam Terma ini.

Anda **tidak boleh**:
- Menyalin, mengubah, atau mengedarkan kod sumber atau bahan platform;
- Menggunakan tanda dagangan "BinaApp" tanpa kebenaran bertulis;
- Mendakwa hak pemilikan ke atas mana-mana komponen platform.

**14.2 Pemilikan Kandungan oleh Merchant**

Anda **mengekalkan pemilikan penuh** ke atas kandungan yang anda muat naik atau cipta menggunakan platform, termasuk:

- **Menu, harga, dan deskripsi produk** yang anda masukkan;
- **Logo perniagaan** yang anda muat naik;
- **Foto produk asal** yang anda muat naik;
- **Maklumat perniagaan** (nama, alamat, jam operasi, dll.);
- **Polisi merchant sendiri** (terma jual beli, polisi refund, dll.).

**Lesen yang anda berikan kepada BinaApp:**

Untuk membolehkan BinaApp menyediakan Perkhidmatan, anda memberikan kepada BinaApp **lesen royalti-percuma, di seluruh dunia, tidak eksklusif, dan boleh disublesenkan** untuk:

- Memaparkan kandungan anda pada laman web yang dijana;
- Memproses kandungan untuk fungsi platform (contohnya, penjanaan AI);
- Membuat sandaran dan replikasi untuk tujuan operasi.

Lesen ini tamat apabila anda menamatkan akaun, tertakluk kepada tempoh penyimpanan untuk sandaran (lihat Polisi Privasi seksyen 14).

**14.3 Kandungan yang Dijana oleh AI**

Untuk kandungan yang dijana melalui pipeline AI BinaApp (HTML laman web, imej menu, imej hero, teks balasan):

- **Pemilikan dipindahkan kepada merchant** — BinaApp **tidak menuntut hak cipta** ke atas output AI;
- Anda bebas untuk menggunakan, mengubah, atau menerbitkan kandungan AI yang dijana untuk perniagaan anda;
- **BinaApp memegang lesen latar belakang terhad, royalti-percuma** untuk memaparkan dan memproses kandungan AI tersebut sebagai sebahagian operasi platform.

**Pengecualian penting:**

- **BinaApp tidak menjamin** bahawa kandungan AI yang dijana adalah **bebas daripada pelanggaran hak cipta pihak ketiga**. Imej yang dijana oleh AI mungkin menyerupai karya berhak cipta sedia ada (lihat seksyen 11);
- **Anda bertanggungjawab** untuk pelanggaran hak cipta yang timbul daripada penggunaan kandungan AI yang dijana.

**14.4 Lesen Subdomain**

BinaApp memberikan kepada anda **lesen terhad, tidak eksklusif, dan boleh ditarik balik** untuk menggunakan subdomain \`[namaperniagaan].binaapp.my\` untuk mengehoskan laman web restoran anda.

**Syarat lesen subdomain:**

- Subdomain mesti **sah dari segi tatabahasa** dan tidak mengelirukan (contohnya, tidak menyerupai jenama lain);
- Subdomain mesti **berkaitan dengan perniagaan F&B anda yang sah**;
- Tidak boleh **mencatut tanda dagangan** atau identiti pihak ketiga (trademark squatting).

**Hak BinaApp untuk membatalkan subdomain:**

BinaApp berhak untuk **membatalkan subdomain tanpa notis terlebih dahulu** jika subdomain digunakan untuk:

- **Aktiviti haram atau menyalahi undang-undang Malaysia**;
- **Pelanggaran Terma ini** (contohnya, kandungan terlarang);
- **Pelanggaran hak pihak ketiga** (trademark, copyright);
- **Kandungan yang mengandungi ujaran kebencian, lucah, atau ganas**.

**Penamatan lesen:**

Lesen subdomain **terhenti secara automatik** apabila:

- Anda menamatkan akaun BinaApp;
- BinaApp menamatkan akaun anda kerana pelanggaran Terma;
- Subdomain dibatalkan untuk sebab yang dinyatakan di atas.

Selepas penamatan, BinaApp boleh **menarik balik dan menetapkan semula** subdomain tersebut untuk pengguna lain.`,
    },

    {
      id: 'ketersediaan-perkhidmatan',
      title: '15. Ketersediaan Perkhidmatan',
      content: `**Sasaran masa operasi (uptime):**

BinaApp menetapkan sasaran **99.9% ketersediaan perkhidmatan** untuk komponen utama platform (dashboard, sistem pesanan, laman web yang diterbitkan). Walau bagaimanapun, **kami tidak menjamin** uptime ini sebagai komitmen kontraktual yang boleh dikuatkuasakan.

**Penyelenggaraan berjadual:**

Dari semasa ke semasa, kami perlu menjalankan penyelenggaraan berjadual untuk mengemas kini perisian, meningkatkan keselamatan, atau memperbaiki prestasi. Untuk penyelenggaraan yang akan menyebabkan **gangguan perkhidmatan yang ketara**, kami akan:

- **Memberi notis sekurang-kurangnya 24 jam** terlebih dahulu melalui emel dan banner dashboard;
- **Menjadualkan penyelenggaraan pada waktu trafik rendah** apabila boleh (contohnya, pukul 2 pagi - 4 pagi waktu Malaysia);
- **Memaklumkan status pemulihan** apabila penyelenggaraan selesai.

**Penyelenggaraan kecemasan:**

Untuk **isu keselamatan kritikal atau gangguan tidak dijangka**, kami boleh menjalankan penyelenggaraan tanpa notis terlebih dahulu. Kami akan memaklumkan anda secepat mungkin selepas isu diselesaikan.

**Force majeure:**

BinaApp **tidak bertanggungjawab** untuk gangguan perkhidmatan yang disebabkan oleh peristiwa di luar kawalan kami, termasuk tetapi tidak terhad kepada:

- Bencana alam (gempa bumi, banjir, taufan);
- Tindakan kerajaan (sekatan, perintah, kawalan eksport);
- Gangguan infrastruktur **pembekal pihak ketiga** (Supabase, Render, Vercel, ToyyibPay, pembekal AI);
- Serangan siber besar-besaran (DDoS yang luar biasa, ransomware);
- Gangguan rangkaian utiliti (elektrik, internet ISP);
- Perang, rusuhan, atau gangguan awam.

**Tahap sokongan mengikut pelan:**

Respons untuk pertanyaan sokongan (waktu perniagaan Isnin-Jumaat, 9 pagi - 6 petang waktu Malaysia):

- **Pelan Free:** Sokongan komuniti sahaja (tiada SLA);
- **Pelan Starter:** Respons emel dalam **48-72 jam** waktu perniagaan;
- **Pelan Basic:** Respons emel dalam **24-48 jam** waktu perniagaan;
- **Pelan Pro:** Respons keutamaan dalam **12-24 jam** waktu perniagaan.

Untuk isu kritikal (perkhidmatan tidak berfungsi langsung, pelanggaran data), kami berusaha untuk respons secepat mungkin tanpa mengira tahap langganan.

**Kompensasi untuk gangguan:**

Kami **tidak menyediakan kompensasi atau pelanjutan langganan automatik** untuk gangguan perkhidmatan, kecuali:

- Gangguan **berlanjutan melebihi 24 jam** disebabkan oleh kesalahan teknikal kami;
- Permintaan kompensasi yang **diluluskan mengikut budi bicara kami**.

Untuk meminta kompensasi, hantarkan emel kepada **support.team@binaapp.my** dengan butiran gangguan.`,
    },

    {
      id: 'penamatan-akaun',
      title: '16. Penamatan Akaun',
      content: `**Penamatan oleh anda:**

Anda boleh menamatkan akaun BinaApp pada **bila-bila masa** dengan:

- Membatalkan langganan melalui tetapan dashboard (akaun diturunkan kepada Pelan Free pada akhir tempoh bil);
- Menghantar emel kepada **admin@binaapp.my** dengan subjek \`Account Termination Request\` untuk pemadaman penuh akaun.

**Kesan penamatan:**

- Akses kepada dashboard ditamatkan pada tarikh penamatan efektif;
- **Laman web yang diterbitkan** akan **dipadam** dari pengehosan BinaApp;
- **Data merchant** (akaun, menu, pesanan, dll.) **dipadam** mengikut polisi pengekalan (lihat **Polisi Privasi seksyen 14**), termasuk:
  - **30 hari** sandaran kecemasan untuk pemulihan;
  - **7 tahun** untuk rekod pesanan dan transaksi pembayaran (keperluan undang-undang perakaunan dan cukai);
  - Selepas tempoh sandaran/pengekalan, data dipadam secara kekal.

**Tiada refund:**

Penamatan akaun **tidak melayakkan anda untuk refund** untuk fi langganan yang telah dibayar untuk tempoh bil semasa. Sila lihat seksyen 5 untuk polisi refund.

**Penamatan oleh BinaApp:**

BinaApp boleh menamatkan akaun anda dengan atau tanpa notis dalam keadaan berikut:

- **Pelanggaran material Terma ini** atau Polisi Privasi (contohnya, aktiviti larangan dalam seksyen 6);
- **Kegagalan pembayaran berterusan** melebihi 30 hari (lihat seksyen 4.3);
- **Aktiviti yang menyalahi undang-undang Malaysia** atau yang menjejaskan keselamatan platform;
- **Pengabaian akaun** (tiada aktiviti log masuk selama 180 hari pada Pelan Free);
- **Perintah mahkamah** atau kewajipan undang-undang.

**Notis penamatan:**

- Untuk pelanggaran **tidak material**, kami akan memberi **amaran bertulis** dan **tempoh remedi 14 hari** sebelum penamatan;
- Untuk pelanggaran **material atau aktiviti menyalahi undang-undang**, kami boleh menamatkan **serta-merta tanpa notis**.

**Eksport data sebelum penamatan:**

Sebelum menamatkan akaun, anda mempunyai hak untuk **mengeksport data anda** dalam format yang berstruktur. Hubungi kami di **admin@binaapp.my** untuk meminta eksport data, mengikut hak mudah alih dalam Polisi Privasi seksyen 15.

**Survival klausa:**

Klausa-klausa berikut akan **terus berkuat kuasa** selepas penamatan akaun:

- Hak harta intelek (seksyen 14);
- Had liabiliti (seksyen 18);
- Indemniti (seksyen 19);
- Undang-undang dan pertikaian (seksyen 21);
- Kewajipan undang-undang pengekalan data (lihat Polisi Privasi seksyen 14).`,
    },

    {
      id: 'perkhidmatan-pihak-ketiga',
      title: '17. Perkhidmatan Pihak Ketiga',
      content: `BinaApp bergantung kepada beberapa pembekal pihak ketiga untuk menyediakan Perkhidmatan. Sila lihat jadual perkhidmatan pihak ketiga di bawah untuk butiran setiap pembekal dan pautan ke polisi privasi mereka.

**Hubungan kontraktual:**

- BinaApp mempunyai **perjanjian komersial** dengan setiap pembekal pihak ketiga di atas;
- Penggunaan Perkhidmatan oleh anda **bersetuju dengan pemindahan data** yang diperlukan kepada pembekal-pembekal ini, mengikut Polisi Privasi seksyen 6 dan 16.

**Liabiliti gangguan pihak ketiga:**

Jika gangguan perkhidmatan disebabkan oleh **kegagalan pembekal pihak ketiga**, BinaApp **tidak bertanggungjawab** untuk kerugian, tetapi kami akan:

- **Mencari penyelesaian alternatif** secepat mungkin;
- **Memaklumkan status** kepada pengguna melalui emel dan banner dashboard;
- **Berkomunikasi dengan pembekal** untuk mempercepat pemulihan.

**Hak untuk menukar pembekal:**

BinaApp berhak untuk **menukar atau menambah pembekal pihak ketiga** dari semasa ke semasa untuk meningkatkan kualiti perkhidmatan, kos, atau pematuhan privasi. Perubahan material pembekal akan dimaklumkan kepada anda mengikut seksyen 22 (Pindaan Terma) dan Polisi Privasi.

**Polisi privasi pembekal:**

Anda digalakkan untuk membaca polisi privasi setiap pembekal pihak ketiga untuk memahami amalan privasi mereka. BinaApp tidak mengawal polisi tersebut dan **tidak bertanggungjawab** untuk perubahan dalam amalan privasi pembekal.`,
      thirdPartyTable: [
        {
          service: 'ToyyibPay',
          region: 'Malaysia',
          purpose: 'Pemprosesan pembayaran langganan merchant',
          policyUrl: 'https://toyyibpay.com/privacy-policy',
        },
        {
          service: 'Supabase',
          region: 'Singapura / Asia Tenggara',
          purpose: 'Pangkalan data dan storan (pengekalan data utama)',
          policyUrl: 'https://supabase.com/privacy',
        },
        {
          service: 'Render',
          region: 'Singapura / Global',
          purpose: 'Pengehosan aplikasi backend',
          policyUrl: 'https://render.com/privacy',
        },
        {
          service: 'Vercel',
          region: 'Amerika Syarikat / Global',
          purpose: 'Pengehosan frontend dan rangkaian penghantaran kandungan (CDN)',
          policyUrl: 'https://vercel.com/legal/privacy-policy',
        },
        {
          service: 'Stability AI',
          region: 'Amerika Syarikat',
          purpose: 'Penjanaan imej AI (menu hero, imej item)',
          policyUrl: 'https://stability.ai/privacy-policy',
        },
        {
          service: 'DeepSeek',
          region: 'Republik Rakyat China',
          purpose: 'Penjanaan laman web AI, analisis aduan, balasan chat AI, BinaBot',
          policyUrl: 'https://www.deepseek.com/privacy',
        },
        {
          service: 'Qwen / Alibaba Cloud International',
          region: 'Singapura',
          purpose: 'Pengesahan foto penghantaran, penambahbaikan kandungan',
          policyUrl: 'https://www.alibabacloud.com/help/en/legal/privacy-policy',
        },
        {
          service: 'Anthropic Claude',
          region: 'Amerika Syarikat',
          purpose: 'Analisis emel sokongan (dengan sanitization)',
          policyUrl: 'https://www.anthropic.com/privacy',
        },
      ],
    },

    {
      id: 'had-liabiliti',
      title: '18. Had Liabiliti',
      content: `**(a) Had Maksimum Liabiliti (Liability Cap)**

Setakat yang dibenarkan oleh undang-undang Malaysia, **jumlah maksimum liabiliti BinaApp** kepada anda untuk semua tuntutan yang timbul daripada atau berkaitan dengan Terma ini atau Perkhidmatan, sama ada dalam kontrak, tort (termasuk kecuaian), pelanggaran kewajipan undang-undang, atau sebaliknya, hendaklah **dihadkan kepada yang lebih tinggi daripada:**

- **Jumlah fi langganan yang anda telah bayar kepada BinaApp dalam tempoh 12 bulan terkini** sebelum peristiwa yang menyebabkan tuntutan; atau
- **RM 100** (untuk pengguna Pelan Free atau pengguna yang belum membayar apa-apa fi).

**(b) Pengecualian Liabiliti**

Setakat yang dibenarkan oleh undang-undang, BinaApp **tidak bertanggungjawab** atas mana-mana kerugian atau ganti rugi berikut:

- **Kerugian tidak langsung (indirect damages)**;
- **Kerugian berbangkit (consequential damages)**;
- **Kerugian khas (special damages)**;
- **Kerugian punitif (punitive damages)** atau kerugian teladan;
- **Kerugian keuntungan (loss of profit)** sama ada langsung atau tidak langsung;
- **Kerugian pendapatan, perniagaan, atau peluang perniagaan**;
- **Kerugian data atau muhibah perniagaan**;
- **Kerugian akibat halusinasi atau kesilapan AI** yang tidak disemak oleh merchant;
- **Kerugian akibat keracunan makanan, penyakit berkaitan makanan**, atau apa-apa isu keselamatan makanan;
- **Kerugian akibat kemalangan penghantaran, kecederaan rider**, atau kerosakan harta benda semasa penghantaran;
- **Kerugian akibat kecuaian rider**, kecurian, atau tindakan tidak profesional rider;
- **Pertikaian customer-merchant** termasuk refund, pesanan salah, masa penghantaran;
- **Pertikaian pembayaran QR statik** atau apa-apa isu pembayaran customer-merchant;
- **Gangguan perkhidmatan pembekal pihak ketiga** (ToyyibPay, Vercel, Render, Supabase, pembekal AI);
- **Kelewatan atau kegagalan disebabkan force majeure** (lihat seksyen 15).

**(c) Pengecualian yang Tidak Boleh Dihadkan (Carve-Outs Undang-Undang Malaysia)**

Tiada satu pun dalam Terma ini akan mengecualikan atau menghadkan liabiliti BinaApp untuk:

- **Penipuan atau salah nyata penipuan** (fraud or fraudulent misrepresentation);
- **Kelakuan tidak senonoh yang disengajakan** (willful misconduct);
- **Kematian atau kecederaan peribadi** yang disebabkan oleh kecuaian BinaApp;
- **Mana-mana liabiliti yang tidak boleh dikecualikan atau dihadkan di bawah undang-undang Malaysia**.

**(d) Asas Pengecualian**

Anda mengakui bahawa:

- Fi langganan BinaApp ditetapkan **berdasarkan had liabiliti** yang dinyatakan dalam Terma ini;
- Jika BinaApp dikehendaki menanggung liabiliti yang lebih tinggi, fi langganan **akan menjadi jauh lebih tinggi** untuk meliputi kos risiko;
- Pengagihan risiko ini adalah **adil dan munasabah** dalam konteks SaaS B2B di Malaysia.

**(e) Tempoh Tuntutan**

Sebarang tuntutan terhadap BinaApp mestilah dikemukakan dalam **tempoh 1 tahun** dari tarikh peristiwa yang menyebabkan tuntutan. Tuntutan yang dikemukakan selepas tempoh ini akan dianggap **diketepikan** (waived).`,
    },

    {
      id: 'indemniti',
      title: '19. Indemniti',
      content: `**Indemniti oleh Merchant kepada BinaApp:**

Anda bersetuju untuk **menjamin (indemnify), mempertahankan (defend), dan melindungi (hold harmless)** BinaApp, syarikat induk dan subsidiarinya, pengarah, kakitangan, ejen, kontraktor, dan wakil ("**Pihak Diindemniti**") daripada dan terhadap **apa-apa dan semua tuntutan, kerosakan, kerugian, kos, perbelanjaan (termasuk fi guaman yang munasabah), penalti, denda, dan liabiliti** yang timbul daripada atau berkaitan dengan:

**(a) Operasi perniagaan merchant:**

- Operasi perniagaan F&B anda secara umum;
- Kualiti, keselamatan, atau keaslian makanan yang anda jual;
- Kelewatan, kegagalan penghantaran, atau pesanan salah;
- Aduan customer mengenai perkhidmatan anda.

**(b) Kandungan merchant:**

- Kandungan yang anda paparkan pada laman web atau dashboard, termasuk **kandungan AI yang dijana** tetapi anda menerbitkan;
- **Pelanggaran hak harta intelek pihak ketiga** akibat kandungan anda;
- **Maklumat palsu, mengelirukan, atau menipu** dalam kandungan anda;
- **Kandungan yang menyalahi undang-undang Malaysia** (lucah, ujaran kebencian, halal/haram).

**(c) Data pihak ketiga:**

- Pemuatnaikan data peribadi customer atau pihak ketiga **tanpa persetujuan yang sewajarnya** (lihat Polisi Privasi seksyen 18);
- **Pelanggaran PDPA 2010** atau undang-undang perlindungan data berkaitan;
- Permintaan akses, pembetulan, atau pemadaman daripada subjek data yang anda gagal kendalikan;
- **Denda atau hukuman** yang dikenakan oleh Jabatan PDP atau pihak berkuasa lain akibat tindakan anda sebagai pengawal data.

**(d) Pelanggaran Terma ini:**

- Mana-mana pelanggaran Terma ini oleh anda;
- Aktiviti larangan dalam seksyen 6;
- Penggunaan Perkhidmatan untuk tujuan yang tidak dibenarkan;
- Berkongsi kelayakan akaun secara tidak diizinkan.

**(e) Pelanggaran undang-undang:**

- **Pelanggaran undang-undang Malaysia** berkaitan operasi perniagaan F&B (Akta Makanan 1983, peraturan PBT, lesen perniagaan SSM, halal JAKIM);
- **Kelas tuntutan pekerja** daripada rider yang anda lantik (mendakwa BinaApp sebagai majikan padahal hubungan adalah merchant-rider);
- **Pelanggaran undang-undang cukai** (SST, cukai pendapatan);
- **Tuntutan harta intelek** daripada pihak ketiga akibat kandungan atau jenama anda.

**Proses indemniti:**

Jika BinaApp menerima tuntutan yang tertakluk kepada indemniti ini, kami akan:

- **Memaklumkan anda secara bertulis** secepat mungkin tentang tuntutan;
- Membenarkan anda **mengambil alih pertahanan** tuntutan tersebut, dengan peguam pilihan anda yang munasabah (BinaApp boleh terus terlibat sebagai pemerhati dengan kos sendiri);
- **Bekerjasama secara munasabah** dengan anda dalam pertahanan.

Anda **tidak boleh menyelesaikan tuntutan** yang melibatkan pengakuan tanggungjawab atau kewajipan kewangan BinaApp tanpa persetujuan bertulis kami terlebih dahulu.

**Survival:**

Kewajipan indemniti ini **terus berkuat kuasa** selepas penamatan akaun untuk tuntutan yang berkaitan dengan tempoh anda menggunakan Perkhidmatan.`,
    },

    {
      id: 'pemecahan',
      title: '20. Pemecahan / Severability',
      content: `Jika mana-mana **peruntukan, klausa, atau perkataan** dalam Terma ini didapati:

- **Tidak sah** (invalid);
- **Tidak boleh dikuatkuasakan** (unenforceable);
- **Menyalahi undang-undang** (illegal); atau
- **Bertentangan dengan dasar awam** (against public policy);

oleh mahkamah Malaysia yang berbidang kuasa atau pihak berkuasa kawal selia, maka:

- Peruntukan, klausa, atau perkataan tersebut **hendaklah dipisahkan** (severed) daripada Terma ini;
- **Baki Terma ini** hendaklah **kekal sah, berkuat kuasa, dan boleh dikuatkuasakan** sepenuhnya;
- Peruntukan yang dipisahkan hendaklah **digantikan, jika boleh, dengan peruntukan yang sah** yang mencerminkan niat asal pihak-pihak sehampir mungkin.

**Tafsiran berkadar:**

Jika sebahagian sahaja daripada peruntukan didapati tidak sah, hanya bahagian yang tidak sah hendaklah dipisahkan, dan bahagian yang sah hendaklah dikuatkuasakan.

**Tiada penepatan implisit:**

Kegagalan kami untuk menguatkuasakan mana-mana peruntukan Terma ini pada bila-bila masa **tidak membentuk penepatan (waiver)** hak kami untuk menguatkuasakan peruntukan tersebut pada masa hadapan.`,
    },

    {
      id: 'undang-undang',
      title: '21. Undang-Undang Yang Mentadbir & Pertikaian',
      content: `**Undang-undang yang mentadbir:**

Terma ini ditadbir oleh dan ditafsirkan mengikut **undang-undang Malaysia**, tanpa mengambil kira prinsip-prinsip percanggahan undang-undang (conflict of laws).

**Bidang kuasa eksklusif:**

Apa-apa pertikaian, perbalahan, atau tuntutan yang timbul daripada atau berkaitan dengan Terma ini, termasuk pertikaian tentang kewujudan, kesahihan, atau penamatannya, hendaklah tertakluk kepada **bidang kuasa eksklusif Mahkamah Malaysia di Kuala Lumpur**.

**Proses penyelesaian pertikaian — penyelesaian tidak formal terlebih dahulu:**

Sebelum memulakan prosiding undang-undang formal, kedua-dua pihak bersetuju untuk:

- **Menghubungi pihak satu lagi secara bertulis** (emel kepada admin@binaapp.my untuk BinaApp) dengan butiran pertikaian dan penyelesaian yang dicadangkan;
- **Berunding dengan niat baik (good faith)** untuk mencapai penyelesaian dalam tempoh **30 hari** dari notis bertulis;
- Jika tiada penyelesaian dicapai dalam tempoh 30 hari, mana-mana pihak boleh meneruskan tindakan undang-undang.

**Tribunal Tuntutan Pengguna Malaysia:**

Untuk **tuntutan pengguna kecil (di bawah RM 50,000)**, anda mungkin layak untuk mengemukakan tuntutan di **Tribunal Tuntutan Pengguna Malaysia (TTPM)** secara bebas. Maklumat lanjut di [www.kpdn.gov.my](https://www.kpdn.gov.my).

**Aduan PDPA:**

Untuk aduan berkaitan privasi atau perlindungan data, anda boleh memohon kepada **Jabatan Perlindungan Data Peribadi (JPDP) Malaysia**. Lihat **Polisi Privasi seksyen 22** dan seksyen Hubungi Kami (23) untuk butiran.

**Pengecualian timbang tara (arbitration):**

Terma ini **tidak menetapkan timbang tara** sebagai mekanisme penyelesaian pertikaian wajib. Anda berhak untuk mengemukakan tuntutan di mahkamah Malaysia yang berbidang kuasa.

**Kos undang-undang:**

Setiap pihak hendaklah menanggung **kos undang-undangnya sendiri**, kecuali jika diperintahkan oleh mahkamah atau dipersetujui secara bertulis.

**Tempoh tuntutan:**

Sila lihat seksyen 18(e) untuk tempoh tuntutan 1 tahun yang terpakai.`,
    },

    {
      id: 'pindaan-terma',
      title: '22. Pindaan Terma',
      content: `BinaApp berhak untuk **meminda Terma ini dari semasa ke semasa** untuk mencerminkan perubahan dalam:

- Perkhidmatan, ciri, atau pelan langganan;
- Pembekal pihak ketiga atau model perniagaan;
- Keperluan undang-undang dan kawal selia;
- Maklum balas pengguna dan amalan terbaik industri.

**Klasifikasi perubahan:**

**(a) Perubahan material:**

Perubahan **material** termasuk (tetapi tidak terhad kepada):

- **Perubahan harga langganan** atau pengenalan caj baru;
- **Pengurangan ciri** atau penamatan ciri yang ketara;
- **Perubahan pembekal pihak ketiga** yang menjejaskan privasi atau lokasi data;
- **Pengubahsuaian terma liabiliti, indemniti**, atau bidang kuasa;
- **Penambahan kewajipan pengguna** yang baru atau ketara.

Untuk perubahan material:

- Kami akan **memberi notis sekurang-kurangnya 30 hari** sebelum perubahan berkuat kuasa;
- Notis dihantar melalui **emel kepada alamat berdaftar akaun anda** dan **banner dashboard**;
- Anda akan diberi pilihan untuk **menerima Terma yang dipinda** atau **membatalkan langganan tanpa penalti** sebelum tarikh berkuat kuasa.

**(b) Perubahan kecil:**

Perubahan **kecil** termasuk:

- **Pembetulan tatabahasa, ejaan, atau penjelasan teks**;
- **Pengemaskinian rujukan silang** atau pautan URL;
- **Penjelasan terma sedia ada** tanpa mengubah maksud material;
- **Penambahan butiran kepada pendedahan sedia ada**.

Untuk perubahan kecil:

- Kami akan mengemas kini Terma **tanpa notis langsung** kepada anda;
- Perubahan akan **dicatatkan dalam seksyen Riwayat Perubahan** dengan butiran ringkas.

**Penggunaan berterusan = penerimaan:**

Penggunaan berterusan Perkhidmatan selepas Terma yang dipinda berkuat kuasa **membentuk penerimaan anda** kepada Terma baru. Jika anda tidak bersetuju dengan perubahan material, anda mesti:

- **Berhenti menggunakan Perkhidmatan** dengan serta-merta; dan
- **Membatalkan langganan** anda dalam tempoh 30 hari dari notis.

**Versi semasa:**

Versi terkini Terma akan **menyatakan tarikh berkuat kuasa** pada bahagian atas dokumen. Lihat seksyen Riwayat Perubahan untuk butiran perubahan antara versi.`,
    },

    {
      id: 'hubungi-kami',
      title: '23. Hubungi Kami',
      content: `**Untuk pertanyaan umum dan pertanyaan perniagaan:**

Emel: **info@binaapp.my**

**Untuk sokongan teknikal:**

Emel: **support.team@binaapp.my**

Tahap sokongan bergantung kepada pelan langganan anda (lihat seksyen 15).

**Untuk pertanyaan privasi dan permintaan PDPA:**

Emel: **admin@binaapp.my**

Sila lihat **Polisi Privasi seksyen 22** untuk butiran format permintaan PDPA.

**Untuk masalah pembayaran atau refund:**

Emel: **admin@binaapp.my** dengan subjek \`Billing Inquiry - [Butiran]\`.

**Maklumat syarikat:**

**Ezy Work Asia Solution**
No. Pendaftaran SSM: **002944700-D**

(Alamat surat-menyurat akan disediakan dalam kemas kini akan datang.)

**Untuk membuat aduan kepada pihak berkuasa:**

Jika anda tidak berpuas hati dengan respons kami atau jika anda percaya kami telah melanggar undang-undang Malaysia:

**(a) Aduan perlindungan data peribadi:**

**Jabatan Perlindungan Data Peribadi (JPDP) Malaysia**
- Talian: **1-300-88-2400**
- Laman web: **www.pdp.gov.my**

**(b) Aduan pengguna umum:**

**Kementerian Perdagangan Dalam Negeri dan Kos Sara Hidup (KPDN)**
- Laman web: **www.kpdn.gov.my**
- Tribunal Tuntutan Pengguna Malaysia (untuk tuntutan < RM 50,000)

**Tempoh respons sokongan:**

- **Pertanyaan privasi/PDPA:** 21 hari (mengikut Polisi Privasi seksyen 22);
- **Pertanyaan sokongan teknikal:** Mengikut pelan langganan anda (lihat seksyen 15).`,
    },

    {
      id: 'bahasa-muktamad',
      title: '24. Bahasa Muktamad',
      content: `Terma ini disediakan dalam dua bahasa: **Bahasa Malaysia (BM)** dan **Bahasa Inggeris (EN)**.

**Versi Bahasa Malaysia Terma ini adalah versi muktamad dan berkuat kuasa.**

Sekiranya terdapat sebarang **percanggahan, perbezaan tafsiran, atau ketidakselarasan** antara versi Bahasa Malaysia dan terjemahan Bahasa Inggeris, **versi Bahasa Malaysia akan diguna pakai dan mengatasi versi Bahasa Inggeris**.

Versi Bahasa Inggeris disediakan sebagai **kemudahan terjemahan sahaja**, untuk membantu pengguna yang lebih selesa dengan Bahasa Inggeris memahami terma-terma. Ia **tidak membentuk dokumen undang-undang berasingan**.

Sebarang versi terjemahan lain (jika dilancarkan pada masa hadapan, contohnya Bahasa Cina atau Tamil) juga adalah **untuk kemudahan sahaja**, dan versi Bahasa Malaysia tetap mengatasi.

**Konsistensi dengan Polisi Privasi:**

Klausa ini selaras dengan **Polisi Privasi seksyen 23** yang juga menetapkan BM sebagai versi muktamad.`,
    },

    {
      id: 'pengakuan',
      title: '25. Pengakuan & Penerimaan',
      content: `Dengan:

- **Mengklik butang "Saya bersetuju"** semasa pendaftaran;
- **Membuat pembayaran langganan** untuk Pelan Starter, Basic, atau Pro;
- **Log masuk dan menggunakan** dashboard BinaApp;
- **Menerbitkan laman web** menggunakan platform; atau
- **Berinteraksi dengan Perkhidmatan** dalam apa jua cara,

**anda mengakui bahawa:**

1. Anda telah **membaca dan memahami** Terma Perkhidmatan ini dalam keseluruhannya, termasuk seksyen-seksyen disclaimer (8, 9, 10, 11) dan had liabiliti (18) dan indemniti (19);

2. Anda telah **membaca dan menerima Polisi Privasi BinaApp** (\`/polisi-privasi\`);

3. Anda **berumur sekurang-kurangnya 18 tahun** dan mempunyai **kapasiti undang-undang penuh** untuk membentuk kontrak yang sah di sisi undang-undang Malaysia;

4. Anda **berkuasa untuk membentuk kontrak ini** bagi pihak perniagaan F&B anda (jika anda mewakili perniagaan);

5. Anda **bersetuju untuk terikat** dengan Terma ini dan apa-apa pindaan kemudian, mengikut seksyen 22;

6. Anda **memahami model perniagaan BinaApp** (lihat callout "Memahami Model Perniagaan BinaApp" di atas) — terutamanya bahawa BinaApp bukan platform penghantaran makanan, bukan rangkaian restoran, bukan pemproses pembayaran customer, dan bukan majikan rider;

7. Anda **bersetuju dengan pemindahan data merentas sempadan** kepada pembekal AI di Singapura, Amerika Syarikat, dan Republik Rakyat China, sebagaimana diterangkan dalam Polisi Privasi;

8. Anda **mengakui tanggungjawab anda sebagai pengawal data** untuk data customer dan data pihak ketiga lain yang anda muat naik (lihat Polisi Privasi seksyen 18);

9. Anda **bersetuju dengan klausa indemniti** dalam seksyen 19, termasuk kewajipan anda untuk melindungi BinaApp daripada tuntutan pihak ketiga yang timbul daripada operasi perniagaan anda atau data yang anda muat naik;

10. Anda **memahami had liabiliti** dalam seksyen 18 dan bersetuju dengan pengagihan risiko tersebut sebagai adil dan munasabah dalam konteks SaaS B2B di Malaysia.

**Jika anda TIDAK bersetuju dengan mana-mana terma:**

- **Berhenti menggunakan Perkhidmatan** dengan serta-merta;
- **Jangan mendaftar akaun** baru;
- **Batalkan langganan sedia ada** anda;
- Hubungi **admin@binaapp.my** untuk memulakan proses pemadaman akaun anda dan data berkaitan.

**Penerimaan kekal:**

Penerimaan ini kekal berkuat kuasa sehingga akaun anda ditamatkan atau Terma dipinda (mengikut seksyen 22).`,
    },

    {
      id: 'riwayat-perubahan',
      title: '26. Riwayat Perubahan / Version History',
      content: `Berikut adalah sejarah versi Terma Perkhidmatan BinaApp. Sila lihat senarai changelog di bawah untuk butiran perubahan antara versi.

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
        'Penambahan callout "Memahami Model Perniagaan BinaApp" di permulaan dokumen sebagai asas pemahaman;',
        'Pembetulan Seksyen 1 — BinaApp dijelaskan sebagai platform SaaS, BUKAN food delivery platform (per audit Conflict #4);',
        'Penambahan definisi baru dalam Seksyen 2: Addon, Kuota, Penyedia AI, QR Statik, dan klarifikasi status Rider sebagai kontraktor bebas merchant;',
        'Restrukturisasi Seksyen 4 (Langganan & Pengebilan) dengan 5 sub-seksyen: pelan tersedia (termasuk Free), pembaharuan auto, kegagalan pembayaran, addon, dan kuota;',
        'Pelan Free RM 0 dimasukkan secara formal dengan butiran ciri dan had kuota (per audit Finding 1);',
        'Penambahan jadual addon (5 jenis: ai_image, ai_hero, website, rider, zone) dengan harga, sahlaku 365 hari, dan polisi refund 7-hari;',
        'Penambahan jadual kuota terperinci untuk semua 4 tier (Free, Starter, Basic, Pro);',
        'Penambahan klarifikasi semantik addon rider — additive di atas had pelan asas (per audit Task 5b verdict);',
        'Penggantian Seksyen 5 (Refund) untuk mengeluarkan ambiguiti dan menambah polisi refund addon;',
        'Pengembangan Seksyen 6 (Aktiviti Larangan) mengikut model foodpanda s3.1 — 5 kategori larangan (teknikal, komersial, kandungan, data, kewangan);',
        'Penambahan Seksyen 7 (Tanggungjawab Khusus Merchant) — ketepatan menu, keselamatan makanan, lesen (SSM/halal/PBT), integriti data customer, kewajipan kepada rider;',
        'Penggantian "Tanggungjawab Pelanggan" lama dengan "Notis kepada Pengguna Akhir" (Seksyen 8) — informational, bukan binding obligations (per audit Conflict #6);',
        'Pengukuhan Seksyen 9 (Disclaimer Penghantaran) — rider sebagai kontraktor bebas merchant, BinaApp tidak menyediakan insurans/EPF/SOCSO (per audit T12);',
        'Penambahan Seksyen 10 (Disclaimer QR Statik) — BinaApp hanya memaparkan imej, tidak memproses pembayaran (per audit T13);',
        'Penambahan Seksyen 11 (Disclaimer Kandungan AI) — kandungan AI as-is, halusinasi mungkin berlaku, merchant bertanggungjawab menyemak (model foodpanda s6.11);',
        'Penggantian Seksyen 12 (PDPA) dengan single paragraph + link-out ke Polisi Privasi (per audit Conflict #2);',
        'Pengemaskinian Seksyen 13 (Alat Perisian & Ciri) untuk mencerminkan platform semasa (/delivery, /rider, /menu-designer, addon system, GPS, chat, AI dispute);',
        'Restrukturisasi Seksyen 14 (Harta Intelek) dengan 4 sub-seksyen termasuk pemilikan kandungan AI (14.3) dan revocation subdomain (14.4);',
        'Penambahan Seksyen 15 dengan tahap sokongan eksplisit per pelan (Starter 48-72h, Basic 24-48h, Pro 12-24h);',
        'Pengembangan Seksyen 17 (Perkhidmatan Pihak Ketiga) dengan jadual 8 pembekal: ToyyibPay, Supabase, Render, Vercel, Stability, DeepSeek, Qwen/Alibaba Cloud, Anthropic;',
        'Restrukturisasi Seksyen 18 (Had Liabiliti) mengikut model foodpanda — (a) cap, (b) pengecualian eksplisit, (c) carve-outs undang-undang Malaysia;',
        'Penambahan Seksyen 19 (Indemniti) — kewajipan merchant melindungi BinaApp dari tuntutan pihak ketiga (model foodpanda s13);',
        'Penambahan Seksyen 20 (Pemecahan / Severability) — model foodpanda s17;',
        'Pengukuhan Seksyen 21 (Undang-Undang) — bidang kuasa Mahkamah KL, 30-day informal resolution, rujukan TTPM dan KPDN;',
        'Konsolidasi Seksyen 22 (Pindaan Terma) — perbezaan material vs minor change, 30-day notice untuk material;',
        'Pengemaskinian Seksyen 23 (Hubungi Kami) dengan 3 emel rasmi: info@, support.team@, admin@;',
        'Penambahan Seksyen 24 (Bahasa Muktamad) — selaras dengan Polisi Privasi s23;',
        'Penambahan Seksyen 25 (Pengakuan & Penerimaan) — 10-point acknowledgment;',
        'Pembuangan rujukan kepada pembekal AI lapuk (GLM dialih keluar) dan pemproses pembayaran lapuk (FPX placeholder dialih keluar).',
      ],
    },
    {
      version: '2.0',
      date: '31 Januari 2025',
      changes: [
        'Penambahan klausa berkaitan ciri AI generatif;',
        'Pengemaskinian senarai pelan langganan dan harga;',
        'Penambahan butiran sistem penghantaran asas;',
        'Pengemaskinian klausa harta intelek.',
      ],
    },
    {
      version: '1.0',
      date: 'Awal 2024',
      changes: ['Versi awal Terma Perkhidmatan pada pelancaran BinaApp.'],
    },
  ],

  contact: {
    company: 'Ezy Work Asia Solution',
    ssm: '002944700-D',
    dpoEmail: 'admin@binaapp.my',
    supportEmail: 'support.team@binaapp.my',
    generalEmail: 'info@binaapp.my',
    pdpDeptPhone: '1-300-88-2400',
    pdpDeptWebsite: 'www.pdp.gov.my',
  },

  prevailingLanguage: {
    title: 'Bahasa Muktamad',
    content: `Versi Bahasa Malaysia Terma ini adalah versi muktamad. Sekiranya terdapat percanggahan antara versi Bahasa Malaysia dan terjemahan Bahasa Inggeris, versi Bahasa Malaysia akan diguna pakai.`,
  },
};
