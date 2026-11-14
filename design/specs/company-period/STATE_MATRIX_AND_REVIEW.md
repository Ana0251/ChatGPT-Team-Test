# H-18 — ماتریس حالت‌ها، چک‌لیست و شواهد بازبینی

**Framework:** 1.3.0 / legacy review: **Coordinator → QA**.  
**Manager authorization:** `APP-HESABYAR-W1-H04-H18-ENTRY-20261114-001`; `H-18.start_authorized=true`, `W1.entry_authorized=true`, H-02/H-17 = COMPLETED.  
**Contract:** `1.0.0-rc.3` SHA `98d34e7bd7b4551c0f429ea5e388781060ceaf63`.  
**Status meaning:** `SPECIFIED` = سند طراحی پوشش می‌دهد؛ `NOT_TESTED` = آزمون واقعی وجود ندارد؛ `FAIL` = نقص مشاهده‌شده در اجرای واقعی. **SPECIFIED ≠ QA PASS**.

## ۱. ماتریس حالت‌های بین‌صفحه‌ای

| مرحله | Loading | Empty | Error | Permission denied | Success |
|---|---|---|---|---|---|
| ورود | دریافت CSRF / ارسال فرم | فرم بدون داده، راهنمای فیلد | AUTH_INVALID، VALIDATION_ERROR، خطای ارتباط | ACCESS_DENIED / CSRF_INVALID با بازیابی جدا | login + CSRF تازه + me |
| نشست | GET me | نشست/هویت موجود نیست | SESSION_EXPIRED / شبکه | نقش مجاز نیست | principal معتبر |
| دعوت عضو | POST invitation | هنوز دعوتی ایجاد نشده | INVITE_EXPIRED/INVALID/USED، DUPLICATE | INVITE_ROLE_FORBIDDEN | 202 دعوت **در انتظار پذیرش** |
| فعال‌سازی | CSRF / POST activate | توکن یا گذرواژه خالی | توکن مصرف‌شده/نامعتبر | خطای CSRF | 204 نیازمند login |
| شرکت | GET companies | [] بدون عضویت | 404/شبکه | 403 بدون افشای شرکت | شرکت و نقش معتبر |
| سال مالی | GET fiscal-years | [] بدون سال | شبکه / داده قدیمی | 403/404 | سال انتخابی |
| دوره مالی | GET periods | [] بدون دوره | شبکه / بازه نامعتبر | 403/404 | دوره با برچسب باز/بسته |

