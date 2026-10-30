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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak, PageTemplate, BaseDocTemplate, Frame
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y COLORES ERGO SOLAR
# ==========================================
st.set_page_config(
    page_title="Reportes de Mantenimiento | Ergo Solar",
    page_icon="Ergogo.png",
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
# 2. LÓGICA Y PLANTILLAS DE PDF (REPORTLAB)
# ==========================================

class NumberedCanvas(canvas.Canvas):
    """
    Canvas personalizado para manejar de forma precisa los elementos gráficos 
    fijos (banners, logos, líneas divisorias y pie de página) diferenciando 
    la primera página de las páginas posteriores, permitiendo además 
    el conteo total de páginas.
    """
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

        # ----------------------------------------------------
        # DISEÑO EXCLUSIVO DE LA PRIMERA PÁGINA (PORTADA)
        # ----------------------------------------------------
        if self._pageNumber == 1:
            if os.path.exists("Ergobannermant.png"):
                ancho_banner = 612  # Ancho exacto del área útil (612 - 36 izq - 36 der)
                alto_banner = 100
                pos_x = (letter[0] - ancho_banner) / 2  # Centrado horizontal perfecto
                pos_y = letter[1] - alto_banner - 20 
                
                self.drawImage(
                    "Ergobannermant.png", 
                    pos_x, 
                    pos_y, 
                    width=ancho_banner, 
                    height=alto_banner, 
                    preserveAspectRatio=True, 
                    mask='auto'
                )
            
            # Pie de página para la primera página
            if os.path.exists("ErgoPieReporte.png"):
                self.drawImage("ErgoPieReporte.png", 36, 15, width=540, height=35, preserveAspectRatio=True, mask='auto')

        # ----------------------------------------------------
        # DISEÑO PARA LAS PÁGINAS POSTERIORES (2 EN ADELANTE)
        # ----------------------------------------------------
        else:
            # Logo superior izquierdo
            if os.path.exists("Ergologo.png"):
                self.drawImage("Ergologo.png", 36, 740, width=120, height=40, preserveAspectRatio=True, mask='auto')
            
            # Texto superior derecho
            self.setFont("Helvetica-Bold", 11)
            self.setFillColor(colors.HexColor(COLOR_AZUL))
            self.drawRightString(576, 755, "Asset Management")
            
            # Línea divisoria naranja (ubicada en y = 730)
            self.setStrokeColor(colors.HexColor(COLOR_NARANJA))
            self.setLineWidth(1)
            self.line(36, 730, 576, 730)

            # Pie de página para páginas siguientes
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

    page_width, page_height = letter
    left_margin = 36
    right_margin = 36
    bottom_margin = 54
    
    # ====================================================
    # DEFINICIÓN MATEMÁTICA DE MÁRGENES Y FRAMES
    # ====================================================
    
    # 1. Portada: El banner ocupa espacio arriba. Hacemos que el contenido empiece en y = 660 
    # (dejando espacio libre debajo del banner que termina aproximadamente en y = 682).
    top_margin_primera = 132  # 792 - 660 = 132 puntos desde arriba
    altura_frame_primera = page_height - top_margin_primera - bottom_margin

    frame_primera = Frame(
        left_margin, 
        bottom_margin, 
        page_width - left_margin - right_margin, 
        altura_frame_primera,
        topPadding=0,
        id='frame_primera'
    )
    
    # 2. Páginas posteriores: La línea naranja está en y = 730. 
    # Queremos que el texto comience justo debajo, en y = 715.
    top_margin_posteriores = 68  # 792 - 715 = 77 puntos desde arriba
    altura_frame_posteriores = page_height - top_margin_posteriores - bottom_margin

    frame_posteriores = Frame(
        left_margin, 
        bottom_margin, 
        page_width - left_margin - right_margin, 
        altura_frame_posteriores,
        topPadding=0,
        id='frame_posteriores'
    )

    # Documento base que administra múltiples plantillas de página
    doc = BaseDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=left_margin,
        rightMargin=right_margin,
        bottomMargin=bottom_margin
    )

    # Asociamos los marcos a las plantillas de página
    template_primera = PageTemplate(id='First', frames=frame_primera)
    template_siguientes = PageTemplate(id='Later', frames=frame_posteriores)
    
    doc.addPageTemplates([template_primera, template_siguientes])

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
        spaceBefore=6,
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

    # ====================================================
    # CONSTRUCCIÓN DEL CONTENIDO (STORY)
    # ====================================================

    # 1. INFORMACIÓN DEL CLIENTE
    
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

    # Compilación final del documento utilizando el NumberedCanvas unificado
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
            tit_obs = st.text_input(f"Observación #{i+1}", placeholder = "Ej. Paneles sucios/ Torques flojos/ Quemaduras/ Cableado suelto/ etc.", key = f"obs_title_{i}")
            desc_obs = st.text_area(f"Descripción #{i+1}", placeholder = "Ej. Los paneles presentan exceso del polvo/ Los torques no coinciden con las marcas/ Se observan quemaduras en el cableado del ITM del inversor/ Los cables debajo de los paneles no están sujetos a la estructura/ etc.", key=f"obs_desc_{i}")
        
        with col_obs2:
            foto_obs = st.file_uploader(f"Fotografía / Evidencia #{i+1}", type=["jpg", "png", "jpeg"], key=f"obs_foto_{i}")
            pie_obs = st.text_input(f"Pie de Foto #{i+1}", placeholder = "Describe lo que se observa en la fotografía agregada", key=f"obs_pie_{i}")
            
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
            tit_act = st.text_input(f"Actividad Realizada #{j+1}", placeholder = "Ej. Limpieza de paneles/ Reapriete de torques/ Cambio de cableado/ Sujetado de cableado/ etc.", key=f"act_title_{j}")
            desc_act = st.text_area(f"Descripción de la Actividad #{j+1}", placeholder = "Se limpiaron los paneles utilizando jabón y trapos especiales/ Se hizo el reapriete de los torques en ITM, paneles, inversores/ Se reemplazó el cableado quemado en el ITM del inversor/ Se sujetaron con cinchos los cables debajo de los paneles/ etc.", key=f"act_desc_{j}")

        with col_act2:
            st.markdown("**Evidencias / Fotografía**")
            fotos_actividad = []
            
            num_fotos_actuales = st.session_state.num_fotos_por_actividad[j]
            
            for k in range(num_fotos_actuales):
                foto_file = st.file_uploader(f"Fotografía #{k+1} (Act. #{j+1})", type=["jpg", "png", "jpeg"], key=f"act_foto_{j}_{k}")
                pie_file = st.text_input(f"Pie de foto #{k+1} (Act. #{j+1})", placeholder = "Describe lo que se observa en la fotografía agregada", key=f"act_pie_{j}_{k}")
                
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
    st.info("Describe el estado físico actual de cada uno de los siguientes elementos")
    resultados_data.append({
        'medicion': "--- ESTADO FÍSICO ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })
    placeholders = {
    "Tablero": "Ej. Bien torqueado/ conectado, sucio, con humedad, etc.",
    "Paneles": "Ej. En buen estado, rotos, sucios, etc.",
    "ITM": "Ej. En buen estado, presencia de quemaduras, etc.",
    "Cableado": "Ej. Correctamente conectado, etiquetado, coincide con el diagrama unifilar, etc.",
    "Canalización": "Ej. Correctamente instalada, con presencia de corrosión, etc.",
    "Inversores": "Ej. Bien conectado, en funcionamiento, desconectado, etc.",
    "Estructura": "Ej. con presencia de corrosión, bien sujeta/torqueada, etc.",
    "Monitoreo (DataLogger, ErgoMeter, Router)": "Ej. Bien ubicado, bien conectado, en funcionamiento, etc."
    } 
    elementos_fisicos = ["Tablero", "Paneles", "ITM", "Cableado", "Canalización", "Inversores", "Estructura", "Monitoreo (DataLogger, ErgoMeter, Router)"]

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
        # Obtenemos el placeholder del diccionario (con un mensaje por defecto en caso de no encontrar la clave)
            ph_texto = placeholders.get(elem, "Describe el estado físico del elemento")
        
            desc_f = st.text_input(
                f"Estado de {elem}", 
                placeholder=ph_texto,
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
    st.markdown("#### 🔍 Estado Eléctrico")
    st.markdown("##### ☀️ Mediciones en Corriente Directa (CD)")
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
    # BLOQUE 1: VOLTAJE POR CADENA
    # ==========================================
    st.markdown("###### ⚡ Voltaje por cadena")
    for s in range(num_strings):
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f"**Cadena {s+1}**")
        with c2:
            val_v = st.text_input(
                f"Voltaje Cadena {s+1}", 
                placeholder="(valor obtenido en campo)", 
                key=f"voc_val_{s}", 
                label_visibility="collapsed"
            )
            
        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Voltaje (V)",
            'valor': val_v if val_v else "-",
            'criterio': "N/A",
            'conclusion': "N/A",
            'es_categoria': False
        })

    st.write("") # Espaciado entre tablas

    # ==========================================
    # BLOQUE 2: CORRIENTE POR CADENA
    # ==========================================
    st.markdown("###### ⚡ Corriente por cadena")
    for s in range(num_strings):
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f"**Cadena {s+1}**")
        with c2:
            val_i = st.text_input(
                f"Corriente Cadena {s+1}", 
                placeholder="(valor obtenido en campo)", 
                key=f"icd_val_{s}", 
                label_visibility="collapsed"
            )

        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Corriente (A)",
            'valor': val_i if val_i else "-",
            'criterio': "N/A",
            'conclusion': "N/A",
            'es_categoria': False
        })

    st.divider()

