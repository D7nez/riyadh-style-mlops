# الإصدار 0.3

ابدأ بـ[تحديث الجودة](QUALITY_UPGRADE_AR.md)، ثم راجع [دليل التشغيل والمقارنة](UPGRADE_AR.md).

# الإصدار 0.2 — Groq + Ollama

ابدأ بـ[دليل التحديث والمقارنة](UPGRADE_AR.md). الدليل أدناه يخص بنية الإصدار الأول؛ إذا تعارضت خطوات Docker أو أسماء النماذج فدليل التحديث هو المرجع.

# Riyadh Style MLOps — مشروع الصياغة العربية

تحويل النوتبوك المرفق إلى تطبيق Python مستقل مع RAG وFastAPI وواجهة عربية وMLflow وLangSmith وDocker Compose وCI. نقطة البداية Python 3.12. هذا مشروع تطوير محلي قابل للتوسعة، وليس ادعاءً باكتمال نشر إنتاجي أو اعتماد جودة المخرجات.

## ابدأ من هنا

1. فك ضغط المشروع وافتح مجلده في VS Code.
2. ثبّت Docker Desktop وشغّله.
3. انسخ `.env.example` إلى `.env` (الأمر يعمل في PowerShell أيضًا):

```powershell
cp .env.example .env
docker compose up --build -d
```

التحميل الأول قد يستغرق وقتًا لأن الصورة تشمل مكتبة embeddings. وضع البداية `mock + tfidf` يعمل دون مفاتيح ودون تنزيل نموذج E5. يعيد mock النص كما هو ولا يقيس جودة الذكاء الاصطناعي.

افتح:

- التطبيق: http://localhost:8000
- تجربة API: http://localhost:8000/docs
- MLflow: http://localhost:5000

## تشغيل النماذج الحقيقية

النوتبوك الأصلي يحتوي على مفتاح Groq مكشوف. ألغِ ذلك المفتاح وأنشئ مفتاحًا جديدًا. الأرشيف المرفق داخل المشروع منزوع المفتاح ومخرجات الخلايا. لا تضع المفتاح داخل الكود أو Git.

عدّل `.env`:

```dotenv
MODEL_BACKEND=groq
RETRIEVAL_BACKEND=e5
GROQ_API_KEY=ضع_مفتاحك_الجديد
GENERATION_MODEL=llama-3.3-70b-versatile
ANALYSIS_MODEL=llama-3.1-8b-instant
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=ضع_مفتاح_لانق_سمث
LANGSMITH_PROJECT=riyadh-style
```

ثم:

```powershell
docker compose up -d --force-recreate api
```

E5 يحمّل `intfloat/multilingual-e5-base` من Hugging Face أول مرة ويخزن النموذج في volume. إذا كانت الشبكة أو ذاكرة جهازك لا تسمح بذلك، استخدم `RETRIEVAL_BACKEND=tfidf`؛ هذا baseline مختلف عن الاسترجاع الدلالي الأصلي. يمكنك تغيير نموذج embedding عبر البيئة، وسيتغير مفتاح cache تلقائيًا. نموذج LLM يعمل عند Groq؛ Docker لا يحوّله إلى نموذج محلي ولا يحتاج GPU محليًا. الاسترجاع بـE5 هنا يعمل افتراضيًا على CPU.

## أين أرى كل شيء؟

| المطلوب | المكان | ماذا ترى؟ |
|---|---|---|
| إدخال نص وتجربة التطبيق | http://localhost:8000 | الناتج، معرف الطلب، المقاييس والأمثلة |
| تجربة HTTP مباشرة | `/docs` | المخطط والتحقق من المدخلات |
| تتبّع الطلب | مشروعك في https://smith.langchain.com | استدعاء `style_transform` وفروع النموذج والاسترجاع والمراجعة |
| مقارنة النماذج | MLflow، تجربة `riyadh-style-groq` | metrics وparams وartifacts لكل تكرار |
| أخطاء التشغيل | `docker compose logs -f api` | معرف الطلب، المرحلة، الزمن ونوع الخطأ |
| فحص متغيرات الكود خطوة خطوة | VS Code → Run and Debug → Debug API (local) | breakpoints والمتغيرات والـcall stack |

