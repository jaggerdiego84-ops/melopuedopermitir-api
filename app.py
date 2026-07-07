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
        metadata = {
            'nombre':     str(user_data.get('nombre', ''))[:100],
            'ciudad':     str(user_data.get('ciudad', ''))[:100],
            'color':      str(user_data.get('color', 'verde')),
            'tipo_gasto': str(user_data.get('tipo_gasto', 'otro')),
            'datos_json': json.dumps(user_data)[:4000],
        }
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'Informe financiero personalizado'},
                    'unit_amount': 499,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=data.get('success_url', 'https://melopuedopermitir.com?pago=ok'),
            cancel_url=data.get('cancel_url', 'https://melopuedopermitir.com?pago=cancelado'),
            customer_email=user_data.get('email', ''),
            metadata=metadata,
        )
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
        email    = (session.get('customer_email') or
                   session.get('customer_details', {}).get('email', ''))
        nombre   = metadata.get('nombre', 'Usuario')
 
        print(f"==> Pago completado. Email: {email}, Nombre: {nombre}")
 
        datos_json = metadata.get('datos_json', '{}')
        try:
            user_data = json.loads(datos_json)
        except:
            user_data = {}
 
        if not user_data.get('nombre'):
            user_data['nombre'] = nombre
        if not user_data.get('color'):
            user_data['color'] = 'verde'
 
        if email:
            try:
                print(f"==> Generando PDF...")
                pdf_bytes = generate_pdf(user_data)
                pdf_b64   = base64.b64encode(pdf_bytes).decode('utf-8')
 
                print(f"==> PDF generado ({len(pdf_bytes)} bytes). Enviando a {email}...")
 
                params = {
                    "from": "informe@melopuedopermitir.com",
                    "to":   [email],
                    "subject": f"Tu informe financiero está listo, {nombre}",
                    "html": f"""
                    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:40px 20px">
                        <h1 style="font-size:28px;color:#17140F;margin-bottom:8px">Aquí está tu informe, {nombre}.</h1>
                        <p style="color:#4A4540;font-size:16px;line-height:1.6">
                            Tu análisis financiero personalizado está adjunto a este email.
                            Léelo con calma, guárdalo y compártelo con quien necesites para tomar la decisión.
                        </p>
                        <p style="color:#8A847C;font-size:13px;margin-top:32px">
                            melopuedopermitir.com · Banco de España · OCDE · BCE
                        </p>
                    </div>
                    """,
                    "attachments": [{"filename": "informe-melopuedopermitir.pdf", "content": pdf_b64}],
                }
                response = resend.Emails.send(params)
                print(f"==> Email enviado OK: {response}")
 
            except Exception as e:
                print(f"==> ERROR: {e}")
                traceback.print_exc()
        else:
            print(f"==> ERROR: sin email del cliente")
 
    return jsonify({'status': 'ok'})
 
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
