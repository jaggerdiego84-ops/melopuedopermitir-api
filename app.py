"""
API — melopuedopermitir.com
Endpoints:
  GET  /health          → health check para Render
  POST /generar-pdf     → genera PDF con datos del usuario (test)
  POST /webhook-stripe  → recibe pago confirmado y entrega PDF por email
"""
import os, json, base64
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import stripe
import resend
import io
from pdf_generator import generate_pdf

app = Flask(__name__)
CORS(app)

# Variables de entorno (se configuran en Render)
stripe.api_key          = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET   = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
RESEND_API_KEY          = os.environ.get('RESEND_API_KEY', '')
resend.api_key          = RESEND_API_KEY

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'melopuedopermitir.com'})

@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    """
    Genera el PDF con los datos del usuario.
    Usado para testing y también llamado internamente tras el pago.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        pdf_bytes = generate_pdf(data)

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"informe-melopuedopermitir-{data.get('nombre','usuario').lower().replace(' ','-')}.pdf"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/crear-sesion-pago', methods=['POST'])
def crear_sesion_pago():
    """
    Crea una sesión de pago en Stripe con los datos del usuario en metadata.
    El frontend llama a este endpoint cuando el usuario pulsa "Pagar 4,99€".
    """
    try:
        data = request.get_json()
        user_data = data.get('user_data', {})

        # Guardamos los datos del usuario en metadata de Stripe
        # (máx 500 chars por campo, así que comprimimos)
        metadata = {
            'nombre':     user_data.get('nombre', '')[:100],
            'ciudad':     user_data.get('ciudad', '')[:100],
            'pais':       user_data.get('pais', '')[:50],
            'color':      user_data.get('color', 'verde'),
            'tipo_gasto': user_data.get('tipo_gasto', 'otro'),
            # Los datos completos los mandamos como JSON comprimido
            'datos_json': json.dumps(user_data)[:4000],
        }

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Informe financiero personalizado',
                        'description': 'Tu análisis completo en PDF — melopuedopermitir.com',
                    },
                    'unit_amount': 499,  # 4,99€ en céntimos
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
        return jsonify({'error': str(e)}), 500

@app.route('/webhook-stripe', methods=['POST'])
def webhook_stripe():
    """
    Stripe llama aquí cuando un pago se completa.
    Generamos el PDF y lo enviamos por email al usuario.
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Recuperar datos del usuario desde metadata
        metadata = session.get('metadata', {})
        datos_json = metadata.get('datos_json', '{}')

        try:
            user_data = json.loads(datos_json)
        except:
            user_data = {}

        email = session.get('customer_email') or user_data.get('email', '')
        nombre = metadata.get('nombre', user_data.get('nombre', 'Usuario'))

        if email:
            try:
                # Generar PDF
                pdf_bytes = generate_pdf(user_data)
                pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                filename = f"informe-{nombre.lower().replace(' ', '-')}.pdf"

                # Enviar email con Resend
                resend.Emails.send({
                    'from': 'informe@melopuedopermitir.com',
                    'to': email,
                    'subject': f'Tu informe financiero está listo, {nombre}',
                    'html': f'''
                    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:40px 20px">
                        <h1 style="font-size:28px;color:#17140F;margin-bottom:8px">Aquí está tu informe, {nombre}.</h1>
                        <p style="color:#4A4540;font-size:16px;line-height:1.6">
                            Tu análisis financiero personalizado está adjunto a este email.
                            Está pensado para que lo leas con calma, lo guardes y lo compartas
                            con quien necesites para tomar la decisión.
                        </p>
                        <p style="color:#8A847C;font-size:13px;margin-top:32px">
                            melopuedopermitir.com · Metodología: Banco de España · OCDE · BCE
                        </p>
                    </div>
                    ''',
                    'attachments': [{
                        'filename': filename,
                        'content': pdf_b64,
                    }],
                })
            except Exception as e:
                print(f"Error enviando email: {e}")

    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
