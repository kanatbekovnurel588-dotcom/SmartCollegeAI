
import io
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SmartCollege AI",
    page_icon="📊",
    layout="wide",
)

# Подключение отдельного CSS
css_path = Path(__file__).with_name("style.css")
if css_path.exists():
    st.markdown(
        f"<style>{css_path.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )
else:
    st.warning("Файл style.css не найден. Создай его рядом с app.py.")


def money(value):
    return f"{value:,.0f} сом".replace(",", " ")


def load_csv(file):
    errors = []

    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        for separator in (None, ";", ",", "\t"):
            try:
                df = pd.read_csv(
                    io.BytesIO(file.getvalue()),
                    encoding=encoding,
                    sep=separator,
                    engine="python",
                )
                if len(df.columns) > 1:
                    return df
            except Exception as error:
                errors.append(str(error))

    raise ValueError("Не удалось прочитать CSV. Проверь разделитель и кодировку.")


def prepare_data(source):
    df = source.copy()
    df.columns = [str(c).strip() for c in df.columns]

    aliases = {
        "категория": "Категория",
        "category": "Категория",
        "сумма": "Сумма",
        "расход": "Сумма",
        "расходы": "Сумма",
        "amount": "Сумма",
        "expenses": "Сумма",
        "прошлый месяц": "Прошлый месяц",
        "предыдущий месяц": "Прошлый месяц",
        "previous month": "Прошлый месяц",
        "previous_month": "Прошлый месяц",
    }

    rename = {}
    for column in df.columns:
        key = str(column).strip().lower().replace("ё", "е")
        if key in aliases:
            rename[column] = aliases[key]

    df = df.rename(columns=rename)

    if "Категория" not in df.columns or "Сумма" not in df.columns:
        raise ValueError(
            "В CSV нужны колонки «Категория» и «Сумма»."
        )

    for column in ("Сумма", "Прошлый месяц"):
        if column in df.columns:
            values = (
                df[column].astype(str)
                .str.replace("\u00a0", "", regex=False)
                .str.replace(" ", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[column] = pd.to_numeric(values, errors="coerce")

    df = df.dropna(subset=["Сумма"])
    df["Категория"] = df["Категория"].astype(str).str.strip()
    df = df[df["Категория"] != ""]
    df["Сумма"] = df["Сумма"].clip(lower=0)

    if "Прошлый месяц" in df.columns:
        df["Прошлый месяц"] = df["Прошлый месяц"].clip(lower=0)

    if df.empty:
        raise ValueError("В файле нет корректных данных о расходах.")

    return df


def aggregate_data(df):
    columns = {"Сумма": "sum"}
    if "Прошлый месяц" in df.columns:
        columns["Прошлый месяц"] = "sum"

    return (
        df.groupby("Категория", as_index=False)
        .agg(columns)
        .sort_values("Сумма", ascending=False)
    )


def find_warnings(df):
    result = []

    if "Прошлый месяц" not in df.columns:
        return result

    for _, row in df.iterrows():
        previous = row["Прошлый месяц"]
        current = row["Сумма"]

        if pd.isna(previous) or previous <= 0:
            continue

        growth = (current - previous) / previous * 100

        if growth >= 20:
            result.append({
                "Категория": row["Категория"],
                "Прошлый месяц": previous,
                "Сумма": current,
                "Рост, %": round(growth, 1),
            })

    return sorted(result, key=lambda x: x["Рост, %"], reverse=True)


def make_recommendations(df, target_percent):
    if df.empty or df["Сумма"].sum() <= 0:
        return ["Добавь расходы, чтобы получить рекомендации."]

    total = df["Сумма"].sum()
    biggest = df.sort_values("Сумма", ascending=False).iloc[0]
    share = biggest["Сумма"] / total * 100
    target = total * target_percent / 100

    result = [
        f"Начни анализ с категории «{biggest['Категория']}»: "
        f"она составляет {share:.1f}% всех расходов.",
        f"Цель экономии {target_percent}% — примерно {money(target)}.",
        "Сравни цены поставщиков и проверь повторяющиеся закупки.",
    ]

    warnings = find_warnings(df)
    if warnings:
        names = ", ".join(x["Категория"] for x in warnings[:3])
        result.append(f"Проверь рост расходов в категориях: {names}.")
    elif "Прошлый месяц" in df.columns:
        result.append("Рост на 20% и более не обнаружен по доступным данным.")

    return result


# БОКОВАЯ ПАНЕЛЬ
with st.sidebar:
    st.markdown(
        "<div class='hero-tag'>SMARTCOLLEGE AI</div>",
        unsafe_allow_html=True,
    )
    st.title("Панель управления")
    st.caption("Контроль бюджета колледжа")
    st.divider()

    st.subheader("Ручной ввод")
    electricity = st.number_input(
        "Электричество — этот месяц", min_value=0.0,
        value=15000.0, step=500.0,
    )
    electricity_prev = st.number_input(
        "Электричество — прошлый месяц", min_value=0.0,
        value=12000.0, step=500.0,
    )
    supplies = st.number_input(
        "Канцелярия — этот месяц", min_value=0.0,
        value=5000.0, step=500.0,
    )
    supplies_prev = st.number_input(
        "Канцелярия — прошлый месяц", min_value=0.0,
        value=4500.0, step=500.0,
    )
    other = st.number_input(
        "Прочие расходы — этот месяц", min_value=0.0,
        value=8000.0, step=500.0,
    )
    other_prev = st.number_input(
        "Прочие расходы — прошлый месяц", min_value=0.0,
        value=7000.0, step=500.0,
    )

    target_percent = st.slider(
        "Цель экономии (%)", 0, 50, 10, step=5
    )

manual_df = pd.DataFrame({
    "Категория": ["Электричество", "Канцелярия", "Прочие расходы"],
    "Сумма": [electricity, supplies, other],
    "Прошлый месяц": [electricity_prev, supplies_prev, other_prev],
})

# ЗАГОЛОВОК
st.markdown("""
<div class="hero">
    <div class="hero-tag">FINANCIAL INTELLIGENCE</div>
    <div class="hero-title">SmartCollege AI</div>
    <div class="hero-subtitle">
        Анализируй расходы колледжа, находи отклонения
        и планируй экономию бюджета.
    </div>
</div>
""", unsafe_allow_html=True)

# ЗАГРУЗКА CSV
with st.expander("📂 Загрузить расходы из CSV"):
    uploaded_file = st.file_uploader(
        "Выбери CSV-файл",
        type=["csv"],
        help="Обязательные колонки: Категория, Сумма. "
             "Для сравнения добавь Прошлый месяц.",
    )

    if uploaded_file is not None:
        try:
            imported = prepare_data(load_csv(uploaded_file))
            st.session_state["imported_df"] = aggregate_data(imported)
            st.success("Данные успешно загружены.")
        except Exception as error:
            st.error(str(error))

if "imported_df" in st.session_state:
    df = st.session_state["imported_df"].copy()
    source_name = "CSV-файл"
else:
    df = manual_df.copy()
    source_name = "Ручной ввод"

df["Сумма"] = df["Сумма"].fillna(0)
total = float(df["Сумма"].sum())
has_previous = "Прошлый месяц" in df.columns

if has_previous:
    df["Прошлый месяц"] = df["Прошлый месяц"].fillna(0)
    previous_total = float(df["Прошлый месяц"].sum())
else:
    previous_total = 0

change = (
    (total - previous_total) / previous_total * 100
    if has_previous and previous_total > 0 else None
)

target_saving = total * target_percent / 100
warnings = find_warnings(df)
recommendations = make_recommendations(df, target_percent)

overview, csv_tab, warning_tab, recommendations_tab = st.tabs([
    "◈ Обзор", "▤ Анализ CSV", "⚠ Предупреждения", "✳ Рекомендации"
])

# ОБЗОР
with overview:
    st.markdown(
        '<div class="section-title">Ключевые показатели</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Источник данных: {source_name}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Общие расходы", money(total))
    c2.metric(
        "К прошлому месяцу",
        f"{change:+.1f}%" if change is not None else "Нет данных",
    )
    c3.metric("Цель экономии", money(target_saving))
    c4.metric("Категорий", len(df))

    st.markdown(
        '<div class="section-title">Структура расходов</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.5, 1])

    with left:
        if total > 0:
            st.bar_chart(
                df.set_index("Категория")[["Сумма"]],
                color="#83e7f5",
                height=340,
            )
        else:
            st.info("Добавь расходы, чтобы увидеть график.")

    with right:
        st.markdown("#### Расходы по категориям")
        shown = df.copy()
        shown["Сумма"] = shown["Сумма"].apply(money)
        if has_previous:
            shown["Прошлый месяц"] = shown["Прошлый месяц"].apply(money)
        st.dataframe(shown, use_container_width=True, hide_index=True)

    st.markdown("#### Цель экономии")
    st.progress(target_percent / 100)
    st.caption(
        f"План: сократить расходы на {target_percent}% "
        f"или на {money(target_saving)}."
    )

# АНАЛИЗ CSV
with csv_tab:
    st.subheader("Подробный анализ")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if has_previous:
        comparison = df.copy()
        comparison["Изменение"] = (
            comparison["Сумма"] - comparison["Прошлый месяц"]
        )
        comparison["Изменение, %"] = comparison.apply(
            lambda row: (
                (row["Сумма"] - row["Прошлый месяц"])
                / row["Прошлый месяц"] * 100
                if row["Прошлый месяц"] > 0 else None
            ),
            axis=1,
        )
        st.markdown("#### Сравнение месяцев")
        st.dataframe(comparison, use_container_width=True, hide_index=True)
    else:
        st.info("Добавь колонку «Прошлый месяц» для сравнения.")

    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇ Скачать отчёт CSV",
        data=buffer.getvalue(),
        file_name="smartcollege_report.csv",
        mime="text/csv",
    )

# ПРЕДУПРЕЖДЕНИЯ
with warning_tab:
    st.subheader("Рост расходов")

    if not has_previous:
        st.info("Нет данных за прошлый месяц.")
    elif not warnings:
        st.success("Категорий с ростом расходов на 20% и более не найдено.")
    else:
        for item in warnings:
            st.markdown(
                f"""
                <div class="info-card">
                    <div class="info-title">⚠ {item['Категория']}</div>
                    <div class="info-text">
                        Было: {money(item['Прошлый месяц'])}<br>
                        Стало: {money(item['Сумма'])}<br>
                        Рост: <b>+{item['Рост, %']}%</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# РЕКОМЕНДАЦИИ
with recommendations_tab:
    st.subheader("Рекомендации по экономии")

    for i, recommendation in enumerate(recommendations, start=1):
        st.markdown(
            f"""
            <div class="info-card">
                <div class="info-title">Рекомендация {i:02d}</div>
                <div class="info-text">{recommendation}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.metric("Целевое сокращение расходов", money(target_saving))
    st.caption(
        "Рекомендации основаны на правилах и введённых данных; "
        "это прототип аналитики, а не обученная модель ИИ."
    )

st.divider()
st.caption("SMARTCOLLEGE AI · Прототип аналитики бюджета колледжа")
