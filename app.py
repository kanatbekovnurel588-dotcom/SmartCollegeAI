import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="SmartCollege AI",
    page_icon="🎓",
    layout="wide"
)

# ОФОРМЛЕНИЕ
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        padding: 18px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# НАСТРОЙКИ
st.sidebar.title("⚙️ Настройки")
st.sidebar.caption("Расходы колледжа за текущий месяц")

electricity = st.sidebar.number_input(
    "Электроэнергия (сом)", min_value=0, value=30000, step=1000
)
supplies = st.sidebar.number_input(
    "Канцелярия и материалы (сом)", min_value=0, value=12000, step=1000
)
other = st.sidebar.number_input(
    "Прочие расходы (сом)", min_value=0, value=20000, step=1000
)
previous_total = st.sidebar.number_input(
    "Все расходы прошлого месяца (сом)",
    min_value=0, value=65000, step=1000
)
goal = st.sidebar.slider("Цель экономии (%)", 1, 30, 10)

# РАСЧЁТЫ
expenses = pd.DataFrame({
    "Категория": [
        "Электроэнергия",
        "Канцелярия и материалы",
        "Прочие расходы"
    ],
    "Сумма": [electricity, supplies, other]
})

total = int(expenses["Сумма"].sum())
difference = total - previous_total
saving = round(total * goal / 100)
new_total = total - saving

# ЗАГОЛОВОК
st.title("🎓 SmartCollege AI")
st.write("Аналитика расходов колледжа и поиск возможностей экономии.")
st.divider()

# ОСНОВНЫЕ ПОКАЗАТЕЛИ
st.subheader("📊 Финансовый обзор")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Расходы за месяц",
    f"{total:,.0f} сом".replace(",", " ")
)
col2.metric(
    "Прошлый месяц",
    f"{previous_total:,.0f} сом".replace(",", " ")
)
col3.metric(
    "Изменение расходов",
    f"{difference:+,.0f} сом".replace(",", " "),
    delta=f"{difference:+,.0f} сом".replace(",", " "),
    delta_color="inverse"
)
col4.metric(
    f"Цель экономии ({goal}%)",
    f"{saving:,.0f} сом".replace(",", " ")
)

overview_tab, csv_tab, alerts_tab, recommendations_tab = st.tabs([
    "📈 Обзор",
    "📂 Анализ CSV",
    "⚠️ Предупреждения",
    "💡 Рекомендации"
])

# ОБЗОР
with overview_tab:
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Расходы по категориям")
        st.bar_chart(expenses.set_index("Категория"))

    with right:
        st.subheader("Сценарий экономии")
        st.metric(
            "Возможная экономия",
            f"{saving:,.0f} сом".replace(",", " ")
        )
        st.metric(
            "Расходы после экономии",
            f"{new_total:,.0f} сом".replace(",", " ")
        )

        if total > 0:
            largest = expenses.loc[expenses["Сумма"].idxmax()]
            st.info(
                f"Самая затратная категория: **{largest['Категория']}** "
                f"({largest['Сумма']:,.0f} сом)".replace(",", " ")
            )

    st.caption(
        "Сценарий экономии — расчётная оценка, а не гарантированный результат."
    )

