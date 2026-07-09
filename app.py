import os, json, base64, traceback
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import stripe
import resend
import io
import threading
import time
import urllib.request
from pdf_generator import generate_pdf

import anthropic
import re as _re

def generar_noticias(user_data):
    """Genera noticias personalizadas usando Claude, conectadas al tipo de gasto
    y a la situacion financiera concreta del usuario. Reintenta una vez si falla,
    ya que ahora se ejecuta en segundo plano y no hay limite de tiempo de Stripe."""
    ciudad   = user_data.get('ciudad', 'España')
    tipo     = user_data.get('tipo_gasto', 'otro')
    ingresos = user_data.get('ingresos', 0)
    ratio    = user_data.get('ratio', 0)
    margen   = user_data.get('margen', 0)
    color    = user_data.get('color', 'verde')

    tipo_labels = {'hijo':'guardería o tener un hijo','vivienda':'vivienda o alquiler',
                  'coche':'coche','formacion':'formación','capricho':'capricho','otro':'gasto personal'}
    tl = tipo_labels.get(tipo, 'gasto personal')

    color_context = {
        'verde':    'tiene margen y su situación es saludable',
        'amarillo': 'tiene margen ajustado y conviene que vigile su situación',
        'rojo':     'tiene poco o ningún margen y su situación es delicada',
    }
    cc = color_context.get(color, color_context['verde'])

    prompt = (
        f'Un usuario en {ciudad} acaba de evaluar en melopuedopermitir.com si puede permitirse un gasto de {tl}. '
        f'Sus datos: ingresos {round(ingresos)}€/mes, ratio de compromisos financieros {round(ratio)}%, '
        f'margen libre {round(margen)}€/mes. El resultado de su análisis fue "{color}": {cc}.\n\n'
        f'Genera 5 noticias o datos financieros de actualidad en España (2025-2026) que sean genuinamente '
        f'relevantes para ESTA persona concreta, no genéricas. Cada una debe conectar con al menos uno de estos dos ejes: '
        f'(a) su tipo de gasto concreto ({tl}) — ayudas, normativa, precios o tendencias relacionadas; '
        f'(b) su situación financiera actual — datos del Banco de España, INE, OCDE o BCE sobre ratios de '
        f'endeudamiento, tipos de interés, ahorro o coste de vida que tengan sentido para alguien en su rango '
        f'de ingresos y con un veredicto "{color}".\n\n'
        'Para cada noticia incluye una URL real si la conoces con certeza; si no estás seguro, deja la URL vacía '
        '(mejor vacía que inventada). '
        'Responde ÚNICAMENTE con JSON, sin texto antes ni después: '
        '[{"contexto":"por que le afecta a ESTA persona en concreto, 1-2 frases, citando su dato de ratio, margen o tipo de gasto",'
        '"titular":"titular con gancho directo","desarrollo":"4-5 frases con datos y cifras concretas",'
        '"fuente":"nombre del medio u organismo","fecha":"2025 o 2026","url":"https://... o vacio"}]'
    )

    for intento in range(2):
        try:
            client = anthropic.Anthropic(
                api_key=os.environ.get('ANTHROPIC_API_KEY', ''),
                timeout=60.0
            )
            response = client.messages.create(
                model='claude-sonnet-4-6',
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            start = text.find('['); end = text.rfind(']')
            if start >= 0 and end >= 0:
                noticias = json.loads(text[start:end+1])
                if noticias:
                    return noticias[:5]
            print(f"==> Intento {intento+1}: respuesta sin JSON valido")
        except Exception as e:
            print(f"==> Intento {intento+1} fallo generando noticias: {e}")
    return []



app = Flask(__name__)
CORS(app)

# Deduplicacion de webhooks — persiste en disco para sobrevivir reinicios
import tempfile, os as _os

_DEDUP_FILE = _os.path.join(tempfile.gettempdir(), 'melopermitir_processed.txt')

def _ya_procesado(key):
    try:
        if _os.path.exists(_DEDUP_FILE):
            with open(_DEDUP_FILE, 'r') as f:
                return key in f.read()
        return False
    except:
        return False

def _marcar_procesado(key):
    try:
        with open(_DEDUP_FILE, 'a') as f:
            f.write(key + '\n')
        # Limpiar si el archivo crece demasiado
        if _os.path.getsize(_DEDUP_FILE) > 50000:
            _os.remove(_DEDUP_FILE)
    except:
        pass

stripe.api_key        = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
RESEND_API_KEY        = os.environ.get('RESEND_API_KEY', '')
resend.api_key        = RESEND_API_KEY

# ── KEEP ALIVE — ping cada 14 minutos para no dormir en Render free ──
def keep_alive():
    while True:
        time.sleep(14 * 60)
        try:
            url = os.environ.get('RENDER_EXTERNAL_URL', 'https://melopuedopermitir-api.onrender.com')
            urllib.request.urlopen(url + '/health', timeout=10)
            print("==> Keep-alive ping OK")
        except Exception as e:
            print(f"==> Keep-alive ping failed: {e}")

threading.Thread(target=keep_alive, daemon=True).start()


def _enviar_email_noticias(email, nombre, user_data):
    """Genera noticias y manda el segundo email HTML. Pensado para ejecutarse
    en un hilo de fondo, sin limite de tiempo del webhook de Stripe."""
    try:
        import gc
        print("==> Generando noticias para " + email + "...")
        noticias = generar_noticias(user_data)
        gc.collect()
        print("==> Noticias generadas: " + str(len(noticias)))
        if not noticias:
            # Mandar email aunque no haya noticias - contenido de respaldo
            noticias = [
                {"contexto": "Tu ratio de compromisos financieros",
                 "titular": "La regla del 50%: por qué tus compromisos fijos no deberían superar la mitad de tus ingresos",
                 "desarrollo": "El Banco de España establece que los compromisos financieros fijos de un hogar no deberían superar el 50% de los ingresos netos mensuales. Por encima de ese umbral, la capacidad de absorber imprevistos se reduce drásticamente. Revisar periódicamente este ratio es una de las acciones más importantes para mantener la salud financiera a largo plazo.",
                 "fuente": "Banco de España", "fecha": "2025", "url": ""},
                {"contexto": "Construir tu colchón de emergencia",
                 "titular": "Tres meses de gastos: el colchón mínimo que separa un imprevisto de una crisis",
                 "desarrollo": "Las principales organizaciones financieras internacionales, incluida la OCDE, recomiendan mantener un fondo de emergencia equivalente a entre tres y seis meses de gastos. Este colchón permite afrontar situaciones imprevistas sin recurrir a deuda, que suele ser el inicio de una espiral financiera difícil de revertir.",
                 "fuente": "OCDE", "fecha": "2025", "url": ""},
                {"contexto": "Optimizar tu ahorro mensual",
                 "titular": "El ahorro automático funciona: por qué domiciliar el ahorro el día de cobro cambia los resultados",
                 "desarrollo": "Numerosos estudios de economía conductual demuestran que las personas que automatizan su ahorro el mismo día de cobro, antes de que el dinero llegue a la cuenta corriente, ahorran consistentemente más que quienes intentan ahorrar lo que sobra a final de mes. El principio es sencillo: págarte primero a ti mismo.",
                 "fuente": "Economía conductual - NBER", "fecha": "2025", "url": ""}
            ]

        ciudad = user_data.get("ciudad", "Espana")
        tipo = user_data.get("tipo_gasto", "otro")
        tipo_labels = {"hijo":"guarderia/hijo","vivienda":"vivienda","coche":"coche",
                      "formacion":"formacion","capricho":"capricho","otro":"gasto"}
        tl = tipo_labels.get(tipo, "gasto")

        noticias_html = ""
        for i, n in enumerate(noticias):
            ctx    = n.get("contexto", "")
            tit    = n.get("titular", "")
            dev    = n.get("desarrollo", "")
            fue    = n.get("fuente", "")
            fec    = n.get("fecha", "")
            url    = n.get("url", "")
            sep    = '<hr style="border:none;border-top:1px solid #E8E4DC;margin:24px 0">' if i > 0 else ""
            link   = ('<a href="' + url + '" style="display:inline-block;margin-top:10px;font-size:12px;color:#6B4700;font-weight:600;text-decoration:none">Leer artículo completo →</a>' if url else "")
            noticias_html += (
                sep +
                '<div style="margin-bottom:8px">'
                '<p style="font-size:13px;font-weight:700;color:#6B4700;margin:0 0 10px;line-height:1.5;background:#FBF0DC;padding:8px 12px;border-radius:6px">' + ctx + "</p>"
                '<h2 style="font-size:20px;color:#17140F;margin:0 0 12px;line-height:1.3;font-family:Georgia,serif">' + tit + "</h2>"
                '<p style="font-size:15px;color:#4A4540;line-height:1.75;margin:0 0 8px">' + dev + "</p>"
                + link +
                '<p style="font-size:11px;color:#9A9188;margin:12px 0 0">' + fue + " · " + fec + "</p>"
                "</div>"
            )

        html_body = (
            '<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body style="margin:0;padding:0;background:#F0EDE8">'
            '<div style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:620px;margin:0 auto;background:#F8F5F0">'
            # Header oscuro
            '<div style="background:#17140F;padding:28px 32px">'
            '<p style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,0.45);margin:0 0 6px;font-weight:600">Informe financiero</p>'
            '<h1 style="font-size:24px;color:#FFFFFF;margin:0 0 6px;line-height:1.2">Lo que está pasando<br>y te afecta, ' + nombre + '.</h1>'
            '<p style="font-size:13px;color:#FFFFFF;opacity:.6;margin:0">Seleccionado para tu perfil financiero en ' + ciudad + "</p>"
            "</div>"
            # Intro
            '<div style="padding:24px 32px 0">'
            '<p style="font-size:14px;color:#5C5750;line-height:1.65;margin:0 0 24px">'
            'Basándonos en lo que nos has contado sobre tu situación financiera y tu análisis de ' + tl + ', '
            'hemos seleccionado las noticias más relevantes para ti en este momento.'
            "</p>"
            '<hr style="border:none;border-top:2px solid #17140F;margin:0 0 28px">'
            "</div>"
            # Noticias
            '<div style="padding:0 32px">' + noticias_html + "</div>"
            # Footer
            '<div style="padding:24px 32px 32px;margin-top:16px;border-top:1px solid #D5CFC7">'
            '<p style="font-size:11px;color:#9A9188;margin:0;line-height:1.6">'
            'Información basada en los estándares del Banco de España, OCDE y BCE.<br>'
            '<a href="https://melopuedopermitir.com" style="color:#6B4700;text-decoration:none">melopuedopermitir.com</a>'
            "</p></div>"
            "</div></body></html>"
        )

        params2 = {
            "from": "melopuedopermitir.com <informe@melopuedopermitir.com>",
            "to": [email],
            "subject": "Noticias que te afectan, " + nombre + " — melopuedopermitir.com",
            "html": html_body,
        }
        r2 = resend.Emails.send(params2)
        print("==> Email 2 noticias enviado OK: " + str(r2))
    except Exception as e2:
        print("==> ERROR email 2 noticias: " + str(e2))

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'melopuedopermitir.com'})