# --- ESTADO ELÉCTRICO - CORRIENTE ALTERNA (CA) ---
    st.markdown("##### ⚡ Mediciones en Corriente Alterna (CA)")

    resultados_data.append({
        'medicion': "--- ESTADO ELÉCTRICO (CA) ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # --- CAMPOS DE ENTRADA GLOBALES (Según encabezado de la imagen) ---
    col_v_sys, col_i_nom = st.columns(2)
    with col_v_sys:
        voltaje_sistema = st.selectbox(
            "Voltaje del sistema (V):", 
            options=[480, 440, 220, 127], 
            index=0, 
            key="v_sistema_ca"
        )

    with col_i_nom:
        corriente_nominal_itm = st.number_input(
            "Corriente nominal ITM (A):", 
            min_value=0, value=500, step=10, key="corriente_nominal"
        )

    # 1. Selectores de cantidad de inversores e ITMs
    col_cnt1, col_cnt2 = st.columns(2)
    with col_cnt1:
        num_inversores = st.number_input(
            "Número de Inversores a evaluar:", 
            min_value=1, max_value=50, value=1, step=1, key="num_inversores_ca"
        )
    with col_cnt2:
        num_itm = st.number_input(
            "Número de ITM a evaluar:", 
            min_value=1, max_value=15, value=1, step=1, key="num_itm_ca"
        )

    # Definición de mediciones de voltaje según la tabla
    mediciones_voltaje = [
        ("Voltaje Línea - Neutro", "LN", "±10%"),
        ("Voltaje Línea - Tierra", "LT", "±10%"),
        ("Voltaje Neutro - Tierra", "NT", "2V")
    ]

    mediciones_corriente = [
        ("Corriente de Línea", "LINEA", "80% del ITM"),
        ("Corriente de Neutro", "NEUTRO", "N/A"),
        ("Corriente de Tierra", "TIERRA", "3mA")
    ]

    # 2. Generación dinámica de secciones (Inversores dinámicos + ITMs dinámicos + Secciones fijas)
    secciones_ca = []
    for i in range(int(num_inversores)):
        secciones_ca.append((f"Inversor {i+1}", f"inv_{i+1}"))
    
    for i in range(int(num_itm)):
        secciones_ca.append((f"ITM {i+1}", f"itm_{i+1}"))

    secciones_ca.append(("Bloque de distribución", "bloq"))

    # --- BLOQUE 1: VOLTAJES (CA) ---
    st.subheader("Voltajes")

    for titulo_sec, prefix in secciones_ca:
        st.info(f"**{titulo_sec} - Voltajes**")
        
        # Encabezados de tabla exactamente como en la imagen
        h1, h2, h3, h4 = st.columns([3, 2.5, 2, 2.5])
        with h1: st.caption("**Voltajes**")
        with h2: st.caption("**Valor Medido**")
        with h3: st.caption("**Límite de tolerancia**")
        with h4: st.caption("**¿En rango?**")

        # Renderizar filas y capturar datos por sección
        for idx, (med_name, grupo, limite_tol) in enumerate(mediciones_voltaje):
            c1, c2, c3, c4 = st.columns([3, 2.5, 2, 2.5])
            
            with c1:
                st.markdown(f"**{med_name}**")

            with c2:
                val_obt = st.text_input(
                    f"Valor {titulo_sec} - {med_name}", 
                    placeholder="Ingresar V", 
                    key=f"{prefix}_volt_val_{idx}", 
                    label_visibility="collapsed"
                )

            # Lógica de evaluación basada exactamente en la imagen
            estado_rango = "---"
            if val_obt and val_obt.strip() != "":
                try:
                    val_num = float(val_obt.strip())

                    # 1. Voltaje Línea-Neutro y Voltaje Línea-Tierra (±10% del Voltaje del sistema)
                    if grupo in ["LN", "LT"]:
                        v_min = voltaje_sistema * 0.90
                        v_max = voltaje_sistema * 1.10
                        if v_min <= val_num <= v_max:
                            estado_rango = "☑"
                        else:
                            estado_rango = "☒"
                            
                    # 2. Voltaje Neutro - Tierra (Menor o igual a 2V = ☑, mayor a 2V = ☒)
                    elif grupo == "NT":
                        if val_num <= 2.0:
                            estado_rango = "☑"
                        else:
                            estado_rango = "☒"

                except ValueError:
                    estado_rango = "⚠️"

            with c3:
                st.markdown(f"`{limite_tol}`")

            with c4:
                st.markdown(f"### {estado_rango}")

            # Guardar en reporte final
            resultados_data.append({
                'medicion': f"{titulo_sec} - {med_name}",
                'valor': f"{val_obt} V" if val_obt else "-",
                'criterio': f"Tolerancia {limite_tol}",
                'conclusion': estado_rango,
                'es_categoria': False
            })

    st.divider()
    
    # --- BLOQUE 2: CORRIENTES (CA) ---
    st.subheader("Corrientes")
    for titulo_sec, prefix in secciones_ca:
            st.info(f"**{titulo_sec} - Corrientes**")
            
            # Encabezados de tabla alineados a la imagen
            h1, h2, h3, h4 = st.columns([3, 2.5, 2, 2.5])
            with h1: st.caption("**Corrientes**")
            with h2: st.caption("**Valor Medido**")
            with h3: st.caption("**Límite de tolerancia**")
            with h4: st.caption("**¿En rango?**")

            # Diccionario auxiliar para comparar la corriente de Neutro contra la de Línea en la misma sección
            valores_seccion = {}

            for idx, (med_name, tipo_med, limite_tol) in enumerate(mediciones_corriente):
                c1, c2, c3, c4 = st.columns([3, 2.5, 2, 2.5])
                
                with c1:
                    st.markdown(f"**{med_name}**")

                with c2:
                    # El placeholder indica Amperios o Miliamperios según el tipo de lectura
                    ph_texto = "Ingresar mA" if tipo_med == "TIERRA" else "Ingresar A"
                    val_obt = st.text_input(
                        f"Valor {titulo_sec} - {med_name}", 
                        placeholder=ph_texto, 
                        key=f"{prefix}_curr_val_{idx}", 
                        label_visibility="collapsed"
                    )

                # Lógica de evaluación basada exactamente en la imagen
                estado_rango = "---"
                if val_obt and val_obt.strip() != "":
                    try:
                        val_num = float(val_obt.strip())
                        valores_seccion[tipo_med] = val_num

                        # 1. Corriente de Línea: Menor o igual al 80% de la capacidad nominal del ITM
                        if tipo_med == "LINEA":
                            limite_itm_80 = corriente_nominal_itm * 0.80
                            if val_num <= limite_itm_80:
                                estado_rango = "☑"
                            else:
                                estado_rango = "☒"

                        # 2. Corriente de Neutro: Igual a la Corriente de Línea ingresada
                        elif tipo_med == "NEUTRO":
                            if "LINEA" in valores_seccion:
                                if val_num == valores_seccion["LINEA"]:
                                    estado_rango = "☑"
                                else:
                                    estado_rango = "☒"
                            else:
                                estado_rango = "---"

                        # 3. Corriente de Tierra: Menor o igual a 3 mA
                        elif tipo_med == "TIERRA":
                            if val_num <= 3.0:
                                estado_rango = "☑"
                            else:
                                estado_rango = "☒"

                    except ValueError:
                        estado_rango = "⚠️"

                with c3:
                    st.markdown(f"`{limite_tol}`")

                with c4:
                    st.markdown(f"### {estado_rango}")

                # Guardar en reporte final
                unidad = "mA" if tipo_med == "TIERRA" else "A"
                resultados_data.append({
                    'medicion': f"{titulo_sec} - {med_name}",
                    'valor': f"{val_obt} {unidad}" if val_obt else "-",
                    'criterio': f"Tolerancia {limite_tol}",
                    'conclusion': estado_rango,
                    'es_categoria': False
                })

    st.divider()

else:
    # ==========================================
    # LOGICA DE CIRCUITO TRIFÁSICO
    # ==========================================
    st.info("Configurando mediciones para Sistema Trifásico")

    # 1. ESTADO FÍSICO
    st.markdown("#### 🔍 Estado Físico")
    st.info("Describe el estado físico actual de cada uno de los siguientes elementos")
    resultados_data.append({
        'medicion': "--- ESTADO FÍSICO ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })
    placeholders = {
    "Tablero": "Ej. Bien torqueado/ conectado, sucio, con humedad, etc.",
    "Paneles": "Ej. En buen estado, rotos, sucios, etc.",
    "ITM": "Ej. En buen estado, presencia de quemaduras, etc.",
    "Cableado": "Ej. Correctamente conectado, etiquetado, coincide con el diagrama unifilar, etc.",
    "Canalización": "Ej. Correctamente instalada, con presencia de corrosión, etc.",
    "Inversores": "Ej. Bien conectado, en funcionamiento, desconectado, etc.",
    "Estructura": "Ej. con presencia de corrosión, bien sujeta/torqueada, etc.",
    "Monitoreo (DataLogger, ErgoMeter, Router)": "Ej. Bien ubicado, bien conectado, en funcionamiento, etc."
    } 
    elementos_fisicos = ["Tablero", "Paneles", "ITM", "Cableado", "Canalización", "Inversores", "Estructura", "Monitoreo (DataLogger, ErgoMeter, Router)"]

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
        # Obtenemos el placeholder del diccionario (con un mensaje por defecto en caso de no encontrar la clave)
            ph_texto = placeholders.get(elem, "Describe el estado físico del elemento")
        
            desc_f = st.text_input(
                f"Estado de {elem}", 
                placeholder=ph_texto,
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
    st.markdown("#### 🔍 Estado Eléctrico")
    st.markdown("##### ☀️ Mediciones en Corriente Directa (DC)")
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
    # BLOQUE 1: VOLTAJE POR CADENA
    # ==========================================
    st.markdown("##### ⚡ Voltaje por cadena")
    for s in range(num_strings):
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f"**Cadena {s+1}**")
        with c2:
            val_v = st.text_input(
                f"Voltaje Cadena {s+1}", 
                placeholder="(valor obtenido en campo)", 
                key=f"voc_val_{s}", 
                label_visibility="collapsed"
            )
            
        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Voltaje (V)",
            'valor': val_v if val_v else "-",
            'criterio': "N/A",
            'conclusion': "N/A",
            'es_categoria': False
        })

    st.write("") # Espaciado entre tablas

    # ==========================================
    # BLOQUE 2: CORRIENTE POR CADENA
    # ==========================================
    st.markdown("##### ⚡ Corriente por cadena")
    for s in range(num_strings):
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f"**Cadena {s+1}**")
        with c2:
            val_i = st.text_input(
                f"Corriente Cadena {s+1}", 
                placeholder="(valor obtenido en campo)", 
                key=f"icd_val_{s}", 
                label_visibility="collapsed"
            )

        resultados_data.append({
            'medicion': f"Cadena #{s+1} - Corriente (A)",
            'valor': val_i if val_i else "-",
            'criterio': "N/A",
            'conclusion': "N/A",
            'es_categoria': False
        })

    st.divider()

# --- ESTADO ELÉCTRICO - CORRIENTE ALTERNA (AC) ---
    st.markdown("##### ⚡ Mediciones en Corriente Alterna (AC)")

    resultados_data = []
    resultados_data.append({
        'medicion': "--- ESTADO ELÉCTRICO (CA) ---", 
        'valor': "", 
        'criterio': "", 
        'conclusion': "", 
        'es_categoria': True
    })

    # --- CAMPOS GLOBALES DE ENTRADA ---
    col_v_sys, col_i_nom = st.columns(2)
    with col_v_sys:
        voltaje_sistema = st.selectbox(
            "Voltaje del sistema (V):", 
            options=[480, 440, 220, 127], 
            index=0, 
            key="v_sistema_ca"
        )

    with col_i_nom:
        corriente_nominal_itm = st.number_input(
            "Corriente nominal ITM (A):", 
            min_value=0, value=500, step=10, key="i_nominal_itm_ca"
        )

    # 1. Selectores de cantidad de inversores e ITMs
    col_cnt1, col_cnt2 = st.columns(2)
    with col_cnt1:
        num_inversores = st.number_input(
            "Número de Inversores a evaluar:", 
            min_value=1, max_value=50, value=1, step=1, key="num_inversores_ca"
        )
    with col_cnt2:
        num_itm = st.number_input(
            "Número de ITM a evaluar:", 
            min_value=1, max_value=15, value=1, step=1, key="num_itm_ca"
        )

    # Función auxiliar para calcular desbalance según norma NEMA (%)
    def calcular_desbalance_nema(valores):
        """Calcula el % de desbalance de un grupo de 3 valores trifásicos."""
        try:
            nums = [float(v.strip()) for v in valores if v and v.strip() != ""]
            if len(nums) < 3:
                return None  # Requiere las 3 lecturas para calcular
            
            promedio = sum(nums) / len(nums)
            if promedio == 0:
                return 0.0
                
            desviacion_maxima = max(abs(x - promedio) for x in nums)
            desbalance = (desviacion_maxima / promedio) * 100
            return round(desbalance, 2)
        except ValueError:
            return None

    # Definición de mediciones y límites de tolerancia según imagen
    mediciones_voltaje = [
        ("Voltaje Linea 1 - Linea 2", "LL", "2%"),
        ("Voltaje Linea 2 - Linea 3", "LL", "2%"),
        ("Voltaje Linea 3 - Linea 1", "LL", "2%"),
        ("Voltaje Linea 1 - Neutro",  "LN", "3%"),
        ("Voltaje Linea 2 - Neutro",  "LN", "3%"),
        ("Voltaje Linea 3 - Neutro",  "LN", "3%"),
        ("Voltaje Neutro - Tierra",   "NT", "5% del voltaje del sistema")
    ]

    mediciones_corriente = [
        ("Linea 1", "fase", "10%"),
        ("Linea 2", "fase", "10%"),
        ("Linea 3", "fase", "10%"),
        ("Corriente de Neutro", "NT", "<= 20% de I_max"),
        ("Corriente de Tierra", "NT", "< 1 A")
    ]

    # 2. Construcción dinámica de la lista de secciones corrigiendo los contadores
    secciones_ca = []
    for i in range(int(num_inversores)):
        secciones_ca.append((f"Inversor {i+1}", f"inv_{i+1}"))
    for i in range(int(num_itm)):
        secciones_ca.append((f"ITM {i+1}", f"itm_{i+1}"))

    secciones_ca.append(("Bloque de distribución", "bloq"))
    secciones_ca.append(("Interruptor", "inter"))


    # --- BLOQUE 1: VOLTAJES (CA) ---
    st.subheader("Voltajes")

    for titulo_sec, prefix in secciones_ca:
        st.info(f"**{titulo_sec} - Voltajes**")
        
        # 1. Encabezados de tabla de entrada
        h1, h2, h3 = st.columns([4, 3, 3])
        with h1: st.caption("**Voltajes**")
        with h2: st.caption("**Valor medido (V)**")
        with h3: st.caption("**Límite de tolerancia**")

        # 2. Filas de captura
        for idx, (med_name, grupo, tol_label) in enumerate(mediciones_voltaje):
            c1, c2, c3 = st.columns([4, 3, 3])
            
            with c1:
                st.markdown(f"**{med_name}**")

            with c2:
                st.text_input(
                    f"Valor {titulo_sec} - {med_name}", 
                    placeholder="Ingresar V", 
                    key=f"{prefix}_volt_val_{idx}", 
                    label_visibility="collapsed"
                )

            with c3:
                st.markdown(f"`{tol_label}`")

        # 3. Procesamiento y evaluación de datos agrupados
        vals_ingresados = [st.session_state.get(f"{prefix}_volt_val_{i}", "") for i in range(7)]
        vals_ll = vals_ingresados[0:3]
        vals_ln = vals_ingresados[3:6]
        val_nt_raw = vals_ingresados[6]

        desbal_linea = calcular_desbalance_nema(vals_ll)
        desbal_fase = calcular_desbalance_nema(vals_ln)

        # Evaluación: Desbalance de Línea (<= 3%)
        if desbal_linea is not None:
            txt_desbal_linea = f"{desbal_linea}%"
            estado_linea = "☑" if desbal_linea <= 3.0 else "☒"
        else:
            txt_desbal_linea = "---"
            estado_linea = "---"

        # Evaluación: Desbalance de Fase (<= 2%)
        if desbal_fase is not None:
            txt_desbal_fase = f"{desbal_fase}%"
            estado_fase = "☑" if desbal_fase <= 2.0 else "☒"
        else:
            txt_desbal_fase = "---"
            estado_fase = "---"

        # Evaluación: Neutro - Tierra (<= 5% del voltaje del sistema)
        limite_nt_5pct = float(voltaje_sistema) * 0.05
        if val_nt_raw and val_nt_raw.strip() != "":
            try:
                val_nt_num = float(val_nt_raw.strip())
                txt_nt = f"{val_nt_num} V"
                estado_nt = "☑" if val_nt_num <= limite_nt_5pct else "☒"
            except ValueError:
                txt_nt = "Error"
                estado_nt = "⚠️"
        else:
            txt_nt = "---"
            estado_nt = "---"

        # 4. Bloque final de la tabla: "¿En rango?"
        st.markdown("---")
        st.markdown("##### **¿En rango?**")
        
        # Desbalance de Voltaje de línea
        r1_c1, r1_c2, r1_c3 = st.columns([4, 4, 2])
        with r1_c1: st.markdown("**Desbalance de Voltaje de linea**")
        with r1_c2: st.markdown(f"`{txt_desbal_linea}`")
        with r1_c3: st.markdown(f"### {estado_linea}")

        # Desbalance de voltaje de fases
        r2_c1, r2_c2, r2_c3 = st.columns([4, 4, 2])
        with r2_c1: st.markdown("**Desbalance de voltaje de fases**")
        with r2_c2: st.markdown(f" `{txt_desbal_fase}`")
        with r2_c3: st.markdown(f"### {estado_fase}")

        # Neutro - Tierra
        r3_c1, r3_c2, r3_c3 = st.columns([4, 4, 2])
        with r3_c1: st.markdown("**Neutro - Tierra**")
        with r3_c2: st.markdown(f"Límite 5%: `{limite_nt_5pct:.2f} V`")
        with r3_c3: st.markdown(f"### {estado_nt}")

        # Guardar resumen en el reporte de salida
        for idx, (med_name, _, tol_label) in enumerate(mediciones_voltaje):
            v_val = st.session_state.get(f"{prefix}_volt_val_{idx}", "")
            resultados_data.append({
                'medicion': f"{titulo_sec} - {med_name}",
                'valor': f"{v_val} V" if v_val else "-",
                'criterio': tol_label,
                'conclusion': "Registrado",
                'es_categoria': False
            })

        resultados_data.append({
            'medicion': f"{titulo_sec} - Desbalance Voltaje de Línea",
            'valor': txt_desbal_linea,
            'criterio': "≤ 3%",
            'conclusion': estado_linea,
            'es_categoria': False
        })
        resultados_data.append({
            'medicion': f"{titulo_sec} - Desbalance Voltaje de Fases",
            'valor': txt_desbal_fase,
            'criterio': "≤ 2%",
            'conclusion': estado_fase,
            'es_categoria': False
        })
        resultados_data.append({
            'medicion': f"{titulo_sec} - Neutro - Tierra",
            'valor': txt_nt,
            'criterio': f"≤ 5% ({limite_nt_5pct:.2f} V)",
            'conclusion': estado_nt,
            'es_categoria': False
        })

    st.divider()

    # --- BLOQUE 2: CORRIENTES (CA) ---
    st.subheader("Corrientes")

    for titulo_sec, prefix in secciones_ca:
        st.info(f"**{titulo_sec} - Corrientes**")
        
        # 1. Encabezados de tabla de entrada
        h1, h2, h3 = st.columns([4, 3, 3])
        with h1: st.caption("**Corrientes**")
        with h2: st.caption("**Valor Medido (A)**")
        with h3: st.caption("**Límite de tolerancia**")

        # 2. Filas de captura de lecturas
        for idx, (med_name, _, tol_label) in enumerate(mediciones_corriente):
            c1, c2, c3 = st.columns([4, 3, 3])
            
            with c1:
                st.markdown(f"**{med_name}**")

            with c2:
                st.text_input(
                    f"Valor {titulo_sec} - {med_name}", 
                    placeholder="Ingresar A", 
                    key=f"{prefix}_curr_val_{idx}", 
                    label_visibility="collapsed"
                )

            with c3:
                st.markdown(f"`{tol_label}`")

        # 3. Lectura y procesamiento de valores de la sección
        vals_curr_raw = [st.session_state.get(f"{prefix}_curr_val_{i}", "") for i in range(5)]
        vals_fases = vals_curr_raw[0:3]
        val_neutro_raw = vals_curr_raw[3]
        val_tierra_raw = vals_curr_raw[4]

        # Convertir a números para cálculo
        nums_fases = []
        for v in vals_fases:
            try:
                nums_fases.append(float(v.strip()) if v and v.strip() != "" else None)
            except ValueError:
                nums_fases.append(None)

        # A) Evaluación Desbalance de Corriente L1-L2-L3 (<= 10%)
        desbal_corriente = calcular_desbalance_nema(vals_fases)
        if desbal_corriente is not None:
            txt_desbalance_curr = f"{desbal_corriente}%"
            estado_desbal_curr = "☑" if desbal_corriente <= 10.0 else "☒"
        else:
            txt_desbalance_curr = "---"
            estado_desbal_curr = "---"

        # B) Evaluación Corriente de Neutro (<= 20% del valor máximo de fase)
        fases_validas = [f for f in nums_fases if f is not None]
        i_max_fase = max(fases_validas) if fases_validas else 0.0
        limite_neutro = i_max_fase * 0.20

        if val_neutro_raw and val_neutro_raw.strip() != "":
            try:
                i_neutro = float(val_neutro_raw.strip())
                txt_neutro = f"{i_neutro} A"
                estado_neutro = "☑" if i_neutro <= limite_neutro else "☒"
            except ValueError:
                txt_neutro = "Error"
                estado_neutro = "⚠️"
        else:
            txt_neutro = "---"
            estado_neutro = "---"

        # C) Evaluación Corriente de Tierra (< 1.0 A)
        if val_tierra_raw and val_tierra_raw.strip() != "":
            try:
                i_tierra = float(val_tierra_raw.strip())
                txt_tierra = f"{i_tierra} A"
                estado_tierra = "☑" if i_tierra < 1.0 else "☒"
            except ValueError:
                txt_tierra = "Error"
                estado_tierra = "⚠️"
        else:
            txt_tierra = "---"
            estado_tierra = "---"

        # 4. Bloque final de la tabla: "¿En rango?"
        st.markdown("---")
        st.markdown("##### **¿En rango?**")

        # Desbalance de Corrientes
        r1_c1, r1_c2, r1_c3 = st.columns([4, 4, 2])
        with r1_c1: st.markdown("**Desbalance de Corrientes (L1, L2, L3)**")
        with r1_c2: st.markdown(f" `{txt_desbalance_curr}`")
        with r1_c3: st.markdown(f"### {estado_desbal_curr}")

        # Corriente de Neutro
        r2_c1, r2_c2, r2_c3 = st.columns([4, 4, 2])
        with r2_c1: st.markdown("**Corriente de Neutro**")
        with r2_c2: st.markdown(f"`{txt_neutro}`")
        with r2_c3: st.markdown(f"### {estado_neutro}")

        # Corriente de Tierra
        r3_c1, r3_c2, r3_c3 = st.columns([4, 4, 2])
        with r3_c1: st.markdown("**Corriente de Tierra**")
        with r3_c2: st.markdown(f"`{txt_tierra}`")
        with r3_c3: st.markdown(f"### {estado_tierra}")

        # Guardar en reporte final
        for idx, (med_name, _, tol_label) in enumerate(mediciones_corriente):
            curr_val = st.session_state.get(f"{prefix}_curr_val_{idx}", "")
            resultados_data.append({
                'medicion': f"{titulo_sec} - {med_name}",
                'valor': f"{curr_val} A" if curr_val else "-",
                'criterio': tol_label,
                'conclusion': "Registrado",
                'es_categoria': False
            })

        resultados_data.append({
            'medicion': f"{titulo_sec} - Desbalance Corrientes",
            'valor': txt_desbalance_curr,
            'criterio': "≤ 10%",
            'conclusion': estado_desbal_curr,
            'es_categoria': False
        })
        resultados_data.append({
            'medicion': f"{titulo_sec} - Corriente de Neutro",
            'valor': txt_neutro,
            'criterio': f"≤ 20% I_máx ({limite_neutro:.2f} A)",
            'conclusion': estado_neutro,
            'es_categoria': False
        })
        resultados_data.append({
            'medicion': f"{titulo_sec} - Corriente de Tierra",
            'valor': txt_tierra,
            'criterio': "< 1.0 A",
            'conclusion': estado_tierra,
            'es_categoria': False
        })

    st.divider()


# 6. PRUEBAS DE AISLAMIENTO Y TIERRA
st.markdown("#### 🔒 Pruebas de Aislamiento y Fallo a Tierra")
resultados_data.append({
    'medicion': "--- PRUEBAS DE AISLAMIENTO Y TIERRA ---", 
    'valor': "", 
    'criterio': "", 
    'conclusion': "", 
    'es_categoria': True 
})

# Pregunta sobre el tipo de canalización (Mantiene su estructura y función original intacta)
canalizacion = st.multiselect(
    "Características de la canalización (Selecciona si aplica):",
    ["Subterránea", "Aérea", "Mide más de 30m"],
    key="tipo_canalizacion"
)

# Selector para el Voltaje del Sistema (utilizado para calcular la referencia de fallo a tierra)
voltaje_sistema = st.selectbox(
    "Voltaje del sistema (V)",
    options=[480, 440, 220, 127],
    index=0,
    key="voltaje_sistema_val"
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

# Cálculo dinámico de la referencia para Voltaje de fallo a tierra (5% del voltaje del sistema)
ref_fallo_tierra_val = float(voltaje_sistema) * 0.05
ref_fallo_tierra_str = f"<= {ref_fallo_tierra_val:g} V"
# Lista base de mediciones con la nueva lógica
mediciones_aislamiento = [
    ("Voltaje de fallo a tierra", ref_fallo_tierra_str),
    ("Continuidad a tierra", "< 1ohm")
]

# Si se cumple alguna de las condiciones de canalización, agregamos "Resistencia de aislamiento"
if len(canalizacion) > 0:
    mediciones_aislamiento.append(("Resistencia de aislamiento", "2Gohms"))

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

    # 3. Valor de Referencia (Fijo / Calculado)
    with c3:
        st.markdown(f"{ref_defecto}")

    # 4. Evaluación automática del Rango (☑ / ☒)
    estado_rango = "---"       
    if val_obt and val_obt.strip() != "":
        try:
            v_num = float(val_obt.strip())
            
            if "Voltaje de fallo a tierra" in med_name:
                # Si el voltaje de fallo a tierra no es mayor al 5% del voltaje del sistema = ☑ / si es mayor = ☒
                estado_rango = "☑" if v_num <= ref_fallo_tierra_val else "☒"
            elif "Continuidad a tierra" in med_name:
                # Si la continuidad a tierra no es mayor a 1ohm = ☑ / si es mayor = ☒
                estado_rango = "☑" if v_num < 1.0 else "☒"
            elif "Resistencia de aislamiento" in med_name:
                estado_rango = "☑" if v_num > 2.0 else "☒"
            else:
                ref_clean = ref_defecto.strip()
                if "<" in ref_clean:
                    limite = float(ref_clean.replace("<", "").strip())
                    estado_rango = "☑" if v_num < limite else "☒"
                elif ">" in ref_clean:
                    limite = float(ref_clean.replace(">", "").strip())
                    estado_rango = "☑" if v_num > limite else "☒"
                else:
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
        'criterio': ref_defecto,
        'conclusion': "En Rango (☑)" if estado_rango == "☑" else ("Fuera de Rango (☒)" if estado_rango == "☒" else "N/A"),
        'es_categoria': False
    })