يرتبط الـtrace بمعرف الطلب عبر metadata. وفي التقييم تضاف `mlflow_run_id` و`case_id` و`repeat` للربط بين نظامي الرصد. LangSmith يستخدم تزيين `traceable` المباشر؛ لا تحتاج إدخال LangGraph في مسار خطّي ثابت.

إعدادا `LANGSMITH_HIDE_INPUTS=true` و`LANGSMITH_HIDE_OUTPUTS=true` يخفيان النصوص في traces افتراضيًا. لرؤية المدخلات والنتائج خلال التطوير على نصوص مسموح بإرسالها، اجعلهما `false` ثم أعد إنشاء خدمة API. هذا يرسل المدخلات والمخرجات إلى خدمة LangSmith الخارجية. MLflow يخزن مخرجات التقييم وأمثلة التقييم محليًا؛ لا تضف إليها بيانات حساسة دون سياسة مناسبة.

## مقارنة أكثر من نموذج

عدّل `configs/benchmark.yaml` لاختيار موديلات Groq المتاحة لحسابك وعدد التكرارات. مسار التحليل والمراجعة ثابت عبر `ANALYSIS_MODEL`، ونموذج إعادة الصياغة وحده يتغير في هذه المقارنة.

```powershell
docker compose --profile tools run --rm benchmark
```

افتح تجربة `riyadh-style-groq` في MLflow، حدّد runs ثم Compare. كل run يمثل نموذجًا وتكرارًا على نفس حالات التقييم، مع خلط ترتيب التشغيل ببذرة ثابتة لتقليل تأثير ترتيب الشبكة.

المقاييس:

- `latency_s`: متوسط زمن الطلبات الناجحة.
- `input_tokens` و`output_tokens`: متوسط الاستهلاك لجميع مراحل النموذج، بما فيها الإصلاح إن حدث.
- `style_pass_rate`: نسبة اجتياز قواعد الأسلوب البرمجية بين الحالات الناجحة.
- `number_recall`: نسبة الأرقام الموجودة في المدخل التي بقيت في المخرج.
- `new_number_count`: عدد الأرقام الجديدة، كمؤشر يتطلب مراجعة.
- `success_rate` و`failed_cases`: لا يتم إخفاء فشل النماذج من التقرير.

قياس الأرقام ليس إثباتًا لصحة الحقائق؛ لا يتحقق من الأسماء والمعنى ولا يكتشف تبديل الرقم بين كيانين. التقييم الأسلوبي آلي جزئي، ولا يقيس التطابق الكامل مع أسلوب الكاتب. مجموعة البداية ثلاث حالات مصطنعة مكتوبة يدويًا وليست benchmark معتمدًا. وسّعها إلى 20–50 حالة مستقلة، وأضف تقييمًا بشريًا للمعنى والأسلوب قبل اختيار النموذج.

التكلفة اختيارية: أضف `MODEL_PRICES_JSON` في `.env` بصيغة JSON، لكل نموذج توليد وتحليل مفتاح يحوي `input` و`output` بالدولار لكل مليون token. حين تكون أسعار جميع الاستدعاءات متوفرة يسجّل `estimated_cost_usd`. لا توجد أسعار أو نتائج جودة مختلقة، والتقدير ليس فاتورة المزود.

الـartifacts في MLflow تحتوي config وحالات التقييم وprompt ونتيجة كل حالة ومعرف الطلب. ملفات `comparison.csv` و`comparison.json` تُكتب أيضًا في volume التقارير. لاستخراجها:

```powershell
docker compose --profile tools run --name styleops-eval benchmark
docker cp styleops-eval:/app/reports ./reports
docker rm styleops-eval
```

