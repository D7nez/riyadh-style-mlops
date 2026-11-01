# التحديث إلى Groq + Ollama — ابدأ هنا

هذا التحديث يضيف مقارنة فعلية بين المزودين. لن يقرر أن Groq أو Ollama أفضل قبل تشغيلهما ومراجعة النصوص.

## 1. حدّث المشروع الموجود

فك ضغط الأرشيف الجديد وانسخ محتويات مجلد `riyadh-style-mlops` فوق مجلد مشروعك الحالي، ووافق على استبدال ملفات الكود. لا تستبدل ملف `.env` الخاص بك؛ الأرشيف لا يحتويه أصلًا. احتفظ بمفاتيحك وإعدادات LangSmith الحالية. لا تشغّل `copy .env.example .env` عند التحديث، ولا تحذف Docker volumes. اسم مجلد المشروع نفسه يبقي MLflow وبياناته في volumes السابقة.

أصبحت النسخة تشمل إصلاح GPT-OSS الذي طبقناه، وتستعمل أسماء موديلاته بدل Llama القديمة. أضيفت تعريفات provider/model إلى LangSmith وتسمية استدعاءات النموذج حسب المرحلة بدل تكرار model_call فقط. ظهور التكلفة يظل معتمدًا على التسعير الصحيح؛ لا يوجد ادعاء بأن هذا اختُبر على حسابك بعد.

## 2. أبقِ Ollama شغّالًا على Windows

نستخدم تثبيت Ollama ونماذجك الموجودة. لا توجد حاوية Ollama جديدة، ولا أوامر pull تلقائية، ولا تعديل تلقائي على نماذجك.

من CMD:

```cmd
curl http://localhost:11434/api/tags
```

إذا لم يعمل، افتح تطبيق Ollama أولًا. اخترنا `qwen2.5:latest` و`gemma3:4b` كبداية من قائمتك، بسبب حجمهما النسبي وذاكرة RTX 3050 ذات 8GB. هذا تقدير اختيار أولي، وليس ضمانًا بأن النموذج والسياق سيبقيان بالكامل على GPU. لم نضع mixtral ذي 26GB أو gemma3:12b ذي 8.1GB في الإعداد الافتراضي. حجم الملف ليس مجموع الذاكرة المطلوبة.

## 3. ابنِ الصورة مرة واحدة

من مجلد المشروع في CMD:

```cmd
docker compose build api
docker compose up -d --no-build
```

خدمات API وMLflow والمقارنة تستخدم الآن الصورة نفسها `riyadh-style-mlops:local`. ترتيب Dockerfile الجديد يفصل تثبيت المكتبات عن نسخ الكود، مع cache لتنزيل pip. يتطلب أول بناء بعد هذا التغيير تثبيت الاعتماديات مرة جديدة؛ تعديل الكود لاحقًا لا يبطل طبقة المكتبات. الصورة الافتراضية خفيفة ولا تثبّت PyTorch أو E5؛ تعمل على TF-IDF الذي تستخدمه الآن.

إذا كان `.env` لديك يحدد `RETRIEVAL_BACKEND=e5`، إما تغيّره إلى `tfidf` لهذه المقارنة أو تضيف `INSTALL_SEMANTIC=true` وتعيد البناء. لا تحتاج ذلك إذا بقيت على TF-IDF.

## 4. افحص الاتصال والموديلات قبل إرسال طلبات توليد

```cmd
docker compose --profile tools run --rm --no-deps benchmark styleops doctor --config /app/configs/compare-smoke.yaml
```

هذا يختبر قائمة Groq وقائمة Ollama من داخل Docker. إذا كان موديل غير متاح يتوقف قبل بدء التقييم. عنوان Ollama الافتراضي من الحاوية هو `http://host.docker.internal:11434`، وليس localhost. يمكن تغييره في `.env` عبر `OLLAMA_BASE_URL`.

### إذا فشل اتصال Docker بـOllama

تحقق أولًا أن `curl http://localhost:11434/api/tags` يعمل على Windows. إذا عمل محليًا وفشل doctor من الحاوية، قد تحتاج جعل Ollama يستمع على واجهة يمكن لـDocker الوصول إليها. اخرج من تطبيق Ollama من أيقونة شريط النظام، ثم افتح نافذة CMD مستقلة ونفّذ:

