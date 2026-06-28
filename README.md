# MARCALERT

SaaS de **vigilancia de marcas** para agentes de propiedad industrial en Uruguay.
Detecta automáticamente colisiones entre la cartera de marcas de un agente y las
nuevas solicitudes publicadas en el Boletín de la Propiedad Industrial (DNPI/MIEM),
y notifica con tiempo suficiente para presentar oposición.

---

## Problema que resuelve

El Boletín de la Propiedad Industrial se publica dos veces por mes. Un agente IP con
50 clientes activos debe revisar manualmente cientos de solicitudes nuevas por boletín
para detectar si alguna colisiona con las marcas que protege. Un boletín no revisado
a tiempo puede significar perder el plazo de oposición y, con eso, la marca de su
cliente.

MARCALERT automatiza ese proceso: descarga el boletín, extrae cada solicitud, la
compara con toda la cartera y avisa solo cuando hay riesgo real, con el plazo de
oposición ya calculado.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11 + FastAPI |
| Base de datos | PostgreSQL 16 (multi-tenant por `tenant_id`) |
| Parser de PDF | `pdfplumber` (texto seleccionable — sin OCR) |
| Motor fonético | Determinístico propio (seseo, yeísmo, betacismo) + `rapidfuzz` |
| IA | Claude API (Anthropic) — explicaciones, visión, borradores |
| Email | Resend |
| Pagos | Stripe (suscripciones) |
| Scheduler | APScheduler + calendario hábil UY |
| Contenedores | Docker + docker-compose |

---

## Arquitectura en 3 capas (embudo de costo)

El diseño central es un embudo que hace 95% del trabajo gratis y solo invoca IA
sobre el puñado de candidatos que lo merecen:

```
Boletín completo (cientos de solicitudes)
        │
        ▼
┌─────────────────────────────────────────┐
│  CAPA A — gratis, determinística        │
│  Motor fonético rioplatense             │
│  · Seseo (c→s, z→s)                    │
│  · Yeísmo (ll→y)                       │
│  · Betacismo (v→b)                     │
│  · H silenciosa                        │
│  + Levenshtein ponderado + Soundex-ES  │
│  + Afinidad de clases de Niza          │
└──────────────┬──────────────────────────┘
               │ solo candidatos con score ≥ umbral
               ▼
┌─────────────────────────────────────────┐
│  CAPA B — IA barata (Claude Haiku)      │
│  Explicación del riesgo en lenguaje     │
│  natural, lista para el cliente final   │
└──────────────┬──────────────────────────┘
               │ solo marcas figurativas finalistas
               ▼
┌─────────────────────────────────────────┐
│  CAPA C — IA cara (Claude Vision)       │
│  Comparación de logos, razonamiento     │
│  visual, clasificación de Viena         │
└─────────────────────────────────────────┘
               │ acción del agente → tier Estudio
               ▼
        Borrador de oposición (Ley 17.011)
```

---

## Fuente de datos

**Boletín de la Propiedad Industrial — DNPI/MIEM**

- URL del índice por año:
  `https://www.gub.uy/ministerio-industria-energia-mineria/comunicacion/publicaciones/boletin-propiedad-industrial-ano-{AÑO}`
- URL directa del PDF (patrón confirmado):
  `.../files/documentos/publicaciones/Boletin%20{N}.pdf`
- Publicación **quincenal**: días 15 y último del mes. Si cae en no hábil, se publica
  el último día hábil anterior.
- PDF de texto seleccionable (~200 páginas, 1.5–6 MB).
- Estructura INID estándar WIPO: `(210)` expediente, `(540)` denominación, `(730)`
  solicitante, `(220)` fecha, `(511)` clases Niza, `(740)` agente, `(591)` colores.

---

## Planes de suscripción

