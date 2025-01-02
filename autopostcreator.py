import requests
import xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
import zipfile
import os
from io import BytesIO
import re
import html
import textwrap
import streamlit as st

# RSS'den veri çekme fonksiyonu
def fetch_rss_data(rss_url, num_items):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(rss_url, headers=headers)
    rss_content = response.text

    # RSS XML'ini parse et
    root = ET.fromstring(rss_content)

    items = root.findall('.//item')
    news_data = []

    for item in items[:num_items]:
        title = item.find('.//title').text if item.find('.//title') is not None else 'Başlık Yok'
        description = item.find('.//description').text if item.find('.//description') is not None else 'Açıklama Yok'

        # CDATA etiketlerini temizleme
        description = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', description)
        description = html.unescape(description)

        # Görsel URL'sini alma
        image_url = None
        image_tag = item.find('.//image') or item.find('.//imageUrl') or \
                    item.find('.//media:content', namespaces={'media': 'http://search.yahoo.com/mrss/'}) or \
                    item.find('.//enclosure')

        if image_tag is not None and 'url' in image_tag.attrib:
            image_url = image_tag.attrib['url'] if image_tag.tag == 'enclosure' and 'url' in image_tag.attrib else image_tag.text

        news_data.append((title, description, image_url))

    return news_data

# Görsel oluşturma fonksiyonu
def wrap_text(text, width):
    lines = textwrap.wrap(text, width=width)
    return "\n".join(lines)

def create_post(title, description, img_url, output_folder, title_font, description_font, title_bg_color, description_bg_color, title_text_color, description_text_color, logo, logo_position):
    headers = {'User-Agent': 'Mozilla/5.0'}
    default_image_url = "https://via.placeholder.com/1080"  # Varsayılan bir görsel URL'si

    try:
        response = requests.get(img_url, headers=headers, timeout=10)
        response.raise_for_status()
        if "image" not in response.headers.get("Content-Type", ""):
            response = requests.get(default_image_url, headers=headers, timeout=10)
    except Exception:
        response = requests.get(default_image_url, headers=headers, timeout=10)

    try:
        img = Image.open(BytesIO(response.content))
    except UnidentifiedImageError:
        return None

    img = img.resize((1080, 1080))
    draw = ImageDraw.Draw(img)

    wrapped_title = wrap_text(title, 50).upper()
    wrapped_description = wrap_text(description, 80).upper()

    title_bbox = draw.textbbox((0, 0), wrapped_title, font=title_font)
    description_bbox = draw.textbbox((0, 0), wrapped_description, font=description_font)

    title_width, title_height = title_bbox[2] - title_bbox[0], title_bbox[3] - title_bbox[1]
    description_width, description_height = description_bbox[2] - description_bbox[0], description_bbox[3] - description_bbox[1]

    # Başlık konumunu ayarlama
    title_x = 30 if title_alignment == "Sol" else 1080 - title_width - 30
    description_x = 30 if description_alignment == "Sol" else 1080 - description_width - 30

    total_height = title_height + description_height
    title_y = (1080 - total_height) / 2 + 280
    description_y = title_y + title_height + 70

    # Oval kutular oluşturma
    corner_radius = 20  # Oval köşe yarıçapı
    draw.rounded_rectangle([title_x - 20, title_y - 20, title_width + title_x + 20, title_y + title_height + 20], radius=corner_radius, fill=title_bg_color)
    draw.rounded_rectangle([description_x - 20, description_y - 20, description_width + description_x + 20, description_y + description_height + 20], radius=corner_radius, fill=description_bg_color)

    draw.text((title_x, title_y), wrapped_title, font=title_font, fill=title_text_color)
    draw.text((description_x, description_y), wrapped_description, font=description_font, fill=description_text_color)

    logo_resized = logo.resize((logo_size, logo_size))

    if logo_position == "Sol Üst":
        logo_x, logo_y = 30, 30
    else:  # Sağ Üst
        logo_x, logo_y = 1080 - logo_size - 30, 30

    img.paste(logo_resized, (logo_x, logo_y), logo_resized)

    safe_title = re.sub(r'[^\w\-_\. ]', '_', title[:10])
    post_filename = os.path.join(os.path.dirname(output_folder), f"post_{safe_title}.jpg")

    os.makedirs(os.path.dirname(output_folder), exist_ok=True)
    img.save(post_filename)
    return post_filename

