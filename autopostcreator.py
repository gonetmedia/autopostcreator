import requests
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, UnidentifiedImageError
from io import BytesIO
import re
import textwrap
import zipfile
import os
import streamlit as st
import tempfile
import html

# Metni belirli genişlikte satırlara böler ve temizler
def wrap_text(text, width):
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text)
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[^;]+;', '', text)
    text = ' '.join(text.split())
    lines = textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=True)
    return '\n'.join(lines)

# Sidebar - Yardım Bilgileri
with st.sidebar:
    st.header("📌 Kullanım Kılavuzu")
    st.markdown("""
    ### 1️⃣ RSS ve Temel Ayarlar
    - RSS adresinizi girin
    - İstediğiniz post sayısını seçin
    
    ### 2️⃣ Font Ayarları
    - TTF formatında font dosyası yükleyin
    - Başlık ve açıklama boyutlarını ayarlayın
    
    ### 3️⃣ Logo Ayarları
    - PNG formatında logo yükleyin
    - Logo konumunu seçin
    
    ### 4️⃣ Görsel Efektleri
    - Parlaklık, kontrast ayarlayın
    - Efekt filtreleri uygulayın
    
    ### 5️⃣ Renk Ayarları
    - Başlık ve açıklama renkleri
    - Arka plan renkleri
    
    ### ❗ Önemli Notlar
    - Yüksek kaliteli görseller kullanın
    - Font dosyası yüklenmesi zorunludur
    - Logo dosyası yüklenmesi zorunludur
    - Görsel boyutu otomatik 1080x1080 olarak ayarlanır
    """)

# Ana sayfa düzeni
st.title("AUTO POST CREATOR")

# RSS ve XML Ayarları
st.header("📰 RSS ve XML Ayarları")
col1, col2 = st.columns(2)
with col1:
    rss_url = st.text_input("RSS adresini girin:")
with col2:
    news_count = st.number_input("Post sayısı:", min_value=1, step=1)

# XML Dosyası Ayarları
st.header("📂 XML Dosyası Ayarları")
uploaded_xml = st.file_uploader("XML dosyası yükleyin:", type=["xml"])

# Font Ayarları
st.header("🔤 Font Ayarları")
col3, col4 = st.columns(2)
with col3:
    uploaded_font = st.file_uploader("Font dosyası (TTF):", type="ttf")
with col4:
    font_size_title = st.slider("Başlık Boyutu", 20, 50, 35)
    font_size_description = st.slider("Açıklama Boyutu", 15, 40, 25)

# Logo Ayarları
st.header("🖼️ Logo Ayarları")
col5, col6 = st.columns(2)
with col5:
    uploaded_logo = st.file_uploader("Logo dosyası:", type=["png", "jpg", "jpeg"])
with col6:
    logo_position = st.selectbox("Logo Konumu", ["Sol Üst", "Sağ Üst"])

# Metin Konumları
st.header("📝 Metin Konumları")
col7, col8 = st.columns(2)
with col7:
    title_position = st.selectbox("Başlık Konumu", ["Sol", "Sağ"])
with col8:
    description_position = st.selectbox("Açıklama Konumu", ["Sol", "Sağ"])

# Renk Seçiciler
st.header("🎨 Renk Ayarları")
col9, col10, col11 = st.columns(3)
with col9:
    title_bg_color = st.color_picker("Başlık Arka Plan", "#006B6B")
    title_text_color = st.color_picker("Başlık Metin", "#FFFFFF")
with col10:
    desc_bg_color = st.color_picker("Açıklama Arka Plan", "#FFFFFF")
    desc_text_color = st.color_picker("Açıklama Metin", "#000000")
with col11:
    overlay_opacity = st.slider("Arka Plan Opaklığı", 0.0, 1.0, 0.9)

# Görsel Efektleri
st.header("✨ Görsel Efektleri")
col12, col13, col14 = st.columns(3)
with col12:
    brightness = st.slider("Parlaklık", 0.5, 2.0, 1.0, 0.1)
    contrast = st.slider("Kontrast", 0.5, 2.0, 1.0, 0.1)
