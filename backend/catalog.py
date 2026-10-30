from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import Field
from core import db, BaseDocument, now_iso

router = APIRouter(prefix="/api")

CATEGORIES = ["finance", "business", "productivity", "health", "education", "bundle"]


class Product(BaseDocument):
    slug: str
    name_en: str
    name_ar: str
    desc_en: str
    desc_ar: str
    details_en: List[str] = []
    details_ar: List[str] = []
    category: str
    price: float
    sale_price: Optional[float] = None
    image: str
    featured: bool = False
    active: bool = True
    sort: int = 0
    includes: List[str] = []
    created_at: str = Field(default_factory=now_iso)

    @property
    def effective_price(self) -> float:
        return self.sale_price if self.sale_price else self.price


def P(slug, en, ar, desc_en, desc_ar, det_en, det_ar, cat, price, sort, sale=None, featured=False, includes=None):
    return Product(slug=slug, name_en=en, name_ar=ar, desc_en=desc_en, desc_ar=desc_ar, details_en=det_en,
                   details_ar=det_ar, category=cat, price=price, sale_price=sale, image=f"/img/products/{slug}.jpg",
                   featured=featured, sort=sort, includes=includes or [])


FORMAT_EN = "Format: Excel workbook (English) + PDF guide, delivered as a ZIP"
FORMAT_AR = "الصيغة: ملف Excel (بالإنجليزية) + دليل PDF، في ملف ZIP"
MONEY_EN = ["Monthly dashboard — remaining balance and savings rate calculate automatically",
            "Transactions log for 100 entries with Income / Expense / Savings / Debt types",
            "Savings goals tracker for 30 goals with remaining amount calculated",
            "Step-by-step guide with a simple weekly money routine", FORMAT_EN]
MONEY_AR = ["لوحة شهرية — يُحسب الرصيد المتبقي ونسبة الادخار تلقائياً",
            "سجل معاملات لـ ١٠٠ عملية بأنواع دخل / مصروف / ادخار / دين",
            "متتبع أهداف الادخار لـ ٣٠ هدفاً مع حساب المبلغ المتبقي",
            "دليل خطوة بخطوة مع روتين مالي أسبوعي بسيط", FORMAT_AR]
BUSINESS_EN = ["Business snapshot with automatic profit-per-sale and monthly gross profit estimates",
               "Customer research worksheet with 8 validation questions",
               "10-step launch checklist with status tracking",
               "Guide with a 30-day action plan", FORMAT_EN]
BUSINESS_AR = ["ملخص المشروع مع حساب تلقائي للربح لكل عملية بيع والربح الإجمالي الشهري",
               "ورقة بحث العملاء مع ٨ أسئلة للتحقق من الفكرة",
               "قائمة إطلاق من ١٠ خطوات مع تتبع الحالة",
               "دليل مع خطة عمل لمدة ٣٠ يوماً", FORMAT_AR]
HABIT_EN = ["30-day tracker for up to 10 habits with automatic completed count",
            "Weekly reflection sheet", "Guide to building habits that last", FORMAT_EN]
HABIT_AR = ["متتبع لمدة ٣٠ يوماً لـ ١٠ عادات مع عدّ تلقائي للأيام المكتملة",
            "ورقة مراجعة أسبوعية", "دليل لبناء عادات تدوم", FORMAT_AR]