لا تستخدم `--rm` في هذا المثال لأن النسخ يتم بعد انتهاء الحاوية. تقارير mock في تجربة منفصلة، ولا يجوز استخدامها لترتيب النماذج أو الادعاء بأن 70B أفضل أو أسوأ من 8B.

## تنظيم المشروع

| الملف/المجلد | المسؤولية |
|---|---|
| `src/styleops/config.py` | الإعدادات والتحقق منها |
| `schemas.py` | عقود المدخلات وتصنيف الموضوع |
| `retrieval.py` | قراءة CSV وتنظيف boolean وE5/TF-IDF والاسترجاع الموزون |
| `llm.py` | Groq، timeout وretries محدودة، التوكنات وLLM spans |
| `pipeline.py` | ترتيب المراحل وتجميع المقاييس ومعرفات النسخ |
| `review.py` | قواعد الأسلوب وفحوص الأرقام وإعادة فحص النص المصحح |
| `api.py` | FastAPI ومعرف الطلب ومفتاح التطبيق الاختياري |
| `evaluate.py` | المقارنة وMLflow وتسجيل النجاح والفشل |
| `cli.py` | تشغيل التحويل والتقييم من terminal |
| `prompts/style_v1.txt` | بصمة الأسلوب الأصلية مستقلة عن الكود |
| `data.csv` | نسخة البيانات الـ37 المرفقة |
| `configs/benchmark.yaml` | اختيار نماذج المقارنة والتكرارات |
| `evaluation/cases.jsonl` | مدخلات اختبار مستقلة عن نصوص الاسترجاع |
| `tests/` | اختبارات المسار والتحقق والأخطاء والتقييم |
| `notebooks/original_sanitized.ipynb` | مرجع تاريخي منزوع الأسرار؛ ليس نقطة التشغيل |
| `.vscode/launch.json` | تشغيل debugger محليًا |
| `.github/workflows/ci.yml` | اختبارات وbuild وتشغيل Docker على GitHub Actions |

## ما الذي تغيّر عن النوتبوك؟

تم الاحتفاظ ببصمة الأسلوب واختيار نمط البداية ومراحل التصنيف والاسترجاع واستخراج الأفكار والصياغة والإصلاح، مع نفس تعزيز الموضوع `0.15` والخصائص `0.05` وأول 400 حرف للتمثيل وأول 600 حرف للمثال. أضفنا فصل الاعتماديات وإعدادات البيئة والتحقق من JSON ومعالجة واضحة لفشل التصنيف وإعادة فحص الإصلاح. تعليمات جديدة تمنع أخذ أرقام الأمثلة كحقائق للمدخل.

لم يتم تدريب نموذج جديد: هذا **LLMOps/RAGOps** مع أدوات MLOps للتجارب والنسخ والتقييم. لا توجد أوزان مدرّبة جديدة لتسجيلها في Model Registry. نستعمل hashes للبيانات والـprompt مع نموذج المزود وإعداداته وGit commit لتوثيق التجربة. هذا نقل منظم مع تعديلات موثقة؛ لم ندّعِ تطابق المخرجات حرفيًا مع النوتبوك.

لا تختبر جودة إعادة الصياغة بإعطاء نفس نصوص corpus كمدخلات ثم استرجاعها كأمثلة. عند استخدام حالة من البيانات، ضع معرفها في `exclude_ids` داخل ملف JSONL؛ مثال `"exclude_ids": ["1"]`. الأفضل الاحتفاظ بمدخلات تقييم مستقلة.

## تشغيل محلي وDebug