# АНАЛИЗ CSV
with csv_tab:
    st.subheader("Анализ расходов из файла")
    st.write(
        "Загрузи CSV с колонками «Категория» и «Сумма». "
        "Для сравнения добавь колонку «Прошлый месяц»."
    )

    uploaded_file = st.file_uploader(
        "Выбери CSV-файл",
        type=["csv"],
        key="expense_csv"
    )

    if uploaded_file is not None:
        try:
            # ЧТЕНИЕ CSV
            try:
                df = pd.read_csv(
                    uploaded_file,
                    encoding="utf-8-sig",
                    sep=None,
                    engine="python"
                )
            except (pd.errors.ParserError, pd.errors.EmptyDataError):
                uploaded_file.seek(0)
                df = pd.read_csv(
                    uploaded_file,
                    encoding="utf-8-sig",
                    sep=","
                )

            # ОЧИСТКА НАЗВАНИЙ
            df.columns = (
                df.columns.astype(str)
                .str.replace("\ufeff", "", regex=False)
                .str.strip()
            )

            # ПРОВЕРКА КОЛОНОК
            required = {"Категория", "Сумма"}

            if not required.issubset(df.columns):
                st.error(
                    "Нужны колонки «Категория» и «Сумма». "
                    "Проверь разделитель и названия столбцов в CSV."
                )
                st.write("Найденные колонки:", df.columns.tolist())

            else:
                # ОЧИСТКА ДАННЫХ
                df["Категория"] = df["Категория"].astype(str).str.strip()
                df["Сумма"] = pd.to_numeric(df["Сумма"], errors="coerce")
                df = df.dropna(subset=["Сумма"])
                df = df[df["Категория"] != ""]

                if "Прошлый месяц" in df.columns:
                    df["Прошлый месяц"] = pd.to_numeric(
                        df["Прошлый месяц"], errors="coerce"
                    )

                if df.empty:
                    st.warning("В файле нет корректных данных.")

                else:
                    # ГРУППИРОВКА ДАННЫХ
                    aggregations = {"Сумма": "sum"}

                    if "Прошлый месяц" in df.columns:
                        aggregations["Прошлый месяц"] = "sum"

                    grouped = (
                        df.groupby("Категория", as_index=False)
                        .agg(aggregations)
                        .sort_values("Сумма", ascending=False)
                    )

                    csv_total = grouped["Сумма"].sum()

                    # ОСНОВНЫЕ ПОКАЗАТЕЛИ CSV
                    m1, m2, m3 = st.columns(3)

                    m1.metric(
                        "Текущие расходы",
                        f"{csv_total:,.0f} сом".replace(",", " ")
                    )
                    m2.metric("Категорий", len(grouped))
                    m3.metric(
                        "Средние расходы на категорию",
                        f"{grouped['Сумма'].mean():,.0f} сом".replace(",", " ")
                    )

                    # ГРАФИК
                    st.subheader("Распределение расходов")
                    st.bar_chart(grouped.set_index("Категория")["Сумма"])

                    # СРАВНЕНИЕ МЕСЯЦЕВ
                    if "Прошлый месяц" in grouped.columns:
                        grouped["Разница"] = (
                            grouped["Сумма"] - grouped["Прошлый месяц"]
                        )

                        def calculate_change(row):
                            previous = row["Прошлый месяц"]
                            current = row["Сумма"]

                            if pd.isna(previous):
                                return float("nan")
                            if previous == 0 and current > 0:
                                return float("inf")
                            if previous == 0 and current == 0:
                                return 0.0

                            return (current - previous) / previous * 100

                        grouped["Изменение (%)"] = grouped.apply(
                            calculate_change,
                            axis=1
                        )

                        st.subheader("Сравнение с прошлым месяцем")

                        display_table = grouped.copy()
                        display_table["Изменение (%)"] = (
                            display_table["Изменение (%)"].map(
                                lambda value: (
                                    "Новая статья"
                                    if value == float("inf")
                                    else (
                                        "Нет данных"
                                        if pd.isna(value)
                                        else f"{value:+.1f}%"
                                    )
                                )
                            )
                        )

                        st.dataframe(
                            display_table,
                            use_container_width=True,
                            hide_index=True
                        )

                        # ПОИСК РОСТА РАСХОДОВ
                        alerts = grouped[
                            (
                                (grouped["Изменение (%)"] >= 20)
                                | (grouped["Изменение (%)"] == float("inf"))
                            )
                            & (grouped["Разница"] > 0)
                        ]

                        st.subheader("⚠️ Результаты проверки")

                        if alerts.empty:
                            st.success(
                                "Категорий с ростом расходов на 20% и более не найдено."
                            )
                        else:
                            for _, row in alerts.iterrows():
                                if row["Изменение (%)"] == float("inf"):
                                    change_text = "новая статья расходов"
                                else:
                                    change_text = (
                                        f"рост на {row['Изменение (%)']:.1f}%"
                                    )

                                st.warning(
                                    f"**{row['Категория']}**: {change_text}. "
                                    f"Разница: {row['Разница']:+,.0f} сом. "
                                    "Рекомендуется проверить причину."
                                    .replace(",", " ")
                                )

                    else:
                        st.info(
                            "Для сравнения месяцев добавь в CSV колонку "
                            "«Прошлый месяц»."
                        )

                    # ЭКСПОРТ ОТЧЁТА
                    csv_report = grouped.to_csv(
                        index=False
                    ).encode("utf-8-sig")

                    st.download_button(
                        "⬇️ Скачать отчёт анализа",
                        data=csv_report,
                        file_name="smartcollege_analysis.csv",
                        mime="text/csv"
                    )

        except Exception as error:
            st.error(f"Не удалось обработать файл: {error}")

# ПРЕДУПРЕЖДЕНИЯ
with alerts_tab:
    st.subheader("Проверка расходов")

    if total == 0:
        st.info("Сначала введи расходы в боковой панели.")

    elif previous_total > 0:
        total_change = (
            (total - previous_total) / previous_total
        ) * 100

        if total_change >= 20:
            st.error(
                f"Общие расходы выросли на {total_change:.1f}% "
                "относительно прошлого месяца. Проверь причины роста."
            )
        elif total_change > 0:
            st.warning(
                f"Общие расходы выросли на {total_change:.1f}%."
            )
        else:
            st.success(
                f"Общие расходы не выросли: изменение {total_change:+.1f}%."
            )

    else:
        st.info(
            "Укажи расходы прошлого месяца, чтобы сравнить показатели."
        )

    st.markdown("#### Категории для проверки")

    for _, row in expenses.sort_values(
        "Сумма", ascending=False
    ).iterrows():
        if row["Сумма"] > 0:
            st.write(
                f"**{row['Категория']}** — "
                f"{row['Сумма']:,.0f} сом".replace(",", " ")
            )

    st.caption(
        "Без данных по каждой категории за прошлый месяц "
        "нельзя определить, какая именно статья вызвала рост."
    )

# РЕКОМЕНДАЦИИ
with recommendations_tab:
    st.subheader("Рекомендации по экономии")

    recommendations = {
        "Электроэнергия": (
            electricity,
            0.05,
            "Проверить освещение и отключение оборудования "
            "в неиспользуемых помещениях."
        ),
        "Канцелярия и материалы": (
            supplies,
            0.05,
            "Проверить складские остатки и планировать закупки "
            "по фактической потребности."
        ),
        "Прочие расходы": (
            other,
            0.03,
            "Разделить расходы по отдельным статьям и проверить "
            "необязательные траты."
        )
    }

    potential_total = 0

    for category, (amount, rate, advice) in recommendations.items():
        potential = round(amount * rate)
        potential_total += potential

        with st.container(border=True):
            st.markdown(f"#### {category}")
            st.write(advice)
            st.caption(
                f"Предварительный сценарий экономии: "
                f"{potential:,.0f} сом".replace(",", " ")
            )

    st.metric(
        "Общая расчётная экономия",
        f"{potential_total:,.0f} сом".replace(",", " ")
    )

    st.caption(
        "Рекомендации основаны на правилах. Проценты условные "
        "и требуют проверки на реальных данных."
    )

# ПОДВАЛ
st.divider()
st.caption(
    "SmartCollege AI · Прототип аналитики бюджета колледжа"
)
