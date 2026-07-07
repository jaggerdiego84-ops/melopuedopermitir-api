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
    """Genera noticias personalizadas usando Claude."""
    try:
        ciudad   = user_data.get('ciudad', 'España')
        tipo     = user_data.get('tipo_gasto', 'otro')
        ingresos = user_data.get('ingresos', 0)
        ratio    = user_data.get('ratio', 0)
        color    = user_data.get('color', 'verde')
 
        tipo_labels = {'hijo':'guardería o tener un hijo','vivienda':'vivienda o alquiler',
                      'coche':'coche','formacion':'formación','capricho':'capricho','otro':'gasto personal'}
        tl = tipo_labels.get(tipo, 'gasto personal')
 
        prompt = (
            'Usuario en '+ciudad+', analiza '+tl+', ingresos '+str(round(ingresos))+' euros, ratio '+str(round(ratio))+'%. '
            'Dame 3 noticias financieras españolas recientes relevantes para esta persona. '
            'Solo JSON, sin texto extra: '
            '[{"contexto":"por que le afecta","titular":"titular gancho directo","desarrollo":"3-4 frases con datos y cifras concretas relevantes para esta persona","fuente":"medio","fecha":"2025"}]'
        )
 
        client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
 
        text = response.content[0].text
        start = text.find('['); end = text.rfind(']')
        if start >= 0 and end >= 0:
            noticias = json.loads(text[start:end+1])
            return noticias[:3]
    except Exception as e:
        print(f"==> Error generando noticias: {e}")
    return []
 
 
 
app = Flask(__name__)
CORS(app)
 
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
                    "from": "informe@melopuedopermitir.com",
                    "to":   [email],
                    "subject": f"Tu informe financiero está listo, {nombre}",
                    "html": f"""
                    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;background:#F8F5F0">
                        <div style="background:#17140F;color:white;padding:24px 28px;border-radius:8px;margin-bottom:24px">
                            <p style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;opacity:.5;margin-bottom:4px">MELOPUEDOPERMITIR.COM</p>
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
                            melopuedopermitir.com · Banco de España · OCDE · BCE
                        </p>
                    </div>
                    """,
                    "attachments": [{"filename": "informe-melopuedopermitir.pdf", "content": pdf_b64}],
                }
                r1 = resend.Emails.send(params1)
                print(f"==> Email 1 enviado OK: {r1}")
 
                # EMAIL 2: Noticias personalizadas en HTML (en hilo separado)
                def enviar_noticias(email, nombre, user_data):
                    try:
                        import gc as _gc
                        print(f"==> Generando noticias para {email}...")
                        noticias = generar_noticias(user_data)
                        _gc.collect()
                        if not noticias:
                            print("==> Sin noticias, no se envía email 2")
                            return
 
                        ciudad = user_data.get('ciudad', 'España')
                        tipo_labels = {'hijo':'guardería/hijo','vivienda':'vivienda','coche':'coche',
                                      'formacion':'formación','capricho':'capricho','otro':'gasto'}
                        tl = tipo_labels.get(user_data.get('tipo_gasto','otro'), 'gasto')
 
                        noticias_html = ''
                        for n in noticias:
                            noticias_html += f"""
                            <div style="border-left:3px solid #6B4700;padding:0 0 0 16px;margin-bottom:28px">
                                <p style="font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6B4700;margin:0 0 6px">{n.get('contexto','').upper()}</p>
                                <h2 style="font-size:17px;color:#17140F;margin:0 0 10px;line-height:1.35">{n.get('titular','')}</h2>
                                <p style="font-size:14px;color:#4A4540;line-height:1.7;margin:0 0 8px">{n.get('desarrollo','')}</p>
                                <p style="font-size:11px;color:#9A9188;margin:0">{n.get('fuente','')} · {n.get('fecha','')}</p>
                            </div>
                            """
 
                        params2 = {{
                            "from": "informe@melopuedopermitir.com",
                            "to":   [email],
                            "subject": f"Noticias relacionadas con tu análisis, {{nombre}}",
                            "html": f"""
                            <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:40px 20px;background:#F8F5F0">
                                <div style="background:#17140F;color:white;padding:24px 28px;border-radius:8px;margin-bottom:28px">
                                    <p style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;opacity:.5;margin-bottom:4px">MELOPUEDOPERMITIR.COM</p>
                                    <h1 style="font-size:22px;margin:0">Lo que está pasando y te afecta, {{nombre}}.</h1>
                                    <p style="font-size:13px;opacity:.7;margin:8px 0 0">Seleccionado para tu perfil financiero en {ciudad}</p>
                                </div>
                                {{noticias_html}}
                                <p style="color:#8A847C;font-size:12px;margin-top:32px;border-top:1px solid #D5CFC7;padding-top:16px">
                                    melopuedopermitir.com · Banco de España · OCDE · BCE
                                </p>
                            </div>
                            """
                        }}
                        r2 = resend.Emails.send(params2)
                        print(f"==> Email 2 noticias enviado OK: {{r2}}")
                    except Exception as e2:
                        print(f"==> ERROR email 2 noticias: {{e2}}")
 
                import threading as _th
                _th.Thread(target=enviar_noticias, args=(email, nombre, user_data.copy()), daemon=True).start()
 
            except Exception as e:
                print(f"==> ERROR: {e}")
                traceback.print_exc()
        else:
            print(f"==> ERROR: sin email del cliente")
 
    return jsonify({'status': 'ok'})
 
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
