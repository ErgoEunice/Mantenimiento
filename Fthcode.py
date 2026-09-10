import streamlit as st
import io
import os
from PIL import Image
from streamlit_js_eval import get_geolocation
from geopy.geocoders import Nominatim

# Librerías para generación de PDF con ReportLab
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y COLORES ERGO SOLAR
# ==========================================
st.set_page_config(
    page_title="Reportes de Mantenimiento | Ergo Solar",
    page_icon="☀️",
    layout="wide"
)

COLOR_NARANJA = "#ff5e00"
COLOR_NARANJA_CLARO = "#ffae7f"
COLOR_AZUL = "#001489"
COLOR_GRIS_OSCURO = "#686666"
COLOR_GRIS_CLARO = "#e0e0e0"

st.markdown(f"""
    <style>
    body, .stApp {{
        background-color: #e0e0e0;
        color: {COLOR_AZUL};
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {COLOR_AZUL} !important;
        font-weight: 700;
    }}
    .stWidgetLabel p, label, .stWidgetLabel label {{
        color: {COLOR_GRIS_OSCURO} !important;  
        font-weight: bold !important;
        font-size: 15px !important;
    }}
    .stButton>button {{
        background-color: {COLOR_NARANJA};
        color:  white !important;
        border-radius: 6px;
        border: none;
        font-weight: bold;
    }}
    .stButton>button:hover {{
        background-color: {COLOR_NARANJA_CLARO};
        color: {COLOR_AZUL} !important;
    }}
    .section-header {{ 
        border-left: 5px solid {COLOR_NARANJA}; 
        padding-left: 15px !important; 
        margin-top: 30px !important;  
        margin-bottom: 20px !important;
    }}
    .card {{
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid {COLOR_GRIS_CLARO};
        margin-bottom: 15px;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIC Y PLANTILLAS DE PDF (REPORTLAB)
# ==========================================

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # ENCABEZADO
        if self._pageNumber > 1:
            if os.path.exists("ErgoSolar_logo.png"):
                self.drawImage("ErgoSolar_logo.png", 36, 740, width=120, height=40, preserveAspectRatio=True, mask='auto')
            
            self.setFont("Helvetica-Bold", 11)
            self.setFillColor(colors.HexColor(COLOR_AZUL))
            self.drawRightString(576, 755, "Asset Management")
            
            self.setStrokeColor(colors.HexColor(COLOR_NARANJA))
            self.setLineWidth(1)
            self.line(36, 730, 576, 730)

        # PIE DE PÁGINA
        if os.path.exists("ErgoPieReporte.png"):
            self.drawImage("ErgoPieReporte.png", 36, 15, width=540, height=35, preserveAspectRatio=True, mask='auto')
        else:
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor(COLOR_GRIS_OSCURO))
            self.drawString(36, 20, "Ergo Solar - Soluciones en Energía Fotovoltaica y Eficiencia Energética")
            self.drawRightString(576, 20, f"Página {self._pageNumber} de {page_count}")
            
        self.restoreState()


def generar_pdf_reporte(datos):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    style_titulo = ParagraphStyle(
        'TituloCustom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor(COLOR_AZUL),
        spaceAfter=10
    )
    
    style_subtitulo = ParagraphStyle(
        'SubtituloCustom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor(COLOR_AZUL),
        spaceBefore=12,
        spaceAfter=6
    )
    
    style_body = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor(COLOR_GRIS_OSCURO)
    )

    style_header_table = ParagraphStyle(
        'HeaderTable',
        parent=style_body,
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )
    
    style_caption = ParagraphStyle(
        'CaptionCustom',
        parent=styles['Italic'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor(COLOR_GRIS_OSCURO),
        spaceBefore=4,
        spaceAfter=8
    )

    contador_ilustraciones = 1

    # BANNER
    if os.path.exists("BannerMantenimiento.png"):
        story.append(RLImage("BannerMantenimiento.png", width=540, height=100, preserveAspectRatio=True))
        story.append(Spacer(1, 15))

    # 1. INFORMACIÓN DEL CLIENTE
    story.append(Paragraph("REPORTE DE MANTENIMIENTO PREVENTIVO / CORRECTIVO", style_titulo))
    
    data_cliente = [
        [Paragraph("<b>Planta:</b>", style_body), Paragraph(datos['info_cliente']['planta'], style_body),
         Paragraph("<b>Fecha:</b>", style_body), Paragraph(str(datos['info_cliente']['fecha']), style_body)],
        [Paragraph("<b>Dirección:</b>", style_body), Paragraph(datos['info_cliente']['direccion'], style_body),
         Paragraph("<b>Técnico:</b>", style_body), Paragraph(datos['info_cliente']['tecnico'], style_body)]
    ]
    
    tabla_cliente = Table(data_cliente, colWidths=[1.1*inch, 2.7*inch, 0.9*inch, 2.8*inch])
    tabla_cliente.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFFFFF")),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor(COLOR_GRIS_OSCURO)),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor(COLOR_GRIS_CLARO)),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor(COLOR_GRIS_CLARO)),
    ]))
    story.append(tabla_cliente)
    story.append(Spacer(1, 15))

    # 2. INSPECCIÓN INICIAL
    story.append(Paragraph("1. Inspección Inicial del Sistema", style_subtitulo))
    if datos['inspecciones']:
        for idx, obs in enumerate(datos['inspecciones']):
            texto_obs = f"<b>Observación {idx+1}: {obs['titulo']}</b><br/>{obs['descripcion']}"
            story.append(Paragraph(texto_obs, style_body))
            story.append(Spacer(1, 4))
            
            if obs['foto'] is not None:
                img_temp = Image.open(obs['foto'])
                img_temp.thumbnail((350, 250))
                img_buffer = io.BytesIO()
                img_temp.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                story.append(RLImage(img_buffer, width=img_temp.width * 0.7, height=img_temp.height * 0.7))
                
                caption_text = f"Ilustración #{contador_ilustraciones}"
                if obs['pie']:
                    caption_text += f": {obs['pie']}"
                story.append(Paragraph(caption_text, style_caption))
                contador_ilustraciones += 1
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No se registraron observaciones iniciales.", style_body))

    story.append(Spacer(1, 10))

    # 3. ACTIVIDADES REALIZADAS
    story.append(Paragraph("2. Actividades Realizadas", style_subtitulo))
    if datos['actividades']:
        for idx, act in enumerate(datos['actividades']):
            texto_act = f"<b>Actividad {idx+1}: {act['titulo']}</b><br/>{act['descripcion']}"
            story.append(Paragraph(texto_act, style_body))
            story.append(Spacer(1, 4))
            
            if act['fotos']:
                for foto_item in act['fotos']:
                    if foto_item['archivo'] is not None:
                        img_temp = Image.open(foto_item['archivo'])
                        img_temp.thumbnail((350, 250))
                        img_buffer = io.BytesIO()
                        img_temp.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        
                        story.append(RLImage(img_buffer, width=img_temp.width * 0.7, height=img_temp.height * 0.7))
                        
                        caption_text = f"Ilustración #{contador_ilustraciones}"
                        if foto_item['pie']:
                            caption_text += f": {foto_item['pie']}"
                        story.append(Paragraph(caption_text, style_caption))
                        contador_ilustraciones += 1
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No se registraron actividades adicionales.", style_body))

    story.append(Spacer(1, 10))

    # 4. RESULTADOS DE MEDICIONES
    tipo_sis_txt = datos['tipo_sistema']
    story.append(Paragraph(f"3. Resultados de Mediciones (Sistema {tipo_sis_txt})", style_subtitulo))
    
    tabla_res_data = [
        [Paragraph("Medición / Elemento", style_header_table),
         Paragraph("Valor Referencia", style_header_table), 
         Paragraph("Valor Campo", style_header_table), 
         Paragraph("Conclusión", style_header_table)]
    ]
    
    for row in datos['resultados']:
        if row.get('es_categoria', False):
            style_cat = ParagraphStyle('CatStyle', parent=style_body, fontName='Helvetica-Bold', textColor=colors.HexColor(COLOR_AZUL))
            tabla_res_data.append([
                Paragraph(f"<b>{row['medicion']}</b>", style_cat),
                Paragraph("", style_body),
                Paragraph("", style_body),
                Paragraph("", style_body)
            ])
        else:
            tabla_res_data.append([
                Paragraph(row['medicion'], style_body),
                Paragraph(row['criterio'], style_body),
                Paragraph(row['valor'], style_body),
                Paragraph(row['conclusion'], style_body)
            ])
        
    tabla_resultados = Table(tabla_res_data, colWidths=[2.5*inch, 1.6*inch, 1.6*inch, 1.8*inch])
    
    estilo_tabla = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLOR_AZUL)),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor(COLOR_GRIS_CLARO)),
    ]

    for idx_f, row in enumerate(datos['resultados']):
        if row.get('es_categoria', False):
            estilo_tabla.append(('BACKGROUND', (0, idx_f+1), (-1, idx_f+1), colors.HexColor("#F0F0F0")))
            estilo_tabla.append(('SPAN', (0, idx_f+1), (-1, idx_f+1)))

    tabla_resultados.setStyle(TableStyle(estilo_tabla))
    story.append(tabla_resultados)
    story.append(Spacer(1, 15))

    # 5. CONCLUSIÓN
    story.append(Paragraph("4. Dictamen y Conclusión Final", style_subtitulo))
    story.append(Paragraph(datos['dictamen'] if datos['dictamen'] else "Sin dictamen registrado.", style_body))

    # Construir PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


# ==========================================
# 3. INTERFAZ EN STREAMLIT
# ==========================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(SCRIPT_DIR, "Ergologo.png")

col_logo, col_vacia = st.columns([2, 3])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_container_width=True)

st.title("GENERADOR DE REPORTES DE MANTENIMIENTO")
st.markdown("<p style='color: #686666;'>Captura de información en tiempo real para la generación del reporte técnico.</p>", unsafe_allow_html=True)

if 'num_observaciones' not in st.session_state:
    st.session_state.num_observaciones = 1

if 'num_actividades' not in st.session_state:
    st.session_state.num_actividades = 1

if "num_fotos_por_actividad" not in st.session_state:
    st.session_state.num_fotos_por_actividad = [1] * st.session_state.num_actividades

while len(st.session_state.num_fotos_por_actividad) < st.session_state.num_actividades:
    st.session_state.num_fotos_por_actividad.append(1)

# --- SECCIÓN 1: INFORMACIÓN DEL CLIENTE ---
st.markdown("<h3 class='section-header'>1. Información del Cliente</h3>", unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    planta = st.text_input("Nombre de la Planta", placeholder="Ej. Planta Solar Metales")
    
    # 1. Obtener la geolocalización desde el navegador
    loc = get_geolocation()
    
    direccion_detectada = "Obteniendo ubicación del dispositivo..."
    
    if loc and 'coords' in loc:
        lat = loc['coords']['latitude']
        lon = loc['coords']['longitude']
        
        # 2. Convertir Latitud y Longitud a una dirección física
        try:
            geolocator = Nominatim(user_agent="app_reporte_mantenimiento")
            location_info = geolocator.reverse(f"{lat}, {lon}")
            if location_info:
                direccion_detectada = location_info.address
            else:
                direccion_detectada = f"Lat: {lat}, Lon: {lon}"
        except Exception:
            direccion_detectada = f"Latitud: {lat}, Longitud: {lon}"
            
        st.success("📍 Ubicación detectada correctamente")
    else:
        st.info("⚠️ Permite el acceso a la ubicación en tu navegador para detectarla automáticamente.")

    direccion = st.text_area("Dirección", value=direccion_detectada, disabled=False)

with col2:
    fecha = st.date_input("Fecha de Mantenimiento")
    tecnico = st.text_input("Nombre del Técnico", placeholder="Ej. Ing. Carlos Pérez")

st.divider()

# --- SECCIÓN 2: INFORMACIÓN DEL SFV ---
st.markdown("<h3 class='section-header'>2. Información del SFV</h3>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    potinst = st.text_input("Potencia Instalada", placeholder="Ej. 100 kWp")
    numinve = st.text_input("Número de Inversores", placeholder="Ej. 4")

with col2:
    numpan = st.text_input("Número de Paneles", placeholder="Ej. 200")
    imax = st.text_input("Corriente máxima de operación del panel", placeholder="Imax")
    voc = st.text_input("Voltaje de Circuito Abierto del panel", placeholder="Voc")

datos_sfv = {
    "Potencia Instalada": potinst,
    "Número de Paneles": numpan,
    "Número de Inversores": numinve,
    "Ficha Técnica Panel": {
        "Imax": imax,
        "Voc": voc
    }
}
st.divider()

# --- SECCIÓN 3: INSPECCIÓN INICIAL DEL SISTEMA ---
st.markdown("<h3 class='section-header'>3. Inspección Inicial del Sistema</h3>", unsafe_allow_html=True)
st.info("Agrega las observaciones detectadas al inicio del mantenimiento.")

inspecciones_data = []

for i in range(st.session_state.num_observaciones):
    with st.container():
        st.markdown(f"**Observación #{i+1}**")
        col_obs1, col_obs2 = st.columns([2, 1])
        
        with col_obs1:
            tit_obs = st.text_input(f"Observación #{i+1}", key=f"obs_title_{i}")
            desc_obs = st.text_area(f"Descripción #{i+1}", key=f"obs_desc_{i}")
        
        with col_obs2:
            foto_obs = st.file_uploader(f"Fotografía / Evidencia #{i+1}", type=["jpg", "png", "jpeg"], key=f"obs_foto_{i}")
            pie_obs = st.text_input(f"Pie de Foto #{i+1}", key=f"obs_pie_{i}")
            
        inspecciones_data.append({
            'titulo': tit_obs,
            'descripcion': desc_obs,
            'foto': foto_obs,
            'pie': pie_obs
        })

if st.button("➕ Agregar Otra Observación", key="add_obs"):
    st.session_state.num_observaciones += 1
    st.rerun()

st.divider()

# --- SECCIÓN 4: ACTIVIDADES REALIZADAS ---
st.markdown("<h3 class='section-header'>4. Actividades Realizadas</h3>", unsafe_allow_html=True)

actividades_data = []

for j in range(st.session_state.num_actividades):
    with st.container():
        st.markdown(f"**Actividad #{j+1}**")
        
        col_act1, col_act2 = st.columns([2, 1])

        with col_act1:
            tit_act = st.text_input(f"Actividad Realizada #{j+1}", key=f"act_title_{j}")
            desc_act = st.text_area(f"Descripción de la Actividad #{j+1}", key=f"act_desc_{j}")

        with col_act2:
            st.markdown("**Evidencias / Fotografía**")
            fotos_actividad = []
            
            num_fotos_actuales = st.session_state.num_fotos_por_actividad[j]
            
            for k in range(num_fotos_actuales):
                foto_file = st.file_uploader(f"Fotografía #{k+1} (Act. #{j+1})", type=["jpg", "png", "jpeg"], key=f"act_foto_{j}_{k}")
                pie_file = st.text_input(f"Pie de foto #{k+1} (Act. #{j+1})", key=f"act_pie_{j}_{k}")
                
                if foto_file is not None:
                    fotos_actividad.append({'archivo': foto_file, 'pie': pie_file})
                
                if k < num_fotos_actuales - 1:
                    st.markdown("---")
            
            if num_fotos_actuales < 10:
                if st.button(f"📷 Agregar otra foto a Actividad #{j+1}", key=f"add_foto_act_{j}"):
                    st.session_state.num_fotos_por_actividad[j] += 1
                    st.rerun()
            else:
                st.info("Límite de 10 fotografías alcanzado.")

        actividades_data.append({
            'titulo': tit_act,
            'descripcion': desc_act,
            'fotos': fotos_actividad
        })


if st.button("➕ Agregar Otra Actividad", key="add_act"):
    st.session_state.num_actividades += 1
    st.rerun()

st.divider()

# --- SECCIÓN 5: RESULTADOS (MONOFÁSICO Y TRIFÁSICO) ---
st.markdown("<h3 class='section-header'>5. Resultados de Mediciones</h3>", unsafe_allow_html=True)

try:
    voc_panel_float = float(voc) if voc and voc.strip() != "" else 0.0
except ValueError:
    voc_panel_float = 0.0
imax_ref_val = imax.strip() if imax and imax.strip() != "" else "N/A"

tipo_sistema = st.radio(
    "Selecciona el tipo de sistema a evaluar:",
    ["Monofásico", "Trifásico"],
    horizontal=True,
    key="tipo_sistema_radio"
)

resultados_data = []

if tipo_sistema == "Monofásico":
    st.success("Configurando mediciones para Sistema Monofásico")

    # 1. ESTADO FÍSICO
    st.markdown("#### 🔍 Estado Físico")
    resultados_data.append({
        'medicion': "--- ESTADO FÍSICO ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    elementos_fisicos = ["Cableado", "Conexiones", "Corrosión", "Caja de Diodos", "Quemaduras"]

    col_h1, col_h2 = st.columns([1, 3])
    with col_h1:
        st.markdown("**Elemento**")
    with col_h2:
        st.markdown("**Descripción / Estado**")

    for idx, elem in enumerate(elementos_fisicos):
        c1, c2 = st.columns([1, 3])
        
        with c1:
            st.markdown(f"**{elem}**")
            
        with c2:
            desc_f = st.text_input(
                f"Estado de {elem}", 
                key=f"mono_fis_desc_{idx}", 
                label_visibility="collapsed"
            )
                
        resultados_data.append({
            'medicion': f"Estado Físico - {elem}",
            'valor': desc_f,
            'criterio': "N/A",
            'conclusion': desc_f,
            'es_categoria': False
        })

    st.divider()

    # 2. ESTADO ELÉCTRICO - Mediciones en Corriente Directa (CD)
    st.markdown("#### ☀️ Mediciones en Corriente Directa (CD)")
    resultados_data.append({
        'medicion': "--- MEDICIONES EN CORRIENTE DIRECTA (CD) ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    num_strings = st.number_input(
        "Número de Cadenas (Strings) a medir:", 
        min_value=1, max_value=20, value=1, step=1, key="num_strings_mono"
    )

    # ==========================================
    # TABLA 1: VOLTAJE POR CADENA
    # ==========================================
    st.markdown("##### ⚡ Voltaje por Cadena")
    
    col_v1, col_v2, col_v3 = st.columns([1.5, 2.5, 2.5])
    with col_v1:
        st.markdown("**Voltaje por cadena (V)**")
    with col_v2:
        st.markdown("**Valor medido**")
    with col_v3:
        st.markdown("**# de paneles** *(Cad / Voc)*")

    dict_voltajes = {}
    dict_paneles = {}

    for s in range(num_strings):
        c1, c2, c3 = st.columns([1.5, 2.5, 2.5])
        
        with c1:
            st.markdown(f"**Cad {s+1}**")
            
        with c2:
            val_v = st.text_input(
                f"Voltaje Cad #{s+1}", 
                placeholder="Ingrese valor medido", 
                key=f"voc_val_{s}", 
                label_visibility="collapsed"
            )
            dict_voltajes[s] = val_v

        with c3:
            try:
                val_v_float = float(val_v) if val_v and val_v.strip() != "" else 0.0
                if voc_panel_float > 0 and val_v_float > 0:
                    num_paneles_calc = round(val_v_float / voc_panel_float, 2)
                    str_paneles = f"{num_paneles_calc}"
                else:
                    str_paneles = "Ingresar Voc"
            except ValueError:
                str_paneles = "Inválido"

            st.text_input(
                f"# Paneles Cad #{s+1}", 
                value=str_paneles, 
                disabled=True, 
                key=f"paneles_calc_{s}", 
                label_visibility="collapsed"
            )
            dict_paneles[s] = str_paneles

    st.write("") # Espaciador entre tablas

    # ==========================================
    # TABLA 2: CORRIENTE POR CADENA
    # ==========================================
    st.markdown("##### 🔌 Corriente por Cadena")
    
    col_i1, col_i2, col_i3 = st.columns([1.5, 2.5, 2.5])
    with col_i1:
        st.markdown("**Corriente por cadena**")
    with col_i2:
        st.markdown("**Valor medido**")
    with col_i3:
        st.markdown("**Corriente máxima de operación**")

    for s in range(num_strings):
        c1, c2, c3 = st.columns([1.5, 2.5, 2.5])
        
        with c1:
            st.markdown(f"**Cad {s+1}**")
            
        with c2:
            val_i = st.text_input(
                f"Corriente Cad #{s+1}", 
                placeholder="Ingrese valor medido", 
                key=f"icd_val_{s}", 
                label_visibility="collapsed"
            )

        with c3:
            st.text_input(
                f"Imax Cad #{s+1}", 
                value=f"{imax_ref_val} A" if imax_ref_val != "N/A" else "N/A", 
                disabled=True, 
                key=f"imax_disp_{s}", 
                label_visibility="collapsed"
            )

        # Registro en PDF
        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Voltaje (V)",
            'valor': dict_voltajes.get(s, "-"),
            'criterio': f"# Paneles: {dict_paneles.get(s, 'N/A')}",
            'conclusion': "N/A",
            'es_categoria': False
        })
        
        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Corriente (A)",
            'valor': val_i if val_i else "-",
            'criterio': f"Imax Ref: {imax_ref_val} A",
            'conclusion': "N/A",
            'es_categoria': False
        })

    st.divider()
        
# 3. ESTADO ELÉCTRICO - Mediciones en Corriente Alterna (CA)
    st.markdown("#### ⚡ Mediciones en Corriente Alterna (CA)")
    resultados_data.append({
        'medicion': "--- MEDICIONES EN CORRIENTE ALTERNA (CA) ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # Encabezados estilo tabla
    col_ca1, col_ca2, col_ca3, col_ca4 = st.columns([2.5, 2.5, 2.5, 1.5])
    with col_ca1:
        st.markdown("**Medida**")
    with col_ca2:
        st.markdown("**Valor obtenido (V)**")
    with col_ca3:
        st.markdown("**Valor de referencia**")
    with col_ca4:
        st.markdown("**¿En rango?**")

    mediciones_ca = [
        ("Voltaje línea - neutro", "110 - 130"),
        ("Voltaje línea - fase", "110 - 130"),
        ("Voltaje neutro - tierra", "< 5")
    ]

    for idx, (med_name, ref_defecto) in enumerate(mediciones_ca):
        c1, c2, c3, c4 = st.columns([2.5, 2.5, 2.5, 1.5])
        
        # 1. Medida
        with c1:
            st.markdown(f"**{med_name}**")

        # 2. Valor obtenido (ingresado por el usuario)
        with c2:
            val_obt = st.text_input(
                f"Valor {med_name}", 
                placeholder="Valor medido", 
                key=f"ca_val_{idx}", 
                label_visibility="collapsed"
            )

        # 3. Valor de referencia
        with c3:
            val_ref = st.text_input(
                f"Ref {med_name}", 
                value=ref_defecto, 
                placeholder="Ej. 110 - 130 o < 5", 
                key=f"ca_crit_{idx}", 
                label_visibility="collapsed"
            )

        # 4. Evaluación automática de Rango (☑ / ☒)
        estado_rango = "---"
        
        if val_obt and val_obt.strip() != "":
            try:
                v_num = float(val_obt.strip())
                ref_clean = val_ref.strip()

                if "<" in ref_clean:
                    limite = float(ref_clean.replace("<", "").strip())
                    estado_rango = "☑" if v_num < limite else "☒"
                elif ">" in ref_clean:
                    limite = float(ref_clean.replace(">", "").strip())
                    estado_rango = "☑" if v_num > limite else "☒"
                elif "-" in ref_clean:
                    partes = ref_clean.split("-")
                    min_v = float(partes[0].strip())
                    max_v = float(partes[1].strip())
                    estado_rango = "☑" if min_v <= v_num <= max_v else "☒"
                else:
                    # Tolerancia +- 5% para valores fijos
                    r_num = float(ref_clean)
                    estado_rango = "☑" if (r_num * 0.95) <= v_num <= (r_num * 1.05) else "☒"
            except ValueError:
                estado_rango = "⚠️"

        with c4:
            st.markdown(f"### {estado_rango}")

        # Registro para el PDF
        resultados_data.append({
            'medicion': med_name,
            'valor': f"{val_obt} V" if val_obt else "-",
            'criterio': val_ref,
            'conclusion': "En Rango (☑)" if estado_rango == "☑" else ("Fuera de Rango (☒)" if estado_rango == "☒" else "N/A"),
            'es_categoria': False
        })

    st.divider()

# 4. PRUEBAS DE AISLAMIENTO Y TIERRA
    st.markdown("#### 🔒 Pruebas de Aislamiento y Fallo a Tierra")
    resultados_data.append({
        'medicion': "--- PRUEBAS DE AISLAMIENTO Y TIERRA ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # Pregunta sobre el tipo de canalización
    canalizacion = st.multiselect(
        "Características de la canalización (Selecciona si aplica):",
        ["Subterránea", "Aérea", "Mide más de 30m"],
        key="tipo_canalizacion"
    )

    # Encabezados de la tabla
    col_a1, col_a2, col_a3, col_a4 = st.columns([2.5, 2.5, 2.5, 1.5])
    with col_a1:
        st.markdown("**Medición**")
    with col_a2:
        st.markdown("**Valor de campo**")
    with col_a3:
        st.markdown("**Valor de referencia**")
    with col_a4:
        st.markdown("**¿En rango?**")

    # Lista base de mediciones: (Nombre, Referencia por defecto)
    mediciones_aislamiento = [
        ("Voltaje de fallo a tierra", "< 5"),
        ("Continuidad a tierra", "< 1")
    ]

    # Si se cumple alguna de las 3 condiciones de canalización, agregamos "Resistencia de aislamiento"
    if len(canalizacion) > 0:
        mediciones_aislamiento.append(("Resistencia de aislamiento", "> 5"))

    for idx, (med_name, ref_defecto) in enumerate(mediciones_aislamiento):
        c1, c2, c3, c4 = st.columns([2.5, 2.5, 2.5, 1.5])
        
        # 1. Nombre de la Medición
        with c1:
            st.markdown(f"**{med_name}**")

        # 2. Valor de Campo
        with c2:
            val_obt = st.text_input(
                f"Valor {med_name}", 
                placeholder="Valor medido", 
                key=f"ais_val_{idx}", 
                label_visibility="collapsed"
            )

        # 3. Valor de Referencia
        with c3:
            val_ref = st.text_input(
                f"Ref {med_name}", 
                value=ref_defecto, 
                placeholder="Ej. < 5 o > 5", 
                key=f"ais_crit_{idx}", 
                label_visibility="collapsed"
            )

        # 4. Evaluación automática del Rango (☑ / ☒)
        estado_rango = "---"
        
        if val_obt and val_obt.strip() != "":
            try:
                v_num = float(val_obt.strip())
                ref_clean = val_ref.strip()

                if "<" in ref_clean:
                    limite = float(ref_clean.replace("<", "").strip())
                    estado_rango = "☑" if v_num < limite else "☒"
                elif ">" in ref_clean:
                    limite = float(ref_clean.replace(">", "").strip())
                    estado_rango = "☑" if v_num > limite else "☒"
                elif "-" in ref_clean:
                    partes = ref_clean.split("-")
                    min_v = float(partes[0].strip())
                    max_v = float(partes[1].strip())
                    estado_rango = "☑" if min_v <= v_num <= max_v else "☒"
                else:
                    # Tolerancia +- 5% para valores fijos
                    r_num = float(ref_clean)
                    estado_rango = "☑" if (r_num * 0.95) <= v_num <= (r_num * 1.05) else "☒"
            except ValueError:
                estado_rango = "⚠️"

        with c4:
            st.markdown(f"### {estado_rango}")

        # Guardar en la estructura del PDF
        resultados_data.append({
            'medicion': med_name,
            'valor': val_obt if val_obt else "-",
            'criterio': val_ref,
            'conclusion': "En Rango (☑)" if estado_rango == "☑" else ("Fuera de Rango (☒)" if estado_rango == "☒" else "N/A"),
            'es_categoria': False
        })

    st.divider()

# 5. TERMOGRAFÍA
    st.markdown("#### 🌡️ Análisis Termográfico")
    resultados_data.append({
        'medicion': "--- PRUEBA DE TERMOGRAFÍA ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # Encabezados de la tabla
    col_t1, col_t2, col_t3, col_t4 = st.columns([2, 2.5, 2.5, 3])
    with col_t1:
        st.markdown("**Equipo**")
    with col_t2:
        st.markdown("**Temperatura (°C)**")
    with col_t3:
        st.markdown("**Rango de Operación**")
    with col_t4:
        st.markdown("**Evidencia Fotográfica**")

    # Lista de equipos con su rango de operación sugerido por defecto
    elementos_termografia = [
        ("Paneles", "25 - 65 °C"),
        ("ITM", "< 60 °C"),
        ("Inversores", "25 - 60 °C"),
        ("Bloques de distribución", "< 60 °C")
    ]

    # Diccionario opcional para almacenar imágenes capturadas si lo requieres luego en el PDF
    fotos_termografia = {}

    for idx, (elem_name, rango_defecto) in enumerate(elementos_termografia):
        c1, c2, c3, c4 = st.columns([2, 2.5, 2.5, 3])
        
        # 1. Equipo
        with c1:
            st.markdown(f"**{elem_name}**")

        # 2. Temperatura (Ingreso del usuario)
        with c2:
            temp_val = st.text_input(
                f"Temp {elem_name}", 
                placeholder="Ej. 45 °C", 
                key=f"termo_val_{idx}", 
                label_visibility="collapsed"
            )

        # 3. Rango de Operación
        with c3:
            rango_val = st.text_input(
                f"Rango {elem_name}", 
                value=rango_defecto, 
                placeholder="Ej. 25 - 65 °C", 
                key=f"termo_crit_{idx}", 
                label_visibility="collapsed"
            )

        # 4. Evidencia (Subir foto)
        with c4:
            foto_evidencia = st.file_uploader(
                f"Foto {elem_name}", 
                type=["jpg", "jpeg", "png"], 
                key=f"termo_foto_{idx}", 
                label_visibility="collapsed"
            )
            if foto_evidencia is not None:
                fotos_termografia[elem_name] = foto_evidencia

        # Guardar registros de texto para la estructura final / PDF
        resultados_data.append({
            'medicion': f"Termografía - {elem_name}",
            'valor': temp_val if temp_val else "-",
            'criterio': rango_val,
            'conclusion': "Foto adjunta" if foto_evidencia else "Sin foto",
            'es_categoria': False
        })

else:
    # ==========================================
    # LOGICA DE CIRCUITO TRIFÁSICO
    # ==========================================
    st.info("Configurando mediciones para Sistema Trifásico")

    # 1. ESTADO FÍSICO
    st.markdown("#### 🔍 Estado Físico")
    resultados_data.append({
        'medicion': "--- ESTADO FÍSICO ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    elementos_fisicos = ["Cableado", "Conexiones", "Corrosión", "Caja de Diodos", "Quemaduras"]

    col_h1, col_h2 = st.columns([1, 3])
    with col_h1:
        st.markdown("**Elemento**")
    with col_h2:
        st.markdown("**Descripción / Estado**")

    for idx, elem in enumerate(elementos_fisicos):
        c1, c2 = st.columns([1, 3])
        
        with c1:
            st.markdown(f"**{elem}**")
            
        with c2:
            desc_f = st.text_input(
                f"Estado de {elem}", 
                key=f"mono_fis_desc_{idx}", 
                label_visibility="collapsed"
            )
                
        resultados_data.append({
            'medicion': f"Estado Físico - {elem}",
            'valor': desc_f,
            'criterio': "N/A",
            'conclusion': desc_f,
            'es_categoria': False
        })

    st.divider()

# 2. ESTADO ELÉCTRICO - Mediciones en Corriente Directa (CD)
    st.markdown("#### ☀️ Mediciones en Corriente Directa (CD)")
    resultados_data.append({
        'medicion': "--- MEDICIONES EN CORRIENTE DIRECTA (CD) ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    num_strings = st.number_input(
        "Número de Cadenas (Strings) a medir:", 
        min_value=1, max_value=20, value=1, step=1, key="num_strings_mono"
    )

    # ==========================================
    # TABLA 1: VOLTAJE POR CADENA
    # ==========================================
    st.markdown("##### ⚡ Voltaje por Cadena")
    
    col_v1, col_v2, col_v3 = st.columns([1.5, 2.5, 2.5])
    with col_v1:
        st.markdown("**Voltaje por cadena (V)**")
    with col_v2:
        st.markdown("**Valor medido**")
    with col_v3:
        st.markdown("**# de paneles** *(Cad / Voc)*")

    dict_voltajes = {}
    dict_paneles = {}

    for s in range(num_strings):
        c1, c2, c3 = st.columns([1.5, 2.5, 2.5])
        
        with c1:
            st.markdown(f"**Cad {s+1}**")
            
        with c2:
            val_v = st.text_input(
                f"Voltaje Cad #{s+1}", 
                placeholder="Ingrese valor medido", 
                key=f"voc_val_{s}", 
                label_visibility="collapsed"
            )
            dict_voltajes[s] = val_v

        with c3:
            try:
                val_v_float = float(val_v) if val_v and val_v.strip() != "" else 0.0
                if voc_panel_float > 0 and val_v_float > 0:
                    num_paneles_calc = round(val_v_float / voc_panel_float, 2)
                    str_paneles = f"{num_paneles_calc}"
                else:
                    str_paneles = "Ingresar Voc"
            except ValueError:
                str_paneles = "Inválido"

            st.text_input(
                f"# Paneles Cad #{s+1}", 
                value=str_paneles, 
                disabled=True, 
                key=f"paneles_calc_{s}", 
                label_visibility="collapsed"
            )
            dict_paneles[s] = str_paneles

    st.write("") # Espaciador entre tablas

    # ==========================================
    # TABLA 2: CORRIENTE POR CADENA
    # ==========================================
    st.markdown("##### 🔌 Corriente por Cadena")
    
    col_i1, col_i2, col_i3 = st.columns([1.5, 2.5, 2.5])
    with col_i1:
        st.markdown("**Corriente por cadena**")
    with col_i2:
        st.markdown("**Valor medido**")
    with col_i3:
        st.markdown("**Corriente máxima de operación**")

    for s in range(num_strings):
        c1, c2, c3 = st.columns([1.5, 2.5, 2.5])
        
        with c1:
            st.markdown(f"**Cad {s+1}**")
            
        with c2:
            val_i = st.text_input(
                f"Corriente Cad #{s+1}", 
                placeholder="Ingrese valor medido", 
                key=f"icd_val_{s}", 
                label_visibility="collapsed"
            )

        with c3:
            st.text_input(
                f"Imax Cad #{s+1}", 
                value=f"{imax_ref_val} A" if imax_ref_val != "N/A" else "N/A", 
                disabled=True, 
                key=f"imax_disp_{s}", 
                label_visibility="collapsed"
            )

        # Registro en PDF
        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Voltaje (V)",
            'valor': dict_voltajes.get(s, "-"),
            'criterio': f"# Paneles: {dict_paneles.get(s, 'N/A')}",
            'conclusion': "N/A",
            'es_categoria': False
        })
        
        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Corriente (A)",
            'valor': val_i if val_i else "-",
            'criterio': f"Imax Ref: {imax_ref_val} A",
            'conclusion': "N/A",
            'es_categoria': False
        })

    st.divider()

# 3. ESTADO ELÉCTRICO - CORRIENTE ALTERNA (CA)
    st.markdown("#### ⚡ Estado Eléctrico - Corriente Alterna (CA)")
    resultados_data.append({
        'medicion': "--- ESTADO ELÉCTRICO (CA) ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # Función auxiliar para evaluar si el valor está en rango (☑ / ☒)
    def evaluar_rango(val_str, ref_str):
        if not val_str or val_str.strip() == "":
            return "---"
        try:
            v_num = float(val_str.strip())
            ref_clean = ref_str.strip()

            if "<" in ref_clean:
                limite = float(ref_clean.replace("<", "").strip())
                return "☑" if v_num < limite else "☒"
            elif ">" in ref_clean:
                limite = float(ref_clean.replace(">", "").strip())
                return "☑" if v_num > limite else "☒"
            elif "-" in ref_clean:
                partes = ref_clean.split("-")
                min_v = float(partes[0].strip())
                max_v = float(partes[1].strip())
                return "☑" if min_v <= v_num <= max_v else "☒"
            else:
                r_num = float(ref_clean)
                return "☑" if (r_num * 0.95) <= v_num <= (r_num * 1.05) else "☒"
        except ValueError:
            return "⚠️"

    # Encabezados generales de la tabla
    col_h1, col_h2, col_h3, col_h4 = st.columns([2.5, 2.5, 2.5, 1.5])
    with col_h1:
        st.markdown("**Medida**")
    with col_h2:
        st.markdown("**Valor obtenido (V)**")
    with col_h3:
        st.markdown("**Valor de referencia**")
    with col_h4:
        st.markdown("**¿En rango?**")

    # Definición de mediciones estándar por equipo
    mediciones_trifasicas = [
        ("Voltaje línea 1 - línea 2", "210 - 230"),
        ("Voltaje línea 2 - línea 3", "210 - 230"),
        ("Voltaje línea 3 - línea 1", "210 - 230"),
        ("Voltaje línea 1 - neutro", "120 - 130"),
        ("Voltaje línea 2 - neutro", "120 - 130"),
        ("Voltaje línea 3 - neutro", "120 - 130"),
        ("Voltaje neutro - tierra", "< 5")
    ]

    secciones_ca = [
        ("Inversor", "inv"),
        ("Bloque de distribución", "bloq"),
        ("Interruptor", "inter")
    ]

    for titulo_sec, prefix in secciones_ca:
        # Subencabezado estilo celda combinada
        st.info(f"**{titulo_sec}**")
        
        for idx, (med_name, ref_defecto) in enumerate(mediciones_trifasicas):
            c1, c2, c3, c4 = st.columns([2.5, 2.5, 2.5, 1.5])
            
            # 1. Medida
            with c1:
                st.markdown(f"**{med_name}**")

            # 2. Valor obtenido (ingresado por el usuario)
            with c2:
                val_obt = st.text_input(
                    f"Valor {titulo_sec} - {med_name}", 
                    placeholder="Valor medido", 
                    key=f"{prefix}_val_{idx}", 
                    label_visibility="collapsed"
                )

            # 3. Valor de referencia
            with c3:
                val_ref = st.text_input(
                    f"Ref {titulo_sec} - {med_name}", 
                    value=ref_defecto, 
                    placeholder="Ej. 210 - 230", 
                    key=f"{prefix}_ref_{idx}", 
                    label_visibility="collapsed"
                )

            # 4. Evaluación automática de Rango (☑ / ☒)
            estado_rango = evaluar_rango(val_obt, val_ref)

            with c4:
                st.markdown(f"### {estado_rango}")

            # Registro de datos para la exportación / PDF
            resultados_data.append({
                'medicion': f"{titulo_sec} - {med_name}",
                'valor': f"{val_obt} V" if val_obt else "-",
                'criterio': val_ref,
                'conclusion': "En Rango (☑)" if estado_rango == "☑" else ("Fuera de Rango (☒)" if estado_rango == "☒" else "N/A"),
                'es_categoria': False
            })

    st.divider()

# 4. PRUEBAS DE AISLAMIENTO Y TIERRA
    st.markdown("#### 🔒 Pruebas de Aislamiento y Fallo a Tierra")
    resultados_data.append({
        'medicion': "--- PRUEBAS DE AISLAMIENTO Y TIERRA ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # Pregunta sobre el tipo de canalización
    canalizacion = st.multiselect(
        "Características de la canalización (Selecciona si aplica):",
        ["Subterránea", "Aérea", "Mide más de 30m"],
        key="tipo_canalizacion"
    )

    # Encabezados de la tabla
    col_a1, col_a2, col_a3, col_a4 = st.columns([2.5, 2.5, 2.5, 1.5])
    with col_a1:
        st.markdown("**Medición**")
    with col_a2:
        st.markdown("**Valor de campo**")
    with col_a3:
        st.markdown("**Valor de referencia**")
    with col_a4:
        st.markdown("**¿En rango?**")

    # Lista base de mediciones: (Nombre, Referencia por defecto)
    mediciones_aislamiento = [
        ("Voltaje de fallo a tierra", "< 5"),
        ("Continuidad a tierra", "< 1")
    ]

    # Si se cumple alguna de las 3 condiciones de canalización, agregamos "Resistencia de aislamiento"
    if len(canalizacion) > 0:
        mediciones_aislamiento.append(("Resistencia de aislamiento", "> 5"))

    for idx, (med_name, ref_defecto) in enumerate(mediciones_aislamiento):
        c1, c2, c3, c4 = st.columns([2.5, 2.5, 2.5, 1.5])
        
        # 1. Nombre de la Medición
        with c1:
            st.markdown(f"**{med_name}**")

        # 2. Valor de Campo
        with c2:
            val_obt = st.text_input(
                f"Valor {med_name}", 
                placeholder="Valor medido", 
                key=f"ais_val_{idx}", 
                label_visibility="collapsed"
            )

        # 3. Valor de Referencia
        with c3:
            val_ref = st.text_input(
                f"Ref {med_name}", 
                value=ref_defecto, 
                placeholder="Ej. < 5 o > 5", 
                key=f"ais_crit_{idx}", 
                label_visibility="collapsed"
            )

        # 4. Evaluación automática del Rango (☑ / ☒)
        estado_rango = "---"
        
        if val_obt and val_obt.strip() != "":
            try:
                v_num = float(val_obt.strip())
                ref_clean = val_ref.strip()

                if "<" in ref_clean:
                    limite = float(ref_clean.replace("<", "").strip())
                    estado_rango = "☑" if v_num < limite else "☒"
                elif ">" in ref_clean:
                    limite = float(ref_clean.replace(">", "").strip())
                    estado_rango = "☑" if v_num > limite else "☒"
                elif "-" in ref_clean:
                    partes = ref_clean.split("-")
                    min_v = float(partes[0].strip())
                    max_v = float(partes[1].strip())
                    estado_rango = "☑" if min_v <= v_num <= max_v else "☒"
                else:
                    # Tolerancia +- 5% para valores fijos
                    r_num = float(ref_clean)
                    estado_rango = "☑" if (r_num * 0.95) <= v_num <= (r_num * 1.05) else "☒"
            except ValueError:
                estado_rango = "⚠️"

        with c4:
            st.markdown(f"### {estado_rango}")

        # Guardar en la estructura del PDF
        resultados_data.append({
            'medicion': med_name,
            'valor': val_obt if val_obt else "-",
            'criterio': val_ref,
            'conclusion': "En Rango (☑)" if estado_rango == "☑" else ("Fuera de Rango (☒)" if estado_rango == "☒" else "N/A"),
            'es_categoria': False
        })

    st.divider()

# 5. TERMOGRAFÍA
    st.markdown("#### 🌡️ Análisis Termográfico")
    resultados_data.append({
        'medicion': "--- PRUEBA DE TERMOGRAFÍA ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # Encabezados de la tabla
    col_t1, col_t2, col_t3, col_t4 = st.columns([2, 2.5, 2.5, 3])
    with col_t1:
        st.markdown("**Equipo**")
    with col_t2:
        st.markdown("**Temperatura (°C)**")
    with col_t3:
        st.markdown("**Rango de Operación**")
    with col_t4:
        st.markdown("**Evidencia Fotográfica**")

    # Lista de equipos con su rango de operación sugerido por defecto
    elementos_termografia = [
        ("Paneles", "25 - 65 °C"),
        ("ITM", "< 60 °C"),
        ("Inversores", "25 - 60 °C"),
        ("Bloques de distribución", "< 60 °C")
    ]

    # Diccionario opcional para almacenar imágenes capturadas si lo requieres luego en el PDF
    fotos_termografia = {}

    for idx, (elem_name, rango_defecto) in enumerate(elementos_termografia):
        c1, c2, c3, c4 = st.columns([2, 2.5, 2.5, 3])
        
        # 1. Equipo
        with c1:
            st.markdown(f"**{elem_name}**")

        # 2. Temperatura (Ingreso del usuario)
        with c2:
            temp_val = st.text_input(
                f"Temp {elem_name}", 
                placeholder="Ej. 45 °C", 
                key=f"termo_val_{idx}", 
                label_visibility="collapsed"
            )

        # 3. Rango de Operación
        with c3:
            rango_val = st.text_input(
                f"Rango {elem_name}", 
                value=rango_defecto, 
                placeholder="Ej. 25 - 65 °C", 
                key=f"termo_crit_{idx}", 
                label_visibility="collapsed"
            )

        # 4. Evidencia (Subir foto)
        with c4:
            foto_evidencia = st.file_uploader(
                f"Foto {elem_name}", 
                type=["jpg", "jpeg", "png"], 
                key=f"termo_foto_{idx}", 
                label_visibility="collapsed"
            )
            if foto_evidencia is not None:
                fotos_termografia[elem_name] = foto_evidencia

        # Guardar registros de texto para la estructura final / PDF
        resultados_data.append({
            'medicion': f"Termografía - {elem_name}",
            'valor': temp_val if temp_val else "-",
            'criterio': rango_val,
            'conclusion': "Foto adjunta" if foto_evidencia else "Sin foto",
            'es_categoria': False
        })

# --- SECCIÓN 6: CONCLUSIÓN ---
st.markdown("<h3 class='section-header'>6. Conclusión</h3>", unsafe_allow_html=True)
dictamen = st.text_area("Dictamen del Mantenimiento", placeholder="Escribe aquí el dictamen técnico final...")

# --- GENERACIÓN DEL REPORT PDF ---
st.divider()

col_btn1, col_btn2 = st.columns([1, 2])

with col_btn1:
    if st.button("GENERAR PDF", type="primary", use_container_width=True):
        if not planta or not tecnico:
            st.error("Por favor completa al menos el nombre de la planta y del técnico.")
        else:
            datos_totales = {
                'info_cliente': {
                    'planta': planta,
                    'direccion': direccion,
                    'fecha': fecha,
                    'tecnico': tecnico
                },
                'tipo_sistema': tipo_sistema,
                'inspecciones': inspecciones_data,
                'actividades': actividades_data,
                'resultados': resultados_data,
                'dictamen': dictamen
            }
            
            pdf_bytes = generar_pdf_reporte(datos_totales)
            
            st.success("¡Reporte generado con éxito!")
            st.download_button(
                label="📥 Descargar Reporte en PDF",
                data=pdf_bytes,
                file_name=f"Reporte_Mantenimiento_{planta.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )