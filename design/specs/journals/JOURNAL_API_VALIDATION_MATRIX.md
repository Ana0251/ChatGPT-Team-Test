# H-19 — نگاشت فیلدها، وضعیت‌ها و خطاهای سند ↔ API rc.4

**Contract blob:** `f57de031224e21f09253642c210a778a60683711`; **Framework:** 1.3.0؛ این سند مشخصات است نه تست API.

## Endpoint map
| رویداد UI | HTTP/URL | DTO و پاسخ معتبر |
|---|---|---|
| فهرست | `GET /companies/{companyId}/journals` | query `page,page_size,status?,fiscal_year_id?` → `200 JournalPage` |
| ایجاد Draft | `POST /companies/{companyId}/journals` | `JournalDraftInput` → `201 Journal` حتی با warnings |
| جزئیات | `GET /companies/{companyId}/journals/{journalId}` | `200 Journal` |
| جایگزینی Draft | `PUT /companies/{companyId}/journals/{journalId}` | `JournalDraftInput` → `200 Journal`؛ posted=409 |
| حذف Draft | `DELETE /companies/{companyId}/journals/{journalId}` | `204` در صورت draft |
| ثبت قطعی | `POST /companies/{companyId}/journals/{journalId}/post` | headers CSRF + `Idempotency-Key` → `200 Journal(status=posted)` |
| برگشت | `POST /companies/{companyId}/journals/{journalId}/reverse` | JSON `{posting_date,reason}` + CSRF + `Idempotency-Key` → `201` reversal یا `200` replay همان درخواست |

## Field mapping با نوع canonical
| UI | API path/schema | نوع/اعتبارسنجی | روی صفحه |
|---|---|---|---|
| شرکت فعال | URL `companyId`; `Journal.company_id` | UUID، tenant scope | نام از context H-18، نه ورودی آزاد |
| سال مالی | `JournalDraftInput.fiscal_year_id` | UUID required | انتخاب از سال‌های همین شرکت |
| تاریخ سند | `JournalDraftInput.posting_date` | ISO Gregorian date required | تقویم شمسی؛ پیش از ارسال convert |
| شرح سند | `JournalDraftInput.description` | string optional | برچسب فارسی و ورودی چندخطی |
| ردیف‌ها | `JournalDraftInput.lines[]` | array required؛ هر عنصر DraftLine | افزودن/حذف سطر؛ ترتیب همان آرایه |
| حساب در ردیف | `lines[i].account_id` | UUID یا null یا absent در Draft | picker حساب؛ خالی مجاز با هشدار |
| شرح ردیف | `lines[i].description` | string optional | توضیح همان ردیف |
| بدهکار | `lines[i].debit` | Rial ASCII string optional در Draft | «مبلغ بدهکار (ریال)»، خالی ≠ صفر |
| بستانکار | `lines[i].credit` | Rial ASCII string optional در Draft | «مبلغ بستانکار (ریال)» |
| شماره سند | `Journal.voucher_number` | integer/null response | خروجی فقط‌خواندنی، null=تخصیص‌نیافته |
| وضعیت | `Journal.status` | draft/posted | badge متنی، منع ویرایش posted |
| برگشت‌خورده | `Journal.reversed` | boolean response | badge و پیوند متن‌دار |
| سند مرجع برگشت | `Journal.reversal_of_id` | UUID/null response | فقط‌خواندنی |
| تاریخ قطعی | `Journal.posted_at` | ISO timestamp UTC/null | فقط پس از server، با timezone مشخص |
| مجموع بدهکار/بستانکار | `Journal.total_debit/total_credit` | Rial string required | نمایش کامل حتی در draft ناقص |
| هشدار | `Journal.warnings[].code/field/line_index` | کد ساخت‌یافته، pointer، شاخص صفرمبنا | متن فارسی + تمرکز سطر i+1 |
| علت برگشت | reversal `reason` | non-empty string | فقط dialog برگشت |
| تاریخ برگشت | reversal `posting_date` | ISO date | ورودی جلالی و تبدیل به میلادی |

**خطاب به Developer:** `JournalLineInput` برای ردیف کامل است ولی بدنه عملیات Draft، `DraftLine` را می‌پذیرد. وجود `lines` ضروری است اما نبود فیلدهای جزء برای Draft می‌تواند هشدار تولید کند؛ `POST /post` بدنه Draft ندارد. شناسه سطر پایدار به `JournalDraftInput` اضافه نکنید؛ JSON Pointerها مثل `/lines/0/account_id` بر اساس ترتیب واقعی پاسخ/آرایه اعتبار دارند.

