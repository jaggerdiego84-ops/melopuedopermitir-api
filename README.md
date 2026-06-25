# melopuedopermitir.com — API

## Endpoints
- GET  /health           → health check
- POST /generar-pdf      → genera PDF (test)
- POST /crear-sesion-pago → crea sesión Stripe
- POST /webhook-stripe   → webhook de pago completado

## Variables de entorno (configurar en Render)
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- RESEND_API_KEY