st.divider()

# 5. TERMOGRAFÍA
st.markdown("#### 🌡️ Análisis Termográfico")

# Contadores para la cantidad de inversores e ITMs
col_cnt1, col_cnt2 = st.columns(2)
with col_cnt1:
    num_inversores = st.number_input("Cantidad de Inversores", min_value=1, value=1, step=1, key="num_inversores")
with col_cnt2:
    num_itms = st.number_input("Cantidad de ITM", min_value=1, value=1, step=1, key="num_itms")

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

# Construir la lista de elementos dinámicamente según los contadores
elementos_termografia = [("Paneles", "25 - 65 °C")]

for i in range(1, int(num_inversores) + 1):
    nombre_inv = f"Inversor {i}" if num_inversores > 1 else "Inversor"
    elementos_termografia.append((nombre_inv, "25 - 60 °C"))

for i in range(1, int(num_itms) + 1):
    nombre_itm = f"ITM {i}" if num_itms > 1 else "ITM"
    elementos_termografia.append((nombre_itm, "< 60 °C"))

elementos_termografia.append(("Bloques de distribución", "< 60 °C"))

# Diccionario opcional para almacenar imágenes capturadas
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

    # 3. Rango de Operación (Fijo, solo lectura)
    with c3:
        st.markdown(f"{rango_defecto}")

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
        'criterio': rango_defecto,
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