with col13:
    sharpness = st.slider("Keskinlik", 0.0, 2.0, 1.0, 0.1)
with col14:
    effect_filter = st.selectbox("Efekt Filtresi", 
                                ["Yok", "Blur", "Contour", "Edge Enhance", "Emboss", "Smooth"])

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def fetch_rss_data(rss_url, num_items):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(rss_url, headers=headers)
    rss_content = response.text

    root = ET.fromstring(rss_content)
    items = root.findall('.//item')
    news_data = []

    for item in items[:num_items]:
        title = item.find('.//title').text if item.find('.//title') is not None else 'Başlık Yok'
        description = item.find('.//description').text if item.find('.//description') is not None else 'Açıklama Yok'
        
        image_url = None
        for tag in ['image', 'imageUrl', './/media:content', './/enclosure']:
            if tag.startswith('.//'):
                elem = item.find(tag, namespaces={'media': 'http://search.yahoo.com/mrss/'})
                if elem is not None:
                    image_url = elem.get('url')
                    break
            else:
                elem = item.find(f'.//{tag}')
                if elem is not None and elem.text:
                    image_url = elem.text
                    break

        news_data.append((title, description, image_url))

    return news_data

def parse_xml_file(xml_file):
    root = ET.fromstring(xml_file.read())
    items = root.findall('.//item')
    news_data = []
    
    for item in items:
        title = item.find('.//title').text if item.find('.//title') is not None else 'Başlık Yok'
        description = item.find('.//description').text if item.find('.//description') is not None else 'Açıklama Yok'
        
        # Resim URL'lerini alma
        image_url = None
        
        # 1. Yöntem: enclosure tag'inden alma
        enclosure = item.find('.//enclosure')
        if enclosure is not None:
            image_url = enclosure.get('url')

        # 2. Yöntem: wp:attachment tag'inden alma
        if image_url is None:
            attachment = item.find('.//wp:attachment/guid', namespaces={"wp": "http://wordpress.org/export/1.2/"} )
            if attachment is not None:
                image_url = attachment.text

        # 3. Yöntem: wp:postmeta tag'inden alma
        if image_url is None:
            meta_value = item.find('.//wp:postmeta/wp:meta_value', namespaces={"wp": "http://wordpress.org/export/1.2/"})
            if meta_value is not None:
                image_url = meta_value.text

        news_data.append((title, description, image_url))
    
    return news_data

def apply_image_effects(img):
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(brightness)
    
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(sharpness)
    
    if effect_filter == "Blur":
        img = img.filter(ImageFilter.BLUR)
    elif effect_filter == "Contour":
        img = img.filter(ImageFilter.CONTOUR)
    elif effect_filter == "Edge Enhance":
        img = img.filter(ImageFilter.EDGE_ENHANCE)
    elif effect_filter == "Emboss":
        img = img.filter(ImageFilter.EMBOSS)
    elif effect_filter == "Smooth":
        img = img.filter(ImageFilter.SMOOTH)
    
    return img

# Verileri çek
data = []
if uploaded_xml:
    data = parse_xml_file(uploaded_xml)
elif rss_url and news_count and uploaded_font:
    data = fetch_rss_data(rss_url, news_count)

# Özelleştirilmiş açıklamalar için bir liste oluştur
customized_descriptions = []
if data:  # Veriye sahipse
    for index, row in enumerate(data):
        title, description, image_url = row
        # Kullanıcıdan özelleştirilmiş bir açıklama girmesini isteyin
        custom_description = st.text_area(f"Özelleştirilmiş Açıklama {index + 1}:", value=description)
        customized_descriptions.append((title, custom_description, image_url))
    
    df = pd.DataFrame(customized_descriptions, columns=['Title', 'Description', 'Image URL'])
else:
    df = pd.DataFrame(columns=['Title', 'Description', 'Image URL'])

# Font yükleme
try:
    temp_dir = tempfile.mkdtemp()
    font_path = os.path.join(temp_dir, "temp_font.ttf")
    
    if uploaded_font:
        with open(font_path, "wb") as f:
            f.write(uploaded_font.getvalue())
    
    title_font = ImageFont.truetype(font_path, font_size_title)
    description_font = ImageFont.truetype(font_path, font_size_description)
    
