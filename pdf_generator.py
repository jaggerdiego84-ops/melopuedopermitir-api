"""
Generador de PDF personalizado — melopuedopermitir.com
Recibe los datos del usuario y genera el informe completo
"""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os
 
def register_fonts():
    font_paths = [
        '/usr/share/fonts/truetype/google-fonts/',
        '/usr/local/share/fonts/',
        os.path.join(os.path.dirname(__file__), 'fonts/'),
    ]
    for base in font_paths:
        try:
            pdfmetrics.registerFont(TTFont('Pp',   base+'Poppins-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('Pp-B', base+'Poppins-Bold.ttf'))
            pdfmetrics.registerFont(TTFont('Pp-M', base+'Poppins-Medium.ttf'))
            pdfmetrics.registerFont(TTFont('Pp-L', base+'Poppins-Light.ttf'))
            return True
        except:
            continue
    # Fallback a Helvetica si no hay Poppins
    return False
 
FONTS_OK = register_fonts()
F  = 'Pp'   if FONTS_OK else 'Helvetica'
FB = 'Pp-B' if FONTS_OK else 'Helvetica-Bold'
FM = 'Pp-M' if FONTS_OK else 'Helvetica'
FL = 'Pp-L' if FONTS_OK else 'Helvetica'
 
W, H = A4
MX = 20*mm; MY_BOT = 22*mm; CONTENT_W = W - 2*MX
SP_XS=3*mm; SP_SM=5*mm; SP_MD=8*mm; SP_LG=12*mm
 
BG=HexColor('#F8F5F0'); BG3=HexColor('#DDD8CE')
INK=HexColor('#17140F'); INK2=HexColor('#4A4540')
INK3=HexColor('#8A847C'); INK4=HexColor('#C0BAB2')
BORDER=HexColor('#D5CFC7'); WHITE=HexColor('#FFFFFF')
VERDE=HexColor('#1E5C1E'); VERDE_L=HexColor('#E8F3E8')
AMAR=HexColor('#6B4700'); AMAR_L=HexColor('#FBF0DC')
ROJO=HexColor('#7A1515'); ROJO_L=HexColor('#FAEAEA')
DARK=HexColor('#0D0D0D')
EUR = u'\u20ac'
 
def wrap(c, text, font, size, max_w):
    c.setFont(font, size)
    words = str(text).split()
    lines, cur = [], ''
    for word in words:
        t = (cur+' '+word).strip()
        if c.stringWidth(t, font, size) < max_w: cur = t
        else:
            if cur: lines.append(cur)
            cur = word
    if cur: lines.append(cur)
    return lines
 
def hr(c, y, x1=None, x2=None, color=None, lw=0.3):
    c.setStrokeColor(color or BORDER); c.setLineWidth(lw)
    c.line(x1 or 14*mm, y, x2 or (W-MX), y)
 
def footer_line(c, n, total):
    c.setFillColor(INK4); c.setFont(F, 6)
    c.drawString(14*mm, 11*mm, u'melopuedopermitir.com  \u00b7  Banco de Espa\u00f1a \u00b7 OCDE \u00b7 BCE  \u00b7  Informe personal y confidencial')
    c.drawRightString(W-MX, 11*mm, str(n)+' / '+str(total))
    c.setStrokeColor(BORDER); c.setLineWidth(0.2)
    c.line(14*mm, 17*mm, W-MX, 17*mm)
 
def circle_num(c, cx, cy, r, num, SC):
    c.setFillColor(SC); c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont(FB, r*1.3)
    c.drawCentredString(cx, cy - r*0.35, str(num))
 
def generar_distribucion(ingresos, gastos, tl, margen, ratio, cmeses, ns, gastos_mes, loc):
    ocio=gastos.get('ocio',0); ahorro_act=gastos.get('ahorro',0)
    transporte=gastos.get('transporte',0); deudas=gastos.get('deudas',0)
    movimientos=[]
    pct_ocio   = ocio/ingresos*100 if ingresos>0 else 0
    pct_ahorro = ahorro_act/ingresos*100 if ingresos>0 else 0
    pct_trans  = transporte/ingresos*100 if ingresos>0 else 0
 
    if pct_ocio>10:
        recorte=round(ocio*0.22)
        movimientos.append({'titulo':u'Reducir el ocio un 22% sin sentirlo','ahorro':recorte,
            'motivo':u'El ocio representa el '+str(round(pct_ocio))+u'% de tus ingresos, por encima del 10% recomendado. Un recorte del 22% equivale a '+str(recorte)+u' '+EUR+u'/mes y casi nunca se nota: revisar suscripciones activas, cocinar en casa 2 veces m\u00e1s por semana. En 12 meses son '+str(recorte*12)+u' '+EUR+u' que pasan al colch\u00f3n.'})
 
    ahorro_ideal=round(ingresos*0.15)
    if pct_ahorro<12 and ahorro_ideal>ahorro_act:
        extra=ahorro_ideal-ahorro_act
        meses_ns=round((ns-cmeses*gastos_mes)/ahorro_ideal) if ahorro_ideal>0 and cmeses<3 else 0
        movimientos.append({'titulo':u'Subir el ahorro sistem\u00e1tico al 15%','ahorro':-extra,
            'motivo':u'Ahora destinas el '+str(round(pct_ahorro))+u'% al ahorro, por debajo del 15% m\u00ednimo recomendado. Subir a '+str(ahorro_ideal)+u' '+EUR+u'/mes no se nota si se automatiza el d\u00eda de cobro. En '+str(meses_ns)+u' meses llegar\u00edas a 3 meses de colch\u00f3n cubiertos.'})
 
    if pct_trans>7:
        ahorro_t=round(transporte*0.15)
        movimientos.append({'titulo':u'Optimizar el coste de transporte un 15%','ahorro':ahorro_t,
            'motivo':u'El transporte supone el '+str(round(pct_trans))+u'% de tus ingresos. Revisar el seguro del coche cada a\u00f1o (ahorro medio 18%), usar Geoportal Carburantes en '+loc+u' (8-12 '+EUR+u'/mes) y valorar el transporte p\u00fablico para trayectos cortos puede liberar '+str(ahorro_t)+u' '+EUR+u'/mes.'})
 
    if deudas>0 and ratio>48:
        movimientos.append({'titulo':u'Acelerar el fin de las deudas','ahorro':0,
            'motivo':u'Con '+str(round(deudas))+u' '+EUR+u'/mes en cuotas y ratio al '+str(round(ratio))+u'%, cada deuda que terminas mejora el ratio directamente. Pregunta a tu banco por amortizaci\u00f3n anticipada: incluso 50-100 '+EUR+u'/mes extra adelanta el fin meses antes.'})
 
    if not movimientos:
        movimientos.append({'titulo':u'Subir el colch\u00f3n al nivel \u00f3ptimo de 6 meses','ahorro':round(margen*0.4),
            'motivo':u'Tu distribuci\u00f3n es sana. Destinar el 40% del margen libre ('+str(round(margen*0.4))+u' '+EUR+u'/mes) al colch\u00f3n hasta llegar a 6 meses cubiertos cambia completamente tu exposici\u00f3n al riesgo.'})
 
    return movimientos[:3]
 
def generate_pdf(data):
    """Genera el PDF y devuelve los bytes."""
    buf = io.BytesIO()
 
    color=data.get('color','verde'); nombre=data.get('nombre','Usuario')
    ciudad=data.get('ciudad',''); pais=data.get('pais',u'Espa\u00f1a')
    tipo=data.get('tipo_gasto','otro')
    ratio=float(data.get('ratio',0)); margen=float(data.get('margen',0))
    cmeses=float(data.get('cmeses',0)); ns=int(data.get('ns',0))
    ingresos=float(data.get('ingresos',1)); gasto_nuevo=float(data.get('gasto_nuevo',0))
    gastos_mes=float(data.get('gastos_mes', ns/3 if ns>0 else 1))
    punch=data.get('punch',''); gastos_data=data.get('gastos_desglose',{})
    noticias=data.get('noticias',[])
 
    SC = VERDE if color=='verde' else (AMAR if color=='amarillo' else ROJO)
    SL = VERDE_L if color=='verde' else (AMAR_L if color=='amarillo' else ROJO_L)
 
    tipo_labels={'hijo':u'Guarden\u00eda/hijo','vivienda':'Vivienda','coche':'Coche',
                 'formacion':u'Formaci\u00f3n','capricho':'Capricho','otro':'Gasto analizado'}
    tl = tipo_labels.get(tipo,'Gasto analizado')
    loc = ciudad if ciudad else pais
    veredictos={
        'verde':  u'S\u00ed, puedes permit\u00edrtelo.',
        'amarillo':'Puedes, pero con los ojos abiertos.',
        'rojo':   u'No lo har\u00eda todav\u00eda.'
    }
    emoji_char = u'\u2713' if color=='verde' else ('!' if color=='amarillo' else u'\u2717')
 
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(u"Tu informe financiero \u2014 melopuedopermitir.com")
 
    # ── PÁG 1 ────────────────────────────────────────
    c.setFillColor(BG); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,0,7*mm,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,H-1*mm,W,1*mm,fill=1,stroke=0)
    c.setFillColor(INK3); c.setFont(F,7)
    c.drawRightString(W-MX, H-8*mm, 'melopuedopermitir.com')
 
    c.setFillColor(INK); c.setFont(FB,42)
    c.drawString(14*mm, H-38*mm, nombre)
    sub_parts=[]
    if ciudad: sub_parts.append(ciudad)
    if pais and pais not in ('Espana',u'Espa\u00f1a'): sub_parts.append(pais)
    sub_parts.append(tl)
    c.setFillColor(INK3); c.setFont(F,10)
    c.drawString(14*mm, H-47*mm, u'  \u00b7  '.join(sub_parts))
    c.setStrokeColor(BORDER); c.setLineWidth(0.5)
    c.line(14*mm, H-52*mm, W-MX, H-52*mm)
 
    # Veredicto
    VER_BOT=H-76*mm; VER_H=21*mm
    c.setFillColor(SC); c.roundRect(14*mm,VER_BOT,CONTENT_W+6*mm,VER_H,3*mm,fill=1,stroke=0)
    ICON_R=7*mm; ICON_CX=14*mm+SP_MD+ICON_R; ICON_CY=VER_BOT+VER_H/2
    c.setFillColor(WHITE); c.circle(ICON_CX,ICON_CY,ICON_R,fill=1,stroke=0)
    c.setFillColor(SC); c.setFont(FB,ICON_R*1.5)
    c.drawCentredString(ICON_CX,ICON_CY-ICON_R*0.38,emoji_char)
    TEXT_X=ICON_CX+ICON_R+SP_SM
    c.setFillColor(WHITE); c.setFont(FB,14)
    c.drawString(TEXT_X,VER_BOT+VER_H-6*mm,veredictos[color])
    punch_lns=wrap(c,punch,F,8.5,W-TEXT_X-MX-4*mm)
    c.setFillColor(WHITE); c.setFont(F,8.5)
    for i,ln in enumerate(punch_lns[:1]):
        c.drawString(TEXT_X,VER_BOT+VER_H-14.5*mm,ln)
 
    # Indicadores
    IND_BOT=H-104*mm; IND_H=24*mm; IND_W=(CONTENT_W+6*mm-2*SP_XS)/3
    inds=[
        ('COMPROMISOS\nSOBRE INGRESOS',str(round(ratio))+'%',u'L\u00edmite sano: 50%',ratio>50),
        (u'MARGEN LIBRE\nREAL',('+' if margen>=0 else '')+str(round(margen))+u' '+EUR,'Lo que sobra al mes',margen<200),
        (u'COLCH\u00d3N\nDISPONIBLE',str(round(cmeses,1))+' meses',u'M\u00ednimo: 3 meses',cmeses<3),
    ]
    for i,(lbl,val,sublbl,alerta) in enumerate(inds):
        ix=14*mm+i*(IND_W+SP_XS)
        c.setFillColor(WHITE); c.setStrokeColor(SC if alerta else BORDER)
        c.setLineWidth(1.5 if alerta else 0.4)
        c.roundRect(ix,IND_BOT,IND_W,IND_H,3*mm,fill=1,stroke=1)
        c.setFillColor(SC if alerta else INK); c.setFont(FB,17)
        c.drawCentredString(ix+IND_W/2,IND_BOT+15*mm,val)
        c.setFillColor(INK3); c.setFont(F,6)
        for j,ll in enumerate(lbl.split('\n')):
            c.drawCentredString(ix+IND_W/2,IND_BOT+10*mm-j*7,ll)
        c.setFillColor(INK4); c.setFont(FL,6)
        c.drawCentredString(ix+IND_W/2,IND_BOT+2.5*mm,sublbl)
 
    # NS
    NS_BOT=H-128*mm; NS_H=20*mm
    c.setFillColor(INK); c.roundRect(14*mm,NS_BOT,CONTENT_W+6*mm,NS_H,3*mm,fill=1,stroke=0)
    c.setFillColor(HexColor('#666666')); c.setFont(FM,6.5)
    c.drawString(14*mm+SP_MD,NS_BOT+NS_H-5.5*mm,u'TU N\u00daMERO DE SEGURIDAD')
    c.setFillColor(WHITE); c.setFont(FB,22)
    c.drawString(14*mm+SP_MD,NS_BOT+NS_H-14*mm,str(ns)+u' '+EUR)
    ns_txt=(u'3 meses de gastos ('+str(round(gastos_mes))+u' '+EUR+u'/mes \u00d7 3). '
            +(u'Tienes '+str(round(cmeses,1))+u' meses cubiertos \u2014 zona segura \u2713' if cmeses>=3
              else u'Tienes '+str(round(cmeses,1))+u' meses \u2014 objetivo: llegar a 3 meses m\u00ednimo.'))
    ns_lns=wrap(c,ns_txt,F,7,CONTENT_W-52*mm)
    c.setFillColor(HexColor('#999999')); c.setFont(F,7)
    for i,ln in enumerate(ns_lns[:2]):
        c.drawString(14*mm+SP_MD,NS_BOT+NS_H-19*mm+i*(-8.5),ln)
    BX=W-MX-46*mm; BW=44*mm; BBY=NS_BOT+NS_H-13*mm
    c.setFillColor(HexColor('#2A2A2A')); c.roundRect(BX,BBY,BW,4*mm,2*mm,fill=1,stroke=0)
    pct_c=min(cmeses/6.0,1.0)
    bc=VERDE if cmeses>=3 else (AMAR if cmeses>=1 else ROJO)
    c.setFillColor(bc); c.roundRect(BX,BBY,max(BW*pct_c,2.5*mm),4*mm,2*mm,fill=1,stroke=0)
    c.setFillColor(HexColor('#555555')); c.setFont(F,5.5)
    c.drawString(BX,BBY-4*mm,'0'); c.drawCentredString(BX+BW/2,BBY-4*mm,'3 meses')
    c.drawRightString(BX+BW,BBY-4*mm,'6+')
 
    # Barras
    TITULO_Y=NS_BOT-SP_LG; BARRA_Y=TITULO_Y-SP_MD
    c.setFillColor(INK3); c.setFont(FM,7)
    c.drawString(14*mm,TITULO_Y,u'AS\u00cd SE REPARTE TU DINERO CADA MES')
 
    cats=[
        ('Vivienda',    gastos_data.get('vivienda',0),   HexColor('#4A7FA5')),
        ('Transporte',  gastos_data.get('transporte',0), HexColor('#5A9A7A')),
        ('Vida diaria', gastos_data.get('vida',0),        HexColor('#8A6FA0')),
        ('Ocio',        gastos_data.get('ocio',0),        HexColor('#C8A040')),
        ('Deudas',      gastos_data.get('deudas',0),      HexColor('#C06050')),
        ('Ahorro',      gastos_data.get('ahorro',0),      HexColor('#50A060')),
        (tl+u' (nuevo)',gasto_nuevo,                      SC),
    ]
    cats=[(n,v,col) for n,v,col in cats if v>0]
    BAR_X=14*mm+28*mm; BAR_AREA=CONTENT_W+6*mm-28*mm-30*mm
    BAR_H=7*mm; BAR_GAP=4*mm; by=BARRA_Y
 
    for cat_name,val,col in cats:
        if by<MY_BOT+6*mm: break
        pct_b=round(val/ingresos*100) if ingresos>0 else 0
        bw_b=(val/ingresos)*BAR_AREA if ingresos>0 else 0
        c.setFillColor(INK2); c.setFont(F,7.5)
        c.drawString(14*mm,by+1.8*mm,cat_name)
        c.setFillColor(BG3); c.roundRect(BAR_X,by,BAR_AREA,BAR_H,3.5*mm,fill=1,stroke=0)
        bw_real=max(bw_b,4*mm) if bw_b>1 else 0
        if bw_real>0:
            c.setFillColor(col); c.roundRect(BAR_X,by,bw_real,BAR_H,3.5*mm,fill=1,stroke=0)
        label=str(round(val))+u' '+EUR+u' - '+str(pct_b)+'%'
        c.setFillColor(INK2); c.setFont(FM,7.5)
        c.drawString(BAR_X+BAR_AREA+3*mm,by+1.8*mm,label)
        by-=(BAR_H+BAR_GAP)
 
    by-=2*mm
    c.setStrokeColor(BORDER); c.setLineWidth(0.35)
    c.line(14*mm,by+3*mm,W-MX,by+3*mm)
    total_g=sum(v for _,v,_ in cats); mrg=ingresos-total_g
    c.setFillColor(INK); c.setFont(FB,8)
    c.drawString(14*mm,by-1*mm,u'Ingresos totales: '+str(round(ingresos))+u' '+EUR)
    c.setFillColor(VERDE if mrg>=0 else ROJO)
    c.drawRightString(W-MX,by-1*mm,(u'Margen libre: +' if mrg>=0 else u'D\u00e9ficit: ')+str(round(abs(mrg)))+u' '+EUR+u'/mes')
 
    footer_line(c,1,4); c.showPage()
 
    # ── PÁG 2 ANÁLISIS ───────────────────────────────
    c.setFillColor(BG); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,0,7*mm,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,H-1*mm,W,1*mm,fill=1,stroke=0)
    c.setFillColor(INK3); c.setFont(FM,7)
    c.drawString(14*mm,H-10*mm,u'LO QUE NOS DICEN TUS N\u00daMEROS')
    c.drawRightString(W-MX,H-10*mm,nombre+u' \u00b7 '+loc)
    c.setFillColor(INK); c.setFont(FB,22)
    c.drawString(14*mm,H-26*mm,u'Tu situaci\u00f3n financiera real')
    c.setFillColor(INK3); c.setFont(F,9.5)
    c.drawString(14*mm,H-35*mm,u'An\u00e1lisis personalizado con tus datos concretos')
    c.setStrokeColor(BORDER); c.setLineWidth(0.4)
    c.line(14*mm,H-40*mm,W-MX,H-40*mm)
 
    bloques_map={
        'amarillo':[
            (u'El ratio del '+str(round(ratio))+u'% ha cruzado el l\u00edmite recomendado',
             u'Con el '+str(round(ratio))+u'% de tus ingresos comprometidos, has superado el umbral del 50% del Banco de Espa\u00f1a. No significa que no puedas pagar \u2014 significa que no tienes red de seguridad. Cualquier subida del alquiler, aver\u00eda o mes de ingresos bajos puede desequilibrar todo. En '+loc+u', el coste de la vida ha subido un 8-12% en los \u00faltimos 2 a\u00f1os.'),
            (u'Con '+str(round(margen))+u' '+EUR+u'/mes libres, el margen es fr\u00e1gil',
             str(round(margen))+u' '+EUR+u' al mes es suficiente para vivir, pero no para absorber imprevistos. Un mes con gastos extra puede dejarte en cero. El problema no es un mes malo \u2014 es que dos meses malos seguidos te obligan a recurrir al colch\u00f3n o a deuda.'),
            (u'El colch\u00f3n de '+str(round(cmeses,1))+u' meses: la prioridad n\u00famero uno',
             u'Con '+str(round(cmeses,1))+u' meses cubiertos est\u00e1s por debajo del m\u00ednimo de 3 meses. Si ma\u00f1ana perdieras el trabajo, en '+str(round(cmeses,1))+u' meses estar\u00edas bajo presi\u00f3n real. El tiempo medio para encontrar empleo equivalente en Espa\u00f1a es 3-5 meses seg\u00fan el SEPE.'),
            (u'Lo que este gasto ha cambiado en tu situaci\u00f3n',
             u'Antes de '+tl.lower()+u', tu ratio era del '+str(round(ratio-(gasto_nuevo/ingresos*100 if ingresos>0 else 0)))+u'%. Con '+tl.lower()+u' sube al '+str(round(ratio))+u'%. El margen libre pasa de '+str(round(margen+gasto_nuevo))+u' '+EUR+u' a '+str(round(margen))+u' '+EUR+u'/mes.'),
        ],
        'verde':[
            (u'El ratio del '+str(round(ratio))+u'% est\u00e1 bajo control',
             u'Con el '+str(round(ratio))+u'% tienes '+str(50-round(ratio))+u' puntos de margen antes de la zona de alerta. El objetivo ideal es mantenerse por debajo del 45% para tener comodidad real ante cualquier cambio.'),
            (u'Te sobran '+str(round(margen))+u' '+EUR+u'/mes \u2014 eso es poder de maniobra',
             str(round(margen))+u' '+EUR+u' libres al mes significa que puedes absorber imprevistos y acelerar el ahorro. En '+loc+u', un imprevisto dom\u00e9stico habitual oscila entre 300 y 800 '+EUR+u'.'),
            (u'El colch\u00f3n de '+str(round(cmeses,1))+u' meses te da tiempo para reaccionar',
             u'Con '+str(round(cmeses,1))+u' meses cubiertos tienes ese tiempo antes de la presi\u00f3n real. '+('Zona segura. El objetivo ideal es llegar a 6 meses.' if cmeses>=3 else u'Por debajo del m\u00ednimo \u2014 punto importante a mejorar.')),
            (u'Lo que este gasto cambia',
             u'Tu ratio sube de '+str(round(ratio-(gasto_nuevo/ingresos*100 if ingresos>0 else 0)))+u'% a '+str(round(ratio))+u'%. Tu margen pasa de '+str(round(margen+gasto_nuevo))+u' '+EUR+u' a '+str(round(margen))+u' '+EUR+u'/mes.'),
        ],
        'rojo':[
            (u'El ratio del '+str(round(ratio))+u'% supera el l\u00edmite con claridad',
             u'Con el '+str(round(ratio))+u'% comprometido, no hay red de seguridad. Una aver\u00eda, una factura mayor, un mes de ingresos bajos puede convertirse en deuda. La deuda sube el ratio a\u00fan m\u00e1s.'),
            (u'El margen de '+str(round(margen))+u' '+EUR+u'/mes no es suficiente',
             (u'No queda margen real.' if margen<100 else str(round(margen))+u' '+EUR+u'/mes no es suficiente hoy. ')+u'Los imprevistos habituales oscilan entre 200 y 1.000 '+EUR+u'.'),
            (u'El efecto domin\u00f3: por qu\u00e9 el riesgo es mayor',
             u'La secuencia: imprevisto \u2192 sin margen \u2192 deuda \u2192 cuota nueva \u2192 ratio sube \u2192 siguiente imprevisto m\u00e1s dif\u00edcil. Romper ese ciclo antes es mucho m\u00e1s f\u00e1cil.'),
            (u'Cu\u00e1ndo cambia este an\u00e1lisis',
             u'Cambia si: ingresos suben a '+str(round(ingresos*1.15))+u' '+EUR+u'/mes, termina alg\u00fan pr\u00e9stamo que libere '+str(round(gasto_nuevo*0.4))+u' '+EUR+u'/mes, o reduces gastos en '+str(round(gasto_nuevo*0.35))+u' '+EUR+u'/mes.'),
        ],
    }
    bloques=bloques_map.get(color,bloques_map['verde'])
    SEP=6.5*mm; y=H-48*mm
    for i,(tit,desc) in enumerate(bloques):
        if y<MY_BOT: break
        if i>0:
            y-=SEP; c.setStrokeColor(BORDER); c.setLineWidth(0.3)
            c.line(14*mm,y,W-MX,y); y-=SEP
            if y<MY_BOT: break
        circle_num(c,14*mm+7*mm,y-4*mm,7*mm,i+1,SC)
        c.setFillColor(INK); c.setFont(FB,10.5)
        c.drawString(14*mm+18*mm,y,tit)
        y-=3.5*mm
        lns=wrap(c,desc,F,8.5,CONTENT_W-18*mm)
        c.setFillColor(INK2); c.setFont(F,8.5)
        for ln in lns:
            if y<MY_BOT: break
            y-=10.5; c.drawString(14*mm+18*mm,y,ln)
 
    footer_line(c,2,4); c.showPage()
 
    # ── PÁG 3 DISTRIBUCIÓN ───────────────────────────
    c.setFillColor(BG); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,0,7*mm,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,H-1*mm,W,1*mm,fill=1,stroke=0)
    c.setFillColor(INK3); c.setFont(FM,7)
    c.drawString(14*mm,H-10*mm,u'C\u00d3MO DISTRIBUIR\u00cdA TU DINERO')
    c.drawRightString(W-MX,H-10*mm,nombre+u' \u00b7 '+loc)
    c.setFillColor(INK); c.setFont(FB,22)
    c.drawString(14*mm,H-26*mm,u'Si mi econom\u00eda dependiera de estos datos\u2026')
    c.setFillColor(INK3); c.setFont(F,9.5)
    c.drawString(14*mm,H-35*mm,u'Redistribuci\u00f3n inteligente sin tocar lo esencial')
    c.setStrokeColor(BORDER); c.setLineWidth(0.4)
    c.line(14*mm,H-40*mm,W-MX,H-40*mm)
 
    intro=u'Analizando tu desglose real, estos son los movimientos concretos que har\u00eda con tu dinero. No para recortarte la vida \u2014 sino para que cada euro trabaje mejor para ti y construyas seguridad financiera real sin sacrificar lo que importa.'
    y=H-48*mm
    for ln in wrap(c,intro,F,9,CONTENT_W):
        c.setFillColor(INK2); c.setFont(F,9)
        c.drawString(14*mm,y,ln); y-=11.5
    y-=SP_SM; c.setStrokeColor(BORDER); c.setLineWidth(0.3)
    c.line(14*mm,y,W-MX,y); y-=SP_SM
 
    movimientos=generar_distribucion(ingresos,gastos_data,tl,margen,ratio,cmeses,ns,gastos_mes,loc)
    for i,mov in enumerate(movimientos):
        if y<MY_BOT: break
        if i>0:
            y-=SEP; c.setStrokeColor(BORDER); c.setLineWidth(0.3)
            c.line(14*mm,y,W-MX,y); y-=SEP
            if y<MY_BOT: break
        ahorro_m=mov.get('ahorro',0)
        circle_num(c,14*mm+7*mm,y-4*mm,7*mm,i+1,SC)
        c.setFillColor(INK); c.setFont(FB,10.5)
        c.drawString(14*mm+18*mm,y,mov['titulo'])
        if ahorro_m>0:
            tag='+'+str(ahorro_m)+u' '+EUR+u'/mes'
            tw=c.stringWidth(tag,FB,7.5)+10*mm
            c.setFillColor(VERDE_L); c.roundRect(W-MX-tw,y-2*mm,tw,7*mm,2*mm,fill=1,stroke=0)
            c.setFillColor(VERDE); c.setFont(FB,7.5)
            c.drawCentredString(W-MX-tw/2,y+1*mm,tag)
        elif ahorro_m<0:
            tag=str(abs(ahorro_m))+u' '+EUR+u'/mes al ahorro'
            tw=c.stringWidth(tag,FB,7.5)+10*mm
            c.setFillColor(SL); c.roundRect(W-MX-tw,y-2*mm,tw,7*mm,2*mm,fill=1,stroke=0)
            c.setFillColor(SC); c.setFont(FB,7.5)
            c.drawCentredString(W-MX-tw/2,y+1*mm,tag)
        y-=3.5*mm
        for ln in wrap(c,mov['motivo'],F,8.5,CONTENT_W-18*mm):
            if y<MY_BOT: break
            c.setFillColor(INK2); c.setFont(F,8.5)
            y-=10.5; c.drawString(14*mm+18*mm,y,ln)
 
    y-=SP_LG
    total_lib=sum(m.get('ahorro',0) for m in movimientos if m.get('ahorro',0)>0)
    if total_lib>0 and y>MY_BOT+16*mm:
        c.setFillColor(INK); c.roundRect(14*mm,y-13*mm,CONTENT_W+6*mm,12*mm,3*mm,fill=1,stroke=0)
        impacto=u'Aplicando estos movimientos, liberar\u00edas '+str(total_lib)+u' '+EUR+u'/mes. En 12 meses: '+str(total_lib*12)+u' '+EUR+u' adicionales en el colch\u00f3n \u2014 '+str(round(total_lib*12/gastos_mes,1))+u' meses extra de seguridad.'
        c.setFillColor(WHITE); c.setFont(FB,8.5)
        imp_y=y-4.5*mm
        for ln in wrap(c,impacto,FB,8.5,CONTENT_W-2*SP_MD)[:2]:
            c.drawString(14*mm+SP_MD,imp_y,ln); imp_y-=11
 
    footer_line(c,3,4); c.showPage()
 
    # ── PÁG 4 NOTICIAS (solo si hay noticias) ───────────
    if not noticias:
        c.save(); buf.seek(0); return buf.read()
    c.setFillColor(DARK); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,0,7*mm,H,fill=1,stroke=0)
    c.setFillColor(SC); c.rect(0,H-1*mm,W,1*mm,fill=1,stroke=0)
    c.setFillColor(INK3); c.setFont(FM,7)
    c.drawString(14*mm,H-10*mm,'NOTICIAS QUE TE AFECTAN DIRECTAMENTE')
    c.drawRightString(W-MX,H-10*mm,nombre+u' \u00b7 '+loc)
    c.setFillColor(WHITE); c.setFont(FB,20)
    c.drawString(14*mm,H-26*mm,u'Lo que est\u00e1 pasando ahora mismo')
    c.setFillColor(HexColor('#777777')); c.setFont(F,9.5)
    c.drawString(14*mm,H-35*mm,u'Seleccionado para tu perfil financiero en '+loc)
    c.setStrokeColor(HexColor('#2A2A2A')); c.setLineWidth(0.4)
    c.line(14*mm,H-40*mm,W-MX,H-40*mm)
 
    yn=H-50*mm
    for i,noticia in enumerate(noticias[:3]):
        if yn<40*mm: break
        if i>0:
            yn-=SP_SM; c.setStrokeColor(HexColor('#222222')); c.setLineWidth(0.25)
            c.line(14*mm,yn,W-MX,yn); yn-=SP_SM
        c.setFillColor(SC); c.setFont(FB,6.5)
        c.drawString(14*mm,yn,(u'PARA TI: '+noticia.get('contexto','')).upper()[:78])
        yn-=7.5*mm
        tit_lns=wrap(c,noticia.get('titular',''),FB,12,CONTENT_W+6*mm)
        c.setFillColor(WHITE); c.setFont(FB,12)
        for ln in tit_lns[:2]:
            c.drawString(14*mm,yn,ln); yn-=14
        yn-=SP_XS
        dev=noticia.get('desarrollo','')
        if dev:
            dev_lns=wrap(c,dev,F,8.5,CONTENT_W+6*mm)
            c.setFillColor(HexColor('#BBBBBB')); c.setFont(F,8.5)
            for ln in dev_lns[:9]:
                if yn<40*mm: break
                c.drawString(14*mm,yn,ln); yn-=10.5
        yn-=SP_XS
        c.setFillColor(HexColor('#555555')); c.setFont(F,7)
        c.drawString(14*mm,yn,noticia.get('fuente','')+u' \u00b7 '+noticia.get('fecha',''))
        yn-=SP_SM
 
    c.setFillColor(SC); c.roundRect(14*mm,26*mm,CONTENT_W+6*mm,15*mm,3*mm,fill=1,stroke=0)
    c.setFillColor(DARK); c.setFont(FB,10)
    c.drawCentredString(W/2,33*mm,u'"Este an\u00e1lisis es tuyo. Gu\u00e1rdalo, \u00fasalo, decide con criterio."')
    c.setFillColor(HexColor('#444444')); c.setFont(F,6.5)
    c.drawString(14*mm,11*mm,u'melopuedopermitir.com  \u00b7  Banco de Espa\u00f1a \u00b7 OCDE \u00b7 BCE')
    c.drawRightString(W-MX,11*mm,'4 / 4')
 
    c.showPage(); c.save()
    buf.seek(0)
    return buf.read()