@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400
        pdf_bytes = generate_pdf(data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name='informe-melopuedopermitir.pdf'
        )
    except Exception as e:
        print(f"ERROR generar_pdf: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/crear-sesion-pago', methods=['POST'])
def crear_sesion_pago():
    try:
        data = request.get_json()
        user_data = data.get('user_data', {})
        # Stripe limita cada campo de metadata a 500 chars
        # Mandamos los datos en campos separados para no perder nada
        import json as _json
        gd = user_data.get('gastos_desglose', {})
        metadata = {
            'nombre':      str(user_data.get('nombre', ''))[:100],
            'ciudad':      str(user_data.get('ciudad', ''))[:100],
            'pais':        str(user_data.get('pais', 'España'))[:50],
            'color':       str(user_data.get('color', 'verde'))[:20],
            'tipo_gasto':  str(user_data.get('tipo_gasto', 'otro'))[:20],
            'ratio':       str(user_data.get('ratio', 0)),
            'margen':      str(user_data.get('margen', 0)),
            'cmeses':      str(user_data.get('cmeses', 0)),
            'ns':          str(user_data.get('ns', 0)),
            'ingresos':    str(user_data.get('ingresos', 0)),
            'gasto_nuevo': str(user_data.get('gasto_nuevo', 0)),
            'gastos_mes':  str(user_data.get('gastos_mes', 0)),
            'punch':       str(user_data.get('punch', ''))[:490],
            'gastos_json': _json.dumps(gd)[:490],
        }
        email = user_data.get('email', '').strip()
        print(f"==> crear_sesion_pago: nombre={user_data.get('nombre','')}, email='{email}', color={user_data.get('color','')}, ingresos={user_data.get('ingresos',0)}")
        session_params = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'Informe financiero personalizado'},
                    'unit_amount': 499,
                },
                'quantity': 1,
            }],
            'mode': 'payment',
            'success_url': data.get('success_url', 'https://melopuedopermitir.com?pago=ok'),
            'cancel_url': data.get('cancel_url', 'https://melopuedopermitir.com?pago=cancelado'),
            'metadata': metadata,
        }
        # Solo mandamos email si es válido
        if email and '@' in email and '.' in email:
            session_params['customer_email'] = email
        session = stripe.checkout.Session.create(**session_params)
        return jsonify({'session_id': session.id, 'url': session.url})
    except Exception as e:
        print(f"ERROR crear_sesion_pago: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/webhook-stripe', methods=['POST'])
def webhook_stripe():
    payload    = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        print(f"==> Evento verificado: {event['type']}")
    except Exception as e:
        print(f"==> ERROR verificando webhook: {e}")
        return jsonify({'error': str(e)}), 400

    # Deduplicar en disco — sobrevive reinicios de Render
    session_tmp = event['data']['object'] if event['type'] == 'checkout.session.completed' else {}
    dedup_key = session_tmp.get('payment_intent', '') or event.get('id', '')
    if dedup_key:
        if _ya_procesado(dedup_key):
            print("==> Evento duplicado ignorado: " + dedup_key)
            return jsonify({'status': 'ok'})
        _marcar_procesado(dedup_key)

    if event['type'] == 'checkout.session.completed':
        session  = event['data']['object']
        metadata = session.get('metadata', {})
        email    = (session.get('customer_details', {}).get('email', '') or
                   session.get('customer_email', ''))
        nombre   = metadata.get('nombre', 'Usuario')

        print(f"==> Pago completado. Email: {email}, Nombre: {nombre}")

        # Reconstruir user_data desde los campos de metadata
        try:
            gastos_desglose = json.loads(metadata.get('gastos_json', '{}'))
        except:
            gastos_desglose = {}

        user_data = {
            'nombre':      metadata.get('nombre', nombre),
            'ciudad':      metadata.get('ciudad', ''),
            'pais':        metadata.get('pais', 'España'),
            'color':       metadata.get('color', 'verde'),
            'tipo_gasto':  metadata.get('tipo_gasto', 'otro'),
            'ratio':       float(metadata.get('ratio', 0)),
            'margen':      float(metadata.get('margen', 0)),
            'cmeses':      float(metadata.get('cmeses', 0)),
            'ns':          int(float(metadata.get('ns', 0))),
            'ingresos':    float(metadata.get('ingresos', 0)),
            'gasto_nuevo': float(metadata.get('gasto_nuevo', 0)),
            'gastos_mes':  float(metadata.get('gastos_mes', 0)),
            'punch':       metadata.get('punch', ''),
            'gastos_desglose': gastos_desglose,
            'noticias':    [],
        }

        if email:
            try:
                # EMAIL 1: PDF del informe (inmediato)
                user_data['noticias'] = []
                import gc; gc.collect()
                print(f"==> Generando PDF...")
                pdf_bytes = generate_pdf(user_data)
                pdf_b64   = base64.b64encode(pdf_bytes).decode('utf-8')
                print(f"==> PDF generado ({len(pdf_bytes)} bytes). Enviando email 1...")

                params1 = {
                    "from": "melopuedopermitir.com <informe@melopuedopermitir.com>",
                    "to":   [email],
                    "subject": f"Tu informe financiero está listo, {nombre}",
                    "html": f"""
                    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;background:#F8F5F0">
                        <div style="background:#17140F;color:white;padding:24px 28px;border-radius:8px;margin-bottom:24px">
                            <h1 style="font-size:26px;margin:0">Aquí está tu informe, {nombre}.</h1>
                        </div>
                        <p style="color:#4A4540;font-size:15px;line-height:1.7">
                            Tu análisis financiero personalizado está adjunto a este email.
                            Léelo con calma, guárdalo y compártelo con quien necesites para tomar la decisión.
                        </p>
                        <p style="color:#4A4540;font-size:15px;line-height:1.7;margin-top:12px">
                            En unos minutos recibirás un segundo email con las noticias más relevantes
                            para tu situación financiera concreta.
                        </p>
                        <p style="color:#8A847C;font-size:12px;margin-top:32px;border-top:1px solid #D5CFC7;padding-top:16px">
                            Información basada en los estándares del Banco de España, OCDE y BCE
                        </p>
                    </div>
                    """,
                    "attachments": [{"filename": "informe-melopuedopermitir.pdf", "content": pdf_b64}],
                }
                r1 = resend.Emails.send(params1)
                print(f"==> Email 1 enviado OK: {r1}")

                # EMAIL 2: en segundo plano, sin bloquear la respuesta del webhook a Stripe.
                # Ahora que no compite por el limite de 30s de Stripe, generar_noticias
                # puede tardar lo que necesite (hasta un par de minutos) y reintentar.
                threading.Thread(
                    target=_enviar_email_noticias,
                    args=(email, nombre, user_data.copy()),
                    daemon=True
                ).start()
                print("==> Email 2 (noticias) lanzado en segundo plano")

            except Exception as e:
                print(f"==> ERROR: {e}")
                traceback.print_exc()
        else:
            print(f"==> ERROR: sin email del cliente")

    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