من مجلد المشروع:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-tested.txt
python -m pip install -c requirements-tested.txt -e ".[semantic,dev]"
python -m uvicorn styleops.api:app --reload
```

على Linux/macOS: `source .venv/bin/activate` بدل أمر التفعيل في Windows. `requirements-tested.txt` يثبّت نسخ الاعتماديات المباشرة التي اختُبرت؛ ليس lock كاملًا لجميع الاعتماديات المتعدية. امتداد semantic اختياري للشغل المحلي بـTF-IDF.

في VS Code اختر interpreter الخاص بـ`.venv` وثبّت Python وPython Debugger. ضع breakpoint في `pipeline.py` عند استدعاء التصنيف أو الاسترجاع أو الصياغة، ثم شغّل **Debug API (local)** واضغط التحويل من الواجهة. افحص `meta` و`examples` و`ideas` و`draft` و`final`. شغّل **Debug benchmark** لفحص تسجيل التجارب. الـdebugger هنا محلي؛ لا يوجد منفذ remote debug مكشوف في Docker.

MLflow محلي خارج Docker:

```powershell
python -m mlflow server --host 127.0.0.1 --port 5001 --backend-store-uri sqlite:///mlflow.db
styleops benchmark
```

يشترك الأمران في SQLite طالما شُغّلا من مجلد المشروع. يستخدم Docker SQLite داخل volume مستقل. لا تخلط نتائج الخادم المحلي بخادم Docker عند المقارنة.

الاختبارات:

```powershell
python -m pytest -q
docker compose run --rm api python -m pytest -q
```

## Troubleshooting

| العارض | التشخيص والإجراء |
|---|---|
| المفتاح غير صحيح / خطأ مزود | افحص نوع الخطأ في logs ثم صحح المفتاح محليًا؛ لا ترسله في محادثة أو screenshot |
| 429 | خفّض التكرارات أو تتابع الطلبات؛ SDK يعيد المحاولة مرتين للأنواع المدعومة |
| لا توجد traces | فعّل tracing وتحقق من المفتاح والمشروع والاتصال وأعد إنشاء API؛ تتبّع أول استدعاء ناجح |
| ترى traces لكن النص مخفي | إعدادا hide inputs/outputs مفعّلان |
| MLflow لا يستقبل التجارب | انتظر healthcheck وتأكد من خدمة mlflow ومن `MLFLOW_TRACKING_URI` |
| E5 يطول أو يفشل | يحتاج تنزيلًا أول مرة ومساحة وذاكرة؛ جرّب TF-IDF لعزل المشكلة |
| الناتج مثل المدخل تمامًا | أنت في `MODEL_BACKEND=mock` |
| `review_required=true` | لم تُحل جميع المخالفات أو تغيّرت الأرقام أو فشل التصنيف؛ راجع الناتج |
| 401 من التطبيق | أدخل نفس `APP_API_KEY` المحدد في البيئة |
| تغييرات `.env` لم تظهر | استخدم `docker compose up -d --force-recreate api` |

## حدود النشر

المنافذ مربوطة بـlocalhost للتطوير، وليس هناك مستخدمون وصلاحيات متعددة أو TLS أو rate limiting أو طابور وظائف. أضف هذه العناصر ونسخًا احتياطية لـMLflow قبل نشره على الإنترنت. `APP_API_KEY` يقيّد التحويل فقط؛ MLflow واجهة تطوير محلية. `docker compose down` يحفظ volumes؛ لا تستخدم `down -v` إلا إذا أردت حذف البيانات المخزنة.

قاعدة البيانات والـembedding cache لهما volumes ثابتة. تعديل CSV يتطلب إعادة بناء الصورة وإعادة تشغيل الخدمات، وتغيير البيانات يبطل embedding cache بالـhash. أضف بيانات جديدة إلى CSV بالـschema نفسه ثم أعد الاختبارات والتقييم قبل اعتمادها. لا يوجد إدخال حي غير مراقب للبيانات في هذه النسخة.

## مراجع التنفيذ

- LangSmith custom instrumentation: https://docs.langchain.com/langsmith/annotate-code
- LangSmith إخفاء المدخلات والمخرجات: https://docs.langchain.com/langsmith/mask-inputs-outputs
- MLflow Tracking: https://mlflow.org/docs/latest/ml/tracking/
- MLflow allowed hosts: https://mlflow.org/docs/latest/self-hosting/security/network/
- Groq model IDs: https://console.groq.com/docs/models
