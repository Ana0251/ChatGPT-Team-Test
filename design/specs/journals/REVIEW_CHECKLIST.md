# H-19 — چک‌لیست تحویل و کنترل کیفیت مستقل

**Owner:** UI/UX؛ **Decision:** `APP-HESABYAR-W2-PHASE1-ENTRY-20261116-001`؛ **Manager handoff:** PR #70 comment `6910825905`.  
**Contract:** rc.4 `f57de031224e21f09253642c210a778a60683711`. **Stage:** document completeness `SPECIFIED`؛ اجرای مرورگر و تست accessibility/security/accounting = `RUNTIME_NOT_TESTED`.

## ماتریس پوشش صفحات و پذیرش
| ID | بازبینی قابل تکرار | وضعیت مستند | مرورگر/QA runtime |
|---|---|---|---|
| AC-01 | ۴ سطح group→general→subsidiary→detail، والد هم‌شرکتی و codes string | SPECIFIED | NOT_TESTED |
| AC-02 | کد پیشرو 000001 بدون تغییر؛ full_code readonly؛ postable computed | SPECIFIED | NOT_TESTED |
| AC-03 | GET account list/parent pagination + Create/GET/PATCH/DELETE دقیق schema | SPECIFIED | NOT_TESTED |
| AC-04 | ساخت/ویرایش/حذف با role، خطاهای 401/403/404/409/422، عدم IDOR | SPECIFIED | NOT_TESTED |
| AC-05 | حالات Empty/Loading/Success/Disabled/Network/Permission/Read-only | SPECIFIED | NOT_TESTED |
| AC-06 | حذف حساب دارای فرزند یا مصرف‌شده مسدود بر اساس پاسخ سرور | SPECIFIED | NOT_TESTED |
| JR-01 | فهرست با status/fiscal_year_id، صفحه‌بندی و context درست | SPECIFIED | NOT_TESTED |
| JR-02 | DraftLine ناقص و نامتوازن با هشدار ساخت‌یافته **قابل ذخیره** | SPECIFIED | NOT_TESTED |
| JR-03 | مقدار خالی draft با `"0"` اشتباه نشود؛ مبلغ و تاریخ canonical | SPECIFIED | NOT_TESTED |
| JR-04 | totals و warnings پاسخ سرور + خطای field/line_index | SPECIFIED | NOT_TESTED |
| JR-05 | حداقل دو سطر معتبر و balanced positive فقط گیت POST سرور | SPECIFIED | NOT_TESTED |
| JR-06 | POST فقط idempotent با Key، بدون blind replay در network/CSRF | SPECIFIED | NOT_TESTED |
| JR-07 | status=posted ⇒ فرم immutable؛ حذف/ویرایش ناممکن | SPECIFIED | NOT_TESTED |
| JR-08 | reverse مستقل با reason/date و ارتباط به سند اصلی | SPECIFIED | NOT_TESTED |
| JR-09 | 401/403/404/409/422 و warnings با متن امن فارسی | SPECIFIED | NOT_TESTED |
| UX-01 | H-17 light/dark palette، Vazirmatn/fallback، logical RTL+bdi LTR | SPECIFIED | NOT_TESTED |
| UX-02 | عرض‌های 360/390/600/1024/1280، 200% zoom، بدون clip مقدار | SPECIFIED | NOT_TESTED |
| UX-03 | Tab/Enter/Space/Escape، focus return، اعلان خطا و totals | SPECIFIED | NOT_TESTED |
| UX-04 | text 4.5:1، nontext 3:1، touch >=44px، reduced-motion | SPECIFIED | NOT_TESTED |
| GOV-01 | تغییر فقط در paths H-19، OpenAPI و frontend/backend/ledger ثابت | PENDING_DIFF | NOT_APPLICABLE |