| Plan | Marcas vigiladas | Borradores de oposición | Precio |
|------|-----------------|------------------------|--------|
| **Starter** | hasta 10 | — | USD 29/mes |
| **Pro** | hasta 50 | — | USD 79/mes |
| **Estudio** | ilimitadas | incluidos (Claude) | USD 199/mes |

Trial gratuito de 30 días. Sin tarjeta al registrarse.

> Los precios son hipótesis de partida — validar con entrevistas a agentes IP
> antes de publicar.

---

## Estructura del proyecto

```
MARCALERT/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan (scheduler)
│   │   ├── config.py                  # Settings (env vars)
│   │   ├── database.py                # SQLAlchemy (lazy engine)
│   │   ├── models/
│   │   │   ├── tenant.py              # Tenant + SubscriptionTier
│   │   │   ├── user.py                # Usuario del agente
│   │   │   ├── marca.py               # Cartera: marcas vigiladas
│   │   │   ├── boletin.py             # Boletines procesados + Solicitudes
│   │   │   └── alerta.py              # Colisiones detectadas + Métricas
│   │   ├── api/
│   │   │   ├── auth.py                # Registro, login, /me
│   │   │   ├── marcas.py              # CRUD cartera (límites por tier)
│   │   │   ├── alertas.py             # Dashboard + cambio de estado + borrador
│   │   │   ├── boletines.py           # Estado de procesamiento + ingesta manual
│   │   │   └── billing.py             # Stripe Checkout, Portal, Webhook
│   │   └── services/
│   │       ├── auth.py                # JWT
│   │       ├── parser/
│   │       │   └── pdf_parser.py      # Parser INID + extracción de logos
│   │       ├── matching/
│   │       │   ├── phonetic.py        # Motor fonético rioplatense
│   │       │   └── niza.py            # Afinidad de clases + score final
│   │       ├── calendar/
│   │       │   └── uruguay.py         # Días hábiles UY + deadline oposición
│   │       ├── ingest/
│   │       │   ├── downloader.py      # Descarga URL correlativa + health check
│   │       │   ├── pipeline.py        # Orquestador: descarga→parseo→matching→alertas
│   │       │   └── scheduler.py       # APScheduler quincenal
│   │       ├── notifications/
│   │       │   └── email.py           # Resend: alertas + health alerts al admin
│   │       ├── billing/
│   │       │   └── stripe_service.py  # Checkout, Portal, Webhook handler
│   │       └── ai/
│   │           ├── explain.py         # Capa B: Claude Haiku (explicación)
│   │           ├── vision.py          # Capa C: Claude Vision (logos)
│   │           └── draft.py           # Premium: borrador de oposición
│   ├── tests/
│   │   ├── test_phonetic.py           # Motor fonético rioplatense (11 tests)
│   │   ├── test_niza.py               # Afinidad de clases Niza (7 tests)
│   │   ├── test_calendar.py           # Calendario hábil UY (9 tests)
│   │   ├── test_parser.py             # Parser INID con datos reales (13 tests)
│   │   └── test_billing.py            # Stripe tier mapping (6 tests)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
├── docker-compose.yml
├── CLAUDE.md
└── README.md
```

---

## Arranque rápido (desarrollo local)

### Con Docker

```bash
cp .env.example .env       # completar las variables
docker compose up -d db    # levantar PostgreSQL
docker compose up backend  # API en http://localhost:8000
```

### Sin Docker

```bash
cd backend
pip install -r requirements.txt
# Crear DB PostgreSQL y configurar DATABASE_URL en .env
uvicorn app.main:app --reload
```

La API crea las tablas automáticamente al arrancar (en producción usar Alembic).

### Variables de entorno requeridas

```env
DATABASE_URL=postgresql://marcalert:marcalert@localhost:5432/marcalert
SECRET_KEY=<clave-aleatoria-larga>

# Stripe (obtener en dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ESTUDIO=price_...

# Claude / Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Resend (email)
RESEND_API_KEY=re_...
EMAIL_FROM=alertas@marcalert.uy
ADMIN_EMAIL=admin@marcalert.uy

# URLs
FRONTEND_URL=https://app.marcalert.uy
```