SEED = [
    P("nova-money-planner", "NOVA MONEY PLANNER", "مخطط نوفا المالي",
      "A personal finance planner that brings your income, spending, savings and goals into one calm monthly system.",
      "مخطط مالي شخصي يجمع دخلك ومصاريفك ومدخراتك وأهدافك في نظام شهري واحد هادئ.",
      MONEY_EN, MONEY_AR,
      "finance", 39, 1, sale=25, featured=True),
    P("nova-business-starter", "NOVA BUSINESS STARTER", "نوفا لبدء الأعمال",
      "A beginner business planning toolkit with business ideas, budget planning and launch checklists.",
      "مجموعة أدوات تخطيط للمبتدئين تتضمن أفكار مشاريع وتخطيط الميزانية وقوائم مراجعة الإطلاق.",
      BUSINESS_EN, BUSINESS_AR, "business", 59, 2),
    P("nova-habit-tracker", "NOVA HABIT TRACKER", "متتبع العادات من نوفا",
      "A daily habit tracking and productivity planner.",
      "مخطط يومي لتتبع العادات وزيادة الإنتاجية.",
      HABIT_EN, HABIT_AR, "productivity", 19, 3),
    P("nova-fitness-planner", "NOVA FITNESS PLANNER", "مخطط اللياقة من نوفا",
      "A workout, progress and fitness tracking planner.",
      "مخطط للتمارين وتتبع التقدم واللياقة البدنية.",
      ["Workout plans", "Progress tracking", "Fitness logs"], ["خطط التمارين", "تتبع التقدم", "سجلات اللياقة"],
      "health", 29, 4),
    P("nova-study-planner", "NOVA STUDY PLANNER", "مخطط الدراسة من نوفا",
      "A study schedule, revision and exam preparation planner.",
      "مخطط لجدول الدراسة والمراجعة والاستعداد للاختبارات.",
      ["Study schedules", "Revision planner", "Exam preparation pages"], ["جداول الدراسة", "مخطط المراجعة", "صفحات الاستعداد للاختبارات"],
      "education", 25, 5),
    P("nova-goal-master", "NOVA GOAL MASTER", "نوفا لإتقان الأهداف",
      "A personal goal setting and progress tracking planner.",
      "مخطط لتحديد الأهداف الشخصية وتتبع التقدم.",
      ["Goal setting framework", "Progress tracking"], ["إطار لتحديد الأهداف", "تتبع التقدم"],
      "productivity", 29, 6),
    P("nova-budget-pro", "NOVA BUDGET PRO", "نوفا للميزانية برو",
      "An advanced monthly and yearly budgeting toolkit.",
      "مجموعة أدوات متقدمة للميزانية الشهرية والسنوية.",
      ["Monthly budgeting", "Yearly budgeting"], ["الميزانية الشهرية", "الميزانية السنوية"],
      "finance", 49, 7),
    P("nova-life-organizer", "NOVA LIFE ORGANIZER", "منظم الحياة من نوفا",
      "A complete personal life organization planner.",
      "مخطط متكامل لتنظيم حياتك الشخصية.",
      ["Personal organization pages", "Planning sections for everyday life"], ["صفحات التنظيم الشخصي", "أقسام تخطيط للحياة اليومية"],
      "productivity", 39, 8),
    P("nova-content-planner", "NOVA CONTENT PLANNER", "مخطط المحتوى من نوفا",
      "A social media content calendar and planning toolkit.",
      "تقويم ومجموعة أدوات لتخطيط محتوى وسائل التواصل الاجتماعي.",
      ["Content calendar", "Post planning toolkit"], ["تقويم المحتوى", "أدوات تخطيط المنشورات"],
      "business", 35, 9),
    P("nova-ultimate-bundle", "NOVA ULTIMATE BUNDLE", "باقة نوفا الشاملة",
      "A bundle containing all nine NOVA digital products.",
      "باقة تحتوي على جميع منتجات نوفا الرقمية التسعة.",
      ["All nine NOVA planners", "One purchase, every download"], ["جميع مخططات نوفا التسعة", "عملية شراء واحدة لكل التحميلات"],
      "bundle", 149, 0, featured=True,
      includes=["nova-money-planner", "nova-business-starter", "nova-habit-tracker", "nova-fitness-planner",
                "nova-study-planner", "nova-goal-master", "nova-budget-pro", "nova-life-organizer", "nova-content-planner"]),
]


def public(p: Product) -> dict:
    return p.out()


async def seed_products():
    await db.products.create_index("slug", unique=True)
    for p in SEED:
        if not await db.products.find_one({"slug": p.slug}):
            await db.products.insert_one(p.to_mongo())


async def get_product(slug: str, active_only=True) -> Product:
    q = {"slug": slug}
    if active_only:
        q["active"] = True
    doc = await db.products.find_one(q)
    if not doc:
        raise HTTPException(404, "Product not found")
    return Product.from_mongo(doc)


@router.get("/products")
async def list_products():
    docs = await db.products.find({"active": True}).sort("sort", 1).to_list(200)
    return [public(Product.from_mongo(d)) for d in docs]


@router.get("/products/{slug}")
async def product_detail(slug: str):
    return public(await get_product(slug))
