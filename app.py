
import io
import re
import time
from urllib.parse import urlparse

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="Lead Generator Bot", page_icon="🎯", layout="wide")

st.title("🎯 Lead Generator Bot")
st.caption("Поиск потенциальных бизнес-клиентов и сбор публичных деловых контактов")

st.info(
    "Первая версия: поиск через OpenStreetMap. "
    "ScrapeGraphAI подключим следующим этапом."
)

with st.sidebar:
    st.header("Настройки поиска")
    niche = st.text_input("Тип бизнеса", "restaurant")
    city = st.text_input("Город", "Wroclaw")
    country = st.text_input("Страна", "Poland")
    limit = st.slider("Количество компаний", 5, 50, 10)

def search_businesses(niche, city, country, limit):
    query = f"{niche} in {city}, {country}"
    endpoint = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": limit,
    }
    headers = {"User-Agent": "LeadGeneratorBot/0.1 (personal research)"}

    response = requests.get(
        endpoint, params=params, headers=headers, timeout=30
    )
    response.raise_for_status()
    return response.json()

def extract_website(url):
    if not url or not url.startswith(("http://", "https://")):
        return {"email": "", "phone": ""}
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        emails = re.findall(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text + " " + str(soup),
        )
        phones = re.findall(
            r"(?:\+?\d[\d\s()./-]{7,}\d)",
            text,
        )

        return {
            "email": emails[0] if emails else "",
            "phone": phones[0].strip() if phones else "",
        }
    except requests.RequestException:
        return {"email": "", "phone": ""}

def build_leads(places):
    leads = []
    progress = st.progress(0)
    status = st.empty()

    for i, place in enumerate(places):
        address = place.get("address", {})
        website = place.get("website", "")
        contact = extract_website(website)

        leads.append({
            "company": place.get("name", ""),
            "category": place.get("type", ""),
            "website": website,
            "email": contact["email"],
            "phone": contact["phone"],
            "address": place.get("display_name", ""),
            "city": address.get("city", address.get("town", city)),
            "country": address.get("country", country),
            "latitude": place.get("lat", ""),
            "longitude": place.get("lon", ""),
            "source_url": (
                "https://www.openstreetmap.org/"
                f"?mlat={place.get('lat', '')}"
                f"&mlon={place.get('lon', '')}"
            ),
        })

        progress.progress((i + 1) / len(places))
        status.write(f"Обработано: {i + 1} из {len(places)}")
        time.sleep(1)

    return pd.DataFrame(leads)

if "leads" not in st.session_state:
    st.session_state.leads = pd.DataFrame()

if st.button("🔎 Найти компании", type="primary"):
    try:
        with st.spinner("Ищем компании..."):
            places = search_businesses(niche, city, country, limit)

        if not places:
            st.warning(
                "Ничего не найдено. Попробуй другой запрос или город."
            )
        else:
            st.session_state.leads = build_leads(places)
            st.success(f"Найдено компаний: {len(places)}")
    except requests.RequestException as error:
        st.error(f"Ошибка поиска: {error}")

if not st.session_state.leads.empty:
    st.subheader("Результаты поиска")

    leads = st.session_state.leads
    st.dataframe(leads, use_container_width=True, hide_index=True)

    csv_data = leads.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Скачать таблицу CSV",
        data=csv_data,
        file_name="leads.csv",
        mime="text/csv",
    )

    st.caption(
        "Пустые контакты означают, что их не удалось обнаружить. "
        "Найденные данные могут требовать проверки."
    )