except Exception as e:
    st.error(f"Font yükleme hatası: {e}")
    st.stop()

def create_post(title, description, img_url, output_folder):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    default_image_url = "https://dummyimage.com/1080x1350/000/fff&text=Placeholder"

    try:
        response = requests.get(img_url if img_url else default_image_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        if "image" not in response.headers.get("Content-Type", ""):
            response = requests.get(default_image_url, headers=headers, timeout=10)
    except Exception:
        response = requests.get(default_image_url, headers=headers, timeout=10)

    try:
        img = Image.open(BytesIO(response.content))
    except UnidentifiedImageError:
        return None

    img = img.convert('RGB')
    img = img.resize((1080, 1350), Image.Resampling.LANCZOS)  # Boyut değişikliği burada yapıldı
    
    img = apply_image_effects(img)
    
    draw = ImageDraw.Draw(img)

    title = wrap_text(title, 50).upper()
    description = wrap_text(description, 80).upper()

    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    description_bbox = draw.textbbox((0, 0), description, font=description_font)

    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]
    description_width = description_bbox[2] - description_bbox[0]
    description_height = description_bbox[3] - description_bbox[1]

    title_x = 30 if title_position == "Sol" else 1080 - title_width - 30
    description_x = 30 if description_position == "Sol" else 1080 - description_width - 30

    total_height = title_height + description_height
    title_y = (1350 - total_height) / 2 + 350  # Bu hesaplama ile uyumlu hale getiriliyor
    description_y = title_y + title_height + 100

    title_bg = (*hex_to_rgb(title_bg_color), int(255 * overlay_opacity))
    desc_bg = (*hex_to_rgb(desc_bg_color), int(255 * overlay_opacity))
    
    overlay = Image.new('RGBA', (1080, 1350), (0, 0, 0, 0))  # Yüksekliğin güncellenmesi
    draw_overlay = ImageDraw.Draw(overlay)
    
    draw_overlay.rectangle([title_x - 20, title_y - 20, title_width + title_x + 20, title_y + title_height + 20], 
                         fill=title_bg)
    draw_overlay.rectangle([description_x - 20, description_y - 20, description_width + description_x + 20, 
                          description_y + description_height + 20], fill=desc_bg)
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay)
    img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    draw.text((title_x, title_y), title, font=title_font, fill=title_text_color)
    draw.text((description_x, description_y), description, font=description_font, fill=desc_text_color)

    if uploaded_logo:
        logo = Image.open(uploaded_logo)
        logo = logo.convert('RGBA')
        logo = logo.resize((120, 120))
        logo_x = 30 if logo_position == "Sol Üst" else 1080 - 150
        img.paste(logo, (logo_x, 30), logo)

    safe_title = re.sub(r'[^\w\-_\. ]', '_', title[:10])
    post_filename = os.path.join(output_folder, f"post_{safe_title}.jpg")
    img.save(post_filename, quality=95)
    
    return post_filename

if st.button("Gönderi Oluştur ve İndir"):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    output_folder = "posts"
    os.makedirs(output_folder, exist_ok=True)

    zip_filename = "posts.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        total_items = len(df)
        for index, row in df.iterrows():
            try:
                status_text.text(f"İşleniyor: {index + 1}/{total_items}")
                progress_bar.progress((index + 1) / total_items)
                
                post_filename = create_post(row['Title'], row['Description'], row['Image URL'], output_folder)
                if post_filename:
                    zipf.write(post_filename, os.path.basename(post_filename))
                    os.remove(post_filename)
            except Exception as e:
                st.error(f"Hata: {str(e)}")
                continue

    try:
        os.remove(font_path)
        os.rmdir(temp_dir)
    except:
        pass

    progress_bar.progress(100)
    status_text.text("Tamamlandı!")

    with open(zip_filename, "rb") as fp:
        st.download_button(
            label="📥 ZIP Dosyasını İndir",
            data=fp,
            file_name=zip_filename,
            mime="application/zip"
        )
