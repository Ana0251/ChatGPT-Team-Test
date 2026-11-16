# H-19 — نگاشت دقیق UI کدینگ ↔ OpenAPI rc.4

**Blob مرجع:** `f57de031224e21f09253642c210a778a60683711`، نسخه `1.0.0-rc.4`. نگاشت endpoint و schema زیر تغییر قرارداد نیست.

## Endpoint و ورودی/خروجی
| عمل رابط | HTTP | نگاشت/پاسخ مورد انتظار |
|---|---|---|
| بازکردن فهرست/زیرحساب‌ها | `GET /companies/{companyId}/accounts?page=&page_size=&parent_id=` | `AccountPage.items/page/page_size/total`؛ parent_id اختیاری |
| ساخت حساب | `POST /companies/{companyId}/accounts` | بدنه `AccountInput`؛ `201 Account` |
| جزئیات | `GET /companies/{companyId}/accounts/{accountId}` | `200 Account` |
| تغییر نام/فعال | `PATCH /companies/{companyId}/accounts/{accountId}` | فقط `{name?,active?}`، minProperties=1؛ `200 Account` |
| حذف | `DELETE /companies/{companyId}/accounts/{accountId}` | `204` فقط برای حساب مجازِ بدون استفاده/فرزند |

## Field mapping
| UI label | API | نوع/قواعد قراردادی | نمایش/ویرایش |
|---|---|---|---|
| شرکت فعال | path `companyId` | UUID، از context عضویت H-18 | نمایش نام؛ شناسه LTR؛ نه از فرم آزاد |
| والد | `AccountInput.parent_id` | UUID یا null | group=null؛ سایر سطح‌ها انتخاب والد هم‌شرکتی صحیح |
| کد جزء | `AccountInput.code` | string 1..64 | حفظ **تمام** صفرهای پیشرو، بلااستثنا بدون عددسازی |
| عنوان | `AccountInput.name` | string 1..200 | فارسی/Unicode؛ label همواره نمایان |
| سطح | `AccountInput.level` | group/general/subsidiary/detail | گزینهٔ فارسی با value استاندارد |
| فعال | `AccountInput.active` | boolean، پیش‌فرض true | switch با برچسب «فعال» |
| شناسه حساب | `Account.id` | UUID output | read-only |
| کد کامل | `Account.full_code` | string computed output | read-only؛ copy عین رشته |
| قابل ثبت در سند | `Account.postable` | boolean computed output | read-only، تنها پاسخ سرور |
| صفحه/اندازه | query `page/page_size` | پارامترهای قراردادی | pagination کنترل‌شده |
| زیرحساب‌های والد | query `parent_id` | UUID | سرور صفحه‌بندی دارد؛ فرض «تمام فرزندان» ممنوع |

## Error → UI recovery
| HTTP / code | متن و اقدام |
|---|---|
| 401 SESSION_EXPIRED | «نشست پایان یافته است.» ورود دوباره و بازبینی شرکت |
| 403 ACCESS_DENIED | «برای این عملیات مجوز ندارید.» بدون جابه‌جایی خودکار شرکت |
| 403 CSRF_INVALID | یک refresh امن GET، سپس ارسال مجدد فقط دستی |
| 404 RESOURCE_NOT_FOUND | «حساب موردنظر در دسترس نیست.» بدون افشای شرکت دیگر |
| 409 ACCOUNT_IN_USE | «این حساب به علت داشتن وابستگی قابل حذف نیست.» بدون پاک‌کردن ردیف |
| 409 conflict other | «ثبت حساب با تعارض مواجه شد. کد و والد را بررسی کنید.» جزئیات فیلدی تنها از `error.details` |
| 422 VALIDATION_ERROR | `details[].field` JSON Pointer نظیر `/code` / `/name` / `/level` و `reason`؛ فوکوس اولین ورودی نامعتبر |

**تذکر دقت:** API الزاماً کد جداگانه‌ای برای duplicate code تعریف نکرده است؛ هر 409 نباید با قطعیت duplicate نامیده شود. کد خطا و `details` واقعی تعیین‌کننده‌اند. مرتب‌سازی و جست‌وجوی سراسری server-side برای accounts در rc.4 منتشر نشده‌اند. هیچ فیلد `parent_id/level/code` در PATCH مجاز نیست.