## ۲. سناریوهای بازبینی
| ID | انتظار قابل بررسی | سند مرجع | وضعیت سند | آزمون واقعی |
|---|---|---|---|---|
| ID-01 | Login داخلی email/password، بدون signup عمومی | identity/AUTH_AND_INVITATIONS.md | SPECIFIED | NOT_TESTED |
| ID-02 | bootstrap CSRF، چرخش نشست، token فقط حافظه | identity/AUTH_AND_INVITATIONS.md | SPECIFIED | NOT_TESTED |
| ID-03 | 401/403/422 به پیام فارسی پایدار و فوکوس | identity/SESSION_STATES.md | SPECIFIED | NOT_TESTED |
| ID-04 | CSRF یک بار refresh، mutation بدون replay خودکار | identity/SESSION_STATES.md | SPECIFIED | NOT_TESTED |
| ID-05 | logout و SESSION_EXPIRED بدون ادعای موفقیت کاذب | identity/AUTH_AND_INVITATIONS.md | SPECIFIED | NOT_TESTED |
| ID-06 | فعال‌سازی مالک اولیه با توکن و login بعدی | identity/AUTH_AND_INVITATIONS.md | SPECIFIED | NOT_TESTED |
| ID-07 | دعوت user جدید/موجود، token یکبارمصرف، وضعیت pending | identity/AUTH_AND_INVITATIONS.md | SPECIFIED | NOT_TESTED |
| ID-08 | admin حق دعوت owner ندارد؛ owner فقط company-scoped | identity/AUTH_AND_INVITATIONS.md | SPECIFIED | NOT_TESTED |
| CP-01 | شرکت‌ها فقط از memberships / companies؛ بدون نشت داده | company-period/COMPANY_FISCAL_SELECTION.md | SPECIFIED | NOT_TESTED |
| CP-02 | تعویض شرکت context/cache/عملیات قبلی را جدا کند | company-period/COMPANY_FISCAL_SELECTION.md | SPECIFIED | NOT_TESTED |
| CP-03 | نقش نمایش‌داده‌شده مختص شرکت انتخابی است | company-period/COMPANY_FISCAL_SELECTION.md | SPECIFIED | NOT_TESTED |
| CP-04 | صفر شرکت/سال/دوره و CTA مبتنی بر نقش | company-period/COMPANY_FISCAL_SELECTION.md | SPECIFIED | NOT_TESTED |
| CP-05 | دوره open/closed با متن، کنترل سروری بسته‌شدن | company-period/COMPANY_FISCAL_SELECTION.md | SPECIFIED | NOT_TESTED |
| CP-06 | پایان دوره inclusive Jalali = API exclusive end - 1 day | company-period/COMPANY_FISCAL_SELECTION.md | SPECIFIED | NOT_TESTED |
| UI-01 | RTL و LTR-isolated email/UUID، Tab منطقی | استاندارد H-17 | SPECIFIED | NOT_TESTED |
| UI-02 | دو تم، متن/کنتراست و حالت focus/hover/disabled | H-17 foundations tokens | SPECIFIED | NOT_TESTED |
| UI-03 | ۳۶۰px یک ستون، padding ۱۶px، target >=۴۴px | هر دو حوزه | SPECIFIED | NOT_TESTED |
| UI-04 | screen reader، keyboard-only، 200% zoom و reduced motion | H-17 و هر دو حوزه | SPECIFIED | NOT_TESTED |
| GOV-01 | فایل‌ها فقط در دو مسیر H-18؛ OpenAPI/کد/ledger ثابت | PR diff | SPECIFIED | NOT_TESTED |

## ۳. روش جمع‌آوری شواهد در آینده
برای QA یا اجرای واقعی، SHA دقیق PR، مرورگر و نسخه، DPI، عرض‌های ۳۶۰/۳۹۰/۶۰۰/۱۰۲۴، دو تم، ۲۰۰٪ zoom، صفحه‌خوان، توالی Tab، پاسخ mock/HTTP واقعی 200/201/202/204/401/403/404/409/422، و تصویری بدون داده حساس ثبت شود. اعتبار امنیت نشست/دعوت فقط با تست سروری مستقل قابل اثبات است؛ طراحی یا mock تست امنیتی PASS نیست.

## ۴. گیت بازبینی legacy v1.3.0
1. **UI/UX owner:** مشخصات، ماتریس و PR را تحویل دهد و شواهد/محدودیت را در PR ثبت کند؛ وضعیت `READY_FOR_REVIEW` فقط در مسیر مصوب توسط PM Assistant/مسئول رسمی به‌روزرسانی می‌شود، نه با ویرایش شخصی `TASKS.json`.
2. **Coordinator review:** کنترل همخوانی طراحی با H-02 API، مرزبندی مالکیت، خطر تداخل H-04/H-18 و الزام تغییر قرارداد در صورت ناسازگاری؛ نتیجه مستقل مستند شود. هر ناسازگاری نیازمند ارجاع تصمیم مدیر است؛ UI/UX نباید خود قرارداد را ویرایش کند.
3. **QA:** پس از گزارش Coordinator، مستقل completeness اسناد، پوشش 360px/RTL و state maps را ارزیابی کند. **هیچ آزمون اجراشده browser/a11y/security بدون پیاده‌سازی گزارش PASS نمی‌شود**.
4. **Manager:** تنها مرجع پذیرش/ادغام/تکمیل H-18. PR تا تصمیم مدیر باز و ادغام‌نشده بماند.

## ۵. محدودیت‌ها
این PR فقط **مستندات طراحی** است؛ اجرای واقعى app/API، پایداری session، کنترل server role و تست مستقل QA انجام نشده‌اند. قوانین business در قرارداد Freeze‌شده باقی می‌مانند. سایر وظایف و موج‌ها تغییر نمی‌کنند.