```cmd
set OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

أبقِ النافذة مفتوحة وأعد doctor من نافذتك الأخرى. هذا يوسّع الاستماع للشبكة؛ لا تفتح المنفذ على الإنترنت، واقصر السماح في Windows Firewall على الشبكات/الاتصالات اللازمة. إعداد `set` مؤقت لهذه النافذة. لا تشغّل خادمين على المنفذ نفسه؛ رسالة address already in use تعني أن Ollama ما زال شغالًا.

## 5. تجربة صغيرة قبل المقارنة الكاملة

```cmd
docker compose --profile tools run --rm --no-deps benchmark styleops compare --config /app/configs/compare-smoke.yaml --cases /app/evaluation/smoke.jsonl
```

تجربة البداية: Groq GPT-OSS 120B مقابل Ollama Qwen2.5، على حالة واحدة، بتكرار واحد لكل منهما. لكل مرشح أيضًا warmup منفصل غير محسوب في متوسط الزمن. كل تشغيل سحابي يستهلك حصة مزودك.

افتح MLflow على http://localhost:5000 واختر **Model training → Experiments → riyadh-style-provider-smoke → Runs**. عند `success_rate=1` للمرشحين انتقل للاختبار الكامل.

## 6. المقارنة الكاملة

```cmd
docker compose --profile tools run --rm --no-deps benchmark
```

الإعداد الافتراضي `configs/compare.yaml` يقارن:

- Groq / `openai/gpt-oss-20b`
- Groq / `openai/gpt-oss-120b`
- Ollama / `qwen2.5:latest`
- Ollama / `gemma3:4b`

ثلاث حالات × تكرارين × أربعة مرشحين = **24 طلب إعادة صياغة مقاسًا**، إضافة إلى warmup واحد لكل مرشح. تجربة البداية المنفصلة لا تُدمج معها. لا تُطلق نسختين من benchmark بالتوازي على نفس GPU؛ ذلك يخلط أثر الحمل بأثر النموذج.

في MLflow اختر تجربة **riyadh-style-provider-comparison**، ثم حدّد أحدث 8 تشغيلات المرتبطة بنفس `batch_id` واضغط Compare. تظهر الأخطاء في artifact `results/predictions.json` وفي tag اسمه `evaluation_status`. قد تكون حالة MLflow التشغيلية FINISHED رغم فشل حالات داخلها؛ اعتمد `success_rate` و`failed_cases` و`evaluation_status`.

## كيف صُممت المقارنة؟

المقارنة الجديدة تقيس **إعادة الصياغة وحدها**. لكل حالة نثبّت النص الأصلي والـprompt والأمثلة المسترجعة مرة واحدة ثم نرسلها لكل مرشح. لا نستخدم مصنفًا سحابيًا أو مستخرج أفكار ولا مصححًا بعد التوليد في هذه المقارنة، حتى لا يغيّر مرشحٌ مدخل مرشح آخر أو يخفي الإصلاح عيوبه. التحويل العادي في التطبيق يحتفظ بمراحله الأصلية. لذلك زمن المقارنة الجديدة ليس زمن التطبيق الكامل.

فحوص الأسلوب والأرقام نفسها تطبق على جميع النتائج. `request_sha256` يثبت تطابق prompt والمدخل لنفس الحالة بين المرشحين، ويُحفظ السياق في `evaluation/frozen_inputs.json`. ترتيب المرشحين يُخلط ببذرة 42 وتُنفّذ طلبات كل مرشح تباعًا لتقليل تبديل الموديلات المحلية.

التكافؤ ليس كاملًا: النماذج مختلفة في الحجم والتدريب والتكميم والتوكنة والبنية. GPT-OSS له reasoning منخفض مخفي وحد توكنات لا يقل عن 4096 لتجنب فراغ الإجابة، بينما الميزانية الافتراضية لـOllama 1800 وسياق 8192. تُسجّل الحدود الفعلية والسياسات لكل تشغيل. هذه مقارنة إعدادات جاهزة لمهمتك؛ لا تعزل وحدها أثر المنصة أو حجم النموذج. إذا أردت عزل المنصة نحتاج نموذجًا مشتركًا وإعدادات متقاربة وتوثيق التكميم.

## ماذا أقارن؟

| المؤشر | التفسير |
|---|---|
| `success_rate` / `failed_cases` | نجاح إنتاج نتيجة؛ افحصه قبل الجودة والسرعة |
| `latency_s` / `latency_p95_s` | متوسط وP95 زمن الحالات الناجحة؛ لا يشمل warmup |
| `style_pass_rate` | اجتياز القواعد البرمجية، وليس التطابق الكامل مع أسلوب الكاتب |
| `number_recall` | الاحتفاظ بالأرقام الموجودة في المدخل |
| `new_number_count` | ظهور أرقام إضافية؛ راجعها يدويًا |
| `input_tokens` / `output_tokens` | استهلاك المزود؛ التوكنات ليست وحدة متكافئة بين tokenizers |
| `load_duration_s` | وقت تحميل موديل Ollama الذي أبلغ به الخادم؛ صفر Groq هنا يعني غير منطبق |
| `estimated_cost_usd` | يظهر فقط إذا زوّدت سعر المزود والموديل؛ غيابه لا يعني مجانًا |

الأسعار تُقرأ من `MODEL_PRICES_JSON` بمفتاح مثل `groq:openai/gpt-oss-120b` وقيمتي `input` و`output` بالدولار لكل مليون توكن. لا تُدرج تكلفة كهرباء أو عتاد محلي ضمن سعر التوكن بشكل مختلق. الـwarmup مستثنى من تكلفة المتوسط المقاس، واستهلاكه مسجل منفصلًا. لا نقيس peak VRAM أو الكهرباء تلقائيًا.

artifact `config/model_inventory.json` يسجل digest وحجم وتكميم موديلات Ollama المتاحة، و`config/local_runtime.json` يسجل snapshot لما أبلغ به `/api/ps` بعد warmup. ليس قياسًا لأقصى استخدام الذاكرة. من CMD يمكنك تشغيل `ollama ps` أثناء المقارنة لترى GPU/CPU allocation، و`nvidia-smi` لمراقبة الذاكرة. إذا كان جزء من النموذج على CPU فسجّل ذلك قبل مقارنة السرعات.

ثلاث حالات ليست كافية للحكم النهائي. وسّع `evaluation/cases.jsonl` إلى 20–50 نصًا مستقلًا، وراجع المعنى والأسلوب والأسماء والادعاءات المضافة بشريًا. لا توجد Accuracy موثوقة للصياغة من الفحوص الحالية، ولا اختيار فائز تلقائيًا.

## التقارير وLangSmith

تُكتب التقارير في `/app/reports/<batch_id>` داخل volume التقارير. يُطبع مسار المجلد في نهاية الأمر. لنسخها إلى جهازك دون إعادة التقييم:

```cmd
docker compose --profile tools run --name styleops-report-copy --no-deps benchmark python -c "print('Ready to copy existing reports')"
docker cp styleops-report-copy:/app/reports ./provider-reports
docker rm styleops-report-copy
```

داخل مجلد batch ستجد:

- `comparison.html`: جدول ونتائج كل حالة، يُفتح في المتصفح.
- `comparison.csv` و`comparison.json`: المقاييس المسجلة.
- `predictions.json`: النصوص الناتجة والأخطاء.
- `human_review.csv`: نموذج مراجعة بشرية للمعنى والأسلوب والعربية والادعاءات غير المسندة. لا يجمع درجات أو يختار فائزًا تلقائيًا.

في LangSmith تظهر مرحلة `compare_rewrite` وتحتها استدعاء `rewrite`. metadata تشمل `batch_id` و`mlflow_run_id` و`candidate` و`case_id` و`request_id`. سجل warmup معلّم بـ`warmup=true`. إذا أردت بقاء بيانات المقارنة المحلية على الجهاز، عطّل tracing أثناء تلك المقارنة؛ تفعيله يرسل النصوص إلى LangSmith وفق إعدادات إخفاء المدخلات والمخرجات، حتى إن كان النموذج محليًا.

## التعديل دون إعادة بناء أثناء التطوير

ملف `compose.dev.yaml` اختياري ويجعل المصدر والـprompts والواجهة/configs ملفات mounted:

```cmd
docker compose -f compose.yaml -f compose.dev.yaml up -d --no-build api
docker compose -f compose.yaml -f compose.dev.yaml --profile tools run --rm --no-deps benchmark
```

تعديلات الكود تُقرأ من الملفات مباشرة، وتعديلات config/cases تُرى في تشغيل المقارنة التالي. إذا تغيّرت الاعتماديات تحتاج بناءً جديدًا. وضع التطوير محلي فقط.

## تشغيل Ollama داخل التطبيق نفسه

المقارنة لا تغيّر `.env` أو نموذج واجهتك. إذا أردت تحويل التطبيق نفسه إلى Ollama، غيّر:

```dotenv
MODEL_BACKEND=ollama
GENERATION_MODEL=qwen2.5:latest
ANALYSIS_MODEL=qwen2.5:latest
RETRIEVAL_BACKEND=tfidf
```

ثم `docker compose up -d --no-build --force-recreate api`. حينها جميع مراحل النموذج في التطبيق تعمل محليًا. للعودة إلى Groq أعد قيم البيئة السابقة. لا يلزم تغيير APP_API_KEY أو مفاتيح LangSmith.

## التحقق والمراجع

اقرأ `VALIDATION.md` للتمييز بين الاختبارات الآلية والتشغيل الحقيقي. لا توجد نتائج تفوق Groq أو Ollama في هذه الحزمة؛ ستنتجها على جهازك.

- Ollama chat: https://docs.ollama.com/api/chat
- Ollama models and runtime: https://docs.ollama.com/api/tags وhttps://docs.ollama.com/api/ps
- Ollama networking/GPU: https://docs.ollama.com/faq
- LangSmith LLM metadata: https://docs.langchain.com/langsmith/log-llm-trace
- Docker cache ordering: https://docs.docker.com/build/cache/optimize/
