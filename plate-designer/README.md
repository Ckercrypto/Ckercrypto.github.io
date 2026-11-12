# Trans Plate Designer · طراح پلاک ترانس

Design and print exact-size **nameplates for transformers and voltage stabilizers**
on Android and Windows. Made for Trans Reza (ترانس رضا), Mashhad.

## English

### What it does
- Plate of any size in mm, graph-paper grid (1 mm, 5 mm, heavier 1 cm lines), mm rulers, pinch / mouse-wheel zoom and pan.
- Tools: text (FA + EN, size in mm, bold, alignment), line, rectangle, rounded rectangle, circle/ellipse,
  mounting holes (diameter in mm, one-tap "4 corner holes"), table of fields, border frame, image/logo import,
  49 industrial electrical symbols, line/fill colours, line width in mm, layers (front/back), duplicate, delete,
  align (left/centre/right/top/middle/bottom, centre on plate), snap to grid (off / 0.5 / 1 / 5 mm),
  exact X / Y / W / H / rotation in mm, undo/redo.
- Templates with a simple form: transformer / stabilizer nameplate, high-voltage warning label,
  terminal strip (L1 L2 L3 N PE), simple stabilizer label. Everything stays editable.
- `{serial}` and `{date}` can be used inside any text. "Serial +1" increments the serial; the A4 sheet export can
  give every copy the next serial number.
- Export: **PDF at exact 1:1 size**, **A4 sheet with many copies and cut marks**, **PNG** at 300 / 600 / 1200 dpi,
  **SVG in millimetres** for laser / CNC, and a **printer calibration page**.
- Printer correction (X % and Y %) for printers that scale; the app computes it from what you measure.
- Autosave, project files (`.tplate`, JSON), recent files, Persian / English interface, quick tour.

### Install on Android
1. Download `TransPlateDesigner-android.apk` from the release **plate-designer-latest**.
2. Open it. If Android asks, allow **"Install unknown apps"** for your browser or file manager
   (Settings > Apps > [browser] > Install unknown apps), then tap **Install**.
3. Exports are saved in **Documents** (PDF / SVG) or **Pictures** (PNG); use **Share / Print** to send them to a print app.

### Install on Windows
1. Download `TransPlateDesigner-windows.zip` from the same release.
2. Unzip it anywhere (for example `C:\TransPlate`) and run `TransPlateDesigner.exe`.
   If SmartScreen warns about an unknown app, choose *More info > Run anyway*.
3. Projects and exports are saved in `Documents\TransPlate`.

### Printing at the exact size
Print with **100 % / Actual size** (turn off *Fit to page*). Print the calibration page once
(Settings > Printer calibration), measure the 100 mm rulers, type the measured values and the
app corrects every later export.

### Developers
- `python main.py` runs the desktop app (Python 3.10+, `pip install -r requirements.txt`).
- `python tests/test_core.py` - core tests (no Kivy needed).
- `python tests/ui_smoke.py OUTDIR [desktop|phone]` - end-to-end UI test with screenshots (needs a display / Xvfb).
- `python tools/make_icons.py` regenerates icons, app icon and presplash.
- Android: `buildozer android debug`. Windows: `pyinstaller TransPlateDesigner.spec --noconfirm`.
- Font: Vazirmatn (SIL Open Font License, `assets/fonts/OFL.txt`).

## فارسی

### این برنامه چه می‌کند؟
- طراحی پلاک مشخصات ترانسفورماتور و استابلایزر با **اندازهٔ دقیق میلی‌متری**؛ شبکهٔ میلی‌متری مثل کاغذ شطرنجی، خط‌کش، بزرگنمایی با دو انگشت یا چرخ ماوس.
- ابزارها: متن فارسی و انگلیسی، خط، مستطیل، گوشه‌گرد، دایره، سوراخ نصب (با دکمهٔ «۴ سوراخ»)، جدول مشخصات، قاب، تصویر/لوگو، ۴۹ نماد صنعتی برق، رنگ و ضخامت خط، جلو/عقب، کپی، حذف، ترازبندی، چسبیدن به شبکه، ورود عددی X/Y/عرض/ارتفاع، واگرد و ازنو.
- قالب آماده: پلاک ترانس/استابلایزر با فرم ساده (نام تجاری پیش‌فرض «ترانس رضا»)، برچسب هشدار فشار قوی، نوار ترمینال، برچسب ساده استابلایزر.
- شماره سریال خودکار (`{serial}`) و خروجی چند نسخه روی برگه A4 با علامت برش.
- خروجی PDF با اندازهٔ ۱:۱، PNG با کیفیت ۳۰۰/۶۰۰/۱۲۰۰ dpi، SVG میلی‌متری برای لیزر و CNC، و صفحهٔ کالیبراسیون چاپگر.

### نصب روی اندروید
1. فایل `TransPlateDesigner-android.apk` را از بخش Release با نام **plate-designer-latest** دانلود کنید.
2. فایل را باز کنید. اگر اندروید اجازه نداد، در تنظیمات گزینهٔ **«نصب برنامه‌های ناشناس» (Install unknown apps)** را برای مرورگر یا مدیر فایل روشن کنید و سپس **نصب** را بزنید.
3. خروجی‌ها در پوشهٔ **Documents** (PDF و SVG) یا **Pictures** (PNG) ذخیره می‌شوند و با دکمهٔ **اشتراک / چاپ** می‌توانید آن‌ها را به برنامهٔ چاپ بفرستید.

### نصب روی ویندوز
1. فایل `TransPlateDesigner-windows.zip` را دانلود و از حالت فشرده خارج کنید.
2. فایل `TransPlateDesigner.exe` را اجرا کنید (اگر SmartScreen هشدار داد: More info ← Run anyway).
3. پروژه‌ها و خروجی‌ها در پوشهٔ `Documents\TransPlate` ذخیره می‌شوند.

### چاپ با اندازهٔ دقیق
هنگام چاپ مقیاس را **۱۰۰٪ (Actual size)** بگذارید و «Fit to page» را خاموش کنید. یک بار صفحهٔ کالیبراسیون را چاپ کنید، خط‌کش ۱۰۰ میلی‌متری را اندازه بگیرید و عدد را در «تنظیمات ← کالیبراسیون چاپگر» وارد کنید.