---

## Tests

```bash
cd backend
pip install pytest pytest-asyncio rapidfuzz jellyfish holidays pdfplumber
PYTHONPATH=. pytest -v
```

**46 tests, todos pasan.** Incluye caso de prueba real: expediente **586527**
(boletín 359, clases 35 y 43) validado contra el PDF oficial de DNPI.

---

## API endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Registro de agente (crea tenant + usuario admin) |
| `POST` | `/api/auth/token` | Login → JWT |
| `GET` | `/api/auth/me` | Perfil del usuario actual |
| `GET` | `/api/marcas/` | Listar cartera |
| `POST` | `/api/marcas/` | Agregar marca a vigilar |
| `PUT` | `/api/marcas/{id}` | Editar marca |
| `DELETE` | `/api/marcas/{id}` | Pausar vigilancia |
| `GET` | `/api/alertas/` | Dashboard de colisiones |
| `PATCH` | `/api/alertas/{id}/estado` | Marcar revisada / en oposición / descartada |
| `POST` | `/api/alertas/{id}/borrador` | Generar borrador de oposición (premium) |
| `GET` | `/api/boletines/` | Historial de boletines procesados |
| `POST` | `/api/boletines/ingest` | Ingesta manual (admin) |
| `GET` | `/api/billing/tier` | Info del plan activo |
| `POST` | `/api/billing/checkout` | Crear sesión de pago Stripe |
| `POST` | `/api/billing/portal` | Redirigir al portal de cliente Stripe |
| `POST` | `/api/billing/webhook` | Webhook de Stripe (sin auth JWT) |

Documentación interactiva disponible en `http://localhost:8000/docs` (Swagger UI).

---

## Plazo de oposición

El sistema calcula la fecha límite como **30 días hábiles** desde la fecha de
publicación del boletín (campo oficial de la portada, no la fecha de presentación
de la solicitud).

> **AVISO LEGAL:** El número de días hábiles debe verificarse contra la
> **Ley 17.011 de Marcas** y la normativa DNPI vigente antes de presentarlo como
> dato legal. Todas las fechas calculadas se muestran con el disclaimer
> _"fecha estimada — verificar con DNPI"_.

---

## Hoja de ruta

| Etapa | Estado |
|-------|--------|
| 1. Modelos multi-tenant + auth | ✅ |
| 2. Ingesta doble vía + scheduler + health check | ✅ |
| 3. Parser INID + extracción de logos | ✅ |
| 4. Motor fonético rioplatense (capa A) | ✅ |
| 5. Deadline hábil UY + feriados | ✅ |
| 6. Alertas + email (Resend) + dashboard API | ✅ |
| 7. Stripe + tiers + trial | ✅ |
| 8. Frontend React/Vite (dashboard) | ⏳ |
| 9. Alembic migrations | ⏳ |
| 10. CI/CD (GitHub Actions) | ⏳ |

---

## Notas de diseño

**Motor fonético propio:** el foso defensivo del producto es conocer la fonética
rioplatense real (seseo, yeísmo, betacismo). El motor es determinístico y no se
reemplaza con IA — es más rápido, más preciso para este dominio y sin costo variable.

**Logos:** los boletines contienen cientos de miles de "imágenes" vectoriales de
~0.5 pt² que son ruido. Los logos reales se identifican por área mínima (configurable,
por defecto 50 pt²) y se asignan al registro `(210)` más próximo en la misma página.
Si el volumen de marcas figurativas crece, la arquitectura permite hacer el swap
a embeddings visuales locales (CLIP) sin reescribir las capas superiores.

**Multi-tenant:** cada tabla incluye `tenant_id`; todas las queries del API lo
filtran. Un agente nunca ve datos de otro.