## تمرین‌های داده مصنوعی برای review بعدی (نه تست انجام‌شده)
1. دو ردیف: بدهکار `"1200000"` و بستانکار `"1200000"` → قبل از POST «متوازن از نظر UI»؛ تنها پاسخ سرور `posted` موفقیت قطعی را ثابت می‌کند.
2. سطر اول فاقد حساب و مبلغ، سطر دوم `"100"` بدهکار و بدون بستانکار → ذخیره Draft با warnings `LINE_MISSING_ACCOUNT / DRAFT_UNBALANCED` در صورت پذیرش سرور؛ Posting رد شود.
3. ردیف account code `000001` به صورت رشته و full_code نمایش داده شود؛ هیچ تبدیل عددی انجام نشود.
4. مبلغ `"99999999999999999999"` با رقم بیستم: نمایش کامل و محاسبات دقیق، نه JS Number؛ رقم بیست‌ویکم با خطای ورودی.
5. `posted` و سپس تلاش `PUT /journals/{id}` → 409 `JOURNAL_IMMUTABLE` در آزمون آینده؛ UI همیشه read-only بماند.
6. برگشت با `reason` خالی → خطای ورودی؛ صحیح: POST /reverse با تاریخ و دلیل و کلید idempotency، بدون تغییر سند قبلی.
7. 403 CSRF_INVALID و timeout پس از POST → بدون ارسال دوباره خودکار؛ بازیابی از GET و تأیید انسانی.
8. جابه‌جایی شرکت هنگام Draft و نقش viewer → هشدار داده ذخیره‌نشده، context ایزوله، عدم ثبت و تغییر فقط در مجوز واقعی.

## شواهد موردنیاز برای مرور واقعی آینده
نسخه مرورگر/OS و ابزار بررسی، commit دقیق UI اجراشده، تصاویر redacted دو تم در 360/390/600/1024/1280، تست 200% zoom و keyboard-only + screen-reader واقعی، نمونه خطاهای server با شناسه امن، آزمون 20-digit + leading zero، idempotency و وضعیت period/tenant در API، اجراکننده/فرمان/log/exit code و جداسازی owner از QA. هیچ‌یک در H-19 اجرا یا ادعا نشده است.

## قبل از PR: نقد داخلی طراحی (read-only reasoning)
- **ریسک ۱:** ذخیره draft نباید با اجباری‌کردن همه سطرها بسته شود؛ در مشخصات `DraftLine` optional را از Posting جدا کردیم.
- **ریسک ۲:** اعداد طولانی و کدهای دارای صفر در RTL بی‌ثبات می‌شوند؛ نمایش ایزوله، رشته canonical و نمای mobile stacked تعریف شد.
- **ریسک ۳:** تغییر role/tenant و شبکه ممکن است موفقیت جعلی بسازد؛ تنها پاسخ معتبر سرور و بازسنجی قبل از mutation معیار است.
- **ریسک ۴:** پرش فوکوس بعد از افزودن/حذف سطر و هشدارهای index-based؛ فوکوس مشخص و invalidate کردن هشدار قدیمی مستند شد.
- **ریسک ۵:** جست‌وجوی سراسری/ثبت شماره سند توسط کلاینت در API وجود ندارد؛ ویژگی جدید بدون مصوبه وارد طرح نشد.
- **ریسک باز:** هیچ UI اجراشده/موتور Posting/QA runtime قابل بررسی نیست. بازبینی‌های قرارداد و امکان‌پذیری با Coordinator و سپس QA باید انجام شود.

## گیت review Policy
1. **Coordinator (coordinator_required):** تطبیق کامل API، سطح دسترسی، Draft/Post/reverse، وجود feature بدون endpoint و همپوشانی مسیرها. نتیجه مستقل در PR گزارش شود.
2. **QA:** فقط بعد از Coordinator، بررسی مستقل سند/ماتریس و قابلیت آزمون؛ از مستندات نتیجه PASS runtime نگیرد.
3. **Manager:** تصمیم تأیید و Merge؛ هیچ ادغام یا تکمیل task توسط UI/UX انجام نشود. H-20 و سایر وظایف خارج از scope باقی بمانند.