## Error and warning map (از ERRORS.md و OpenAPI)
| code | پیام فارسی و راهکار |
|---|---|
| `DRAFT_INCOMPLETE` | «پیش‌نویس ذخیره شد؛ اطلاعاتی هنوز ناقص است.» — بازگشت به فیلد |
| `DRAFT_UNBALANCED` | «پیش‌نویس ذخیره شد؛ جمع بدهکار و بستانکار برابر نیست.» — نمایش جمع‌ها |
| `LINE_MISSING_ACCOUNT` | «ردیف {n}: حساب انتخاب نشده است.» |
| `LINE_MISSING_AMOUNT` | «ردیف {n}: مبلغ بدهکار یا بستانکار را بررسی کنید.» |
| `LINE_ACCOUNT_NOT_POSTABLE` | «ردیف {n}: این حساب قابل ثبت سند نیست.» |
| `LINE_AMOUNT_INVALID` | «ردیف {n}: مبلغ معتبر ریالی وارد کنید.» |
| `DRAFT_DATE_OUTSIDE_PERIOD` | «تاریخ سند با دوره مالی انتخابی سازگار نیست.» |
| `422 ACCOUNT_NOT_POSTABLE` | روی `/lines/{i}/account_id` و `line_index` فوکوس؛ حساب قابل ثبت انتخاب شود |
| `422 UNBALANCED` | «جمع بدهکار و بستانکار برابر نیست؛ سند قطعی نشد.» |
| `422 JOURNAL_LINE_INVALID` | خطاهای `details[].field/reason/line_index` با فوکوس ردیف متناظر |
| `409 PERIOD_CLOSED` | «دوره مالی بسته است؛ امکان ثبت قطعی وجود ندارد.» |
| `409 JOURNAL_IMMUTABLE` | «سند قطعی قابل ویرایش یا حذف نیست.» |
| `409 DUPLICATE_POST` | «این سند قبلاً ثبت قطعی شده است.» — نمایش GET سند مرجع، نه ارسال مجدد |
| `409 IDEMPOTENCY_CONFLICT` | «اطلاعات درخواست با عملیات پیشین یکسان نیست؛ بررسی کنید.» |
| `403 ACCESS_DENIED` | «برای انجام این عملیات مجوز ندارید.» |
| `403 CSRF_INVALID` | «اعتبار نشست باید تجدید شود؛ اطلاعات را بررسی و دستی ارسال کنید.» یک GET refresh حداکثر |
| `401 SESSION_EXPIRED` | «نشست پایان یافت؛ دوباره وارد شوید.» انتخاب شرکت/سال دوباره تأیید شود |
| `404 RESOURCE_NOT_FOUND` | «سند یا حساب موردنظر در دسترس نیست.» عدم افشای tenant |
| `422 VALIDATION_ERROR` | متن `reason` محلی‌شده با `JSON Pointer`؛ raw `message` نمایش داده نشود |

`line_index` صفرمبناست و **ردیف نمایشی = index + 1**. در ردیف حذف/جابجایی، هشدار قبلی تا دریافت پاسخ مجدد با آرایه تازه قابل اتکا نیست؛ «در انتظار بررسی دوباره» نشان داده شود. برای هر خطای غیرشناخته‌شده فقط متن عمومی خنثی و `request_id` برای پشتیبانی، بدون داده شرکت دیگر/جزئیات token.

## محدودیت‌های تاییدپذیری
- `Journal.total_*` پاسخ سرور است، نه عدد تخمینی محلی. اگر ردیف‌ها تغییر کرده‌اند، عدد محلی با نشان «محاسبه موقت» جدا از جمع تأییدشده سرور است. مجموع دقیق ۲۰رقمی ممکن است بیش از ۲۰ رقم شود؛ UI نباید آن را کوتاه کند یا قبل از اعتبارسنجی سرور PASS نشان دهد.
- `Journal.warnings[]` اجازه ذخیره پیش‌نویس است، نه تضمین Posting. status=posted فقط با پاسخ GET/POST معتبر سرور و مجوز/دوره کنترل‌شده قابل ادعاست.
- کنترل نقش‌ها، open/closed بودن دوره و عدم دسترسی بین شرکت‌ها با backend است؛ UI صرفاً نمایش پیشگیرانه می‌دهد، نه مرجع امنیتی.