# ZIP dosyasını oluşturma ve indirme fonksiyonu
def create_zip_from_posts(csv_data, output_folder, logo_position):
    with zipfile.ZipFile(output_folder, 'w') as zipf:
        for index, row in csv_data.iterrows():
            title = row['Title']
            description = row['Description']
            img_url = row['Image URL']

            post_filename = create_post(title, description, img_url, output_folder, title_font, description_font, title_bg_color, description_bg_color, title_text_color, description_text_color, logo, logo_position)
            if post_filename:
                zipf.write(post_filename, os.path.basename(post_filename))
                os.remove(post_filename)

# Streamlit UI ile işlemi başlatma
st.title("Auto Post Creator")
rss_url = st.text_input("RSS adresini girin:")
news_count = st.number_input("istediğiniz Post sayısını girin:", min_value=1, step=1)

# Logo konumu ve dosya yükleme
logo_position = st.selectbox("Logonun konumunu seçin:", options=["Sol Üst", "Sağ Üst"])
uploaded_font = st.file_uploader("Yazı fontunu yükleyin (TTF formatında)", type=["ttf"])
uploaded_logo = st.file_uploader("Logo dosyasını yükleyin (PNG formatında)", type=["png", "jpg", "jpeg"])

# Kutu ve metin renkleri
title_bg_color = st.color_picker("Başlık arka plan rengini seçin:", "#009999")
description_bg_color = st.color_picker("Açıklama arka plan rengini seçin:", "#FFFFFF")
title_text_color = st.color_picker("Başlık metni rengini seçin:", "#FFFFFF")
description_text_color = st.color_picker("Açıklama metni rengini seçin:", "#000000")

# Font boyutlarını ayarlama
title_font_size = st.number_input("Başlık font boyutunu ayarlayın:", min_value=10, max_value=100, value=35)
description_font_size = st.number_input("Açıklama font boyutunu ayarlayın:", min_value=10, max_value=100, value=25)

# Metin konumu ayarlama için seçim aracı
title_alignment = st.selectbox("Başlık konumunu seçin:", options=["Sol", "Sağ"])
description_alignment = st.selectbox("Açıklama konumunu seçin:", options=["Sol", "Sağ"])

# Logo boyutunu sabit olarak belirleme
logo_size = 150  # Logo boyutu: 150x150

# Yardım Dokümanları
st.sidebar.header("Yardım")
st.sidebar.write("""
Uygulama Rehberi:
- RSS adresi girin ve kaç post oluşturmak istediğinizi seçin.
- Logo ve font dosyalarınızı yükleyin.
- Başlık / açıklama konumlarını ve renklerini ayarlayın.
- En uygun FONT "Avgardd TTF" fontudur.
- Tercihinize göre farklı fontlar ve font boyutlar deneyerek değişikler yapabilirsiniz.
- "Gönder" butonuna basarak gerekli işlemleri tamamlayın.
""")

if st.button('Gönder'):
    if rss_url and uploaded_font and uploaded_logo:
        # ZIP dosyası için dizini belirleme
        zip_dir = os.path.join(os.path.expanduser("~"), "Desktop", "post")
        os.makedirs(zip_dir, exist_ok=True)  # Dizin yoksa oluştur
        
        # ZIP dosyasının tam yolunu belirleme
        output_zip_path = os.path.join(zip_dir, "posts.zip")

        # RSS verilerini al
        data = fetch_rss_data(rss_url, news_count)
        if data:
            df = pd.DataFrame(data, columns=['Title', 'Description', 'Image URL'])

            # Fontu yükleme
            title_font = None
            description_font = None
            
            if uploaded_font:
                try:
                    font_bytes = uploaded_font.read()
                    title_font = ImageFont.truetype(BytesIO(font_bytes), title_font_size)
                    description_font = ImageFont.truetype(BytesIO(font_bytes), description_font_size)
                except Exception as e:
                    st.error(f"Font yüklenirken bir hata oluştu: {e}")

            # Logo dosyasını yükleme
            logo = None
            if uploaded_logo:
                logo = Image.open(uploaded_logo)

            # ZIP dosyasının oluşturulması
            create_zip_from_posts(df, output_zip_path, logo_position)

            # ZIP dosyasını oku ve akışa yaz
            with open(output_zip_path, 'rb') as f:
                st.download_button("ZIP Dosyasını İndir", data=f, file_name="posts.zip", mime="application/zip")
        else:
            st.error("Hatalı RSS URL veya veri bulunamadı.")
    else:
        st.error("Lütfen tüm alanları doldurun: RSS URL, Font, Logo.")
