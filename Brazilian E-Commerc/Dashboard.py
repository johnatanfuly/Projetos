import math
import os
from datetime import date

import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st


st.set_page_config(
    page_title="Olist | Inteligência de Lucro",
    page_icon="📦",
    layout="wide",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "products": "olist_products_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "translations": "product_category_name_translation.csv",
}
MONEY = "R$ {:,.2f}"
BRAZILIAN_STATES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco",
    "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}
PAYMENT_NAMES = {
    "credit_card": "Cartão de crédito",
    "boleto": "Boleto",
    "voucher": "Vale/voucher",
    "debit_card": "Cartão de débito",
    "not_defined": "Não definido",
}
STATUS_NAMES = {
    "delivered": "Entregue",
    "shipped": "Enviado",
    "canceled": "Cancelado",
    "unavailable": "Indisponível",
    "invoiced": "Faturado",
    "processing": "Em processamento",
    "created": "Criado",
    "approved": "Aprovado",
}


@st.cache_data(show_spinner="Carregando e relacionando os CSVs...")
def load_data():
    customers = pd.read_csv(
        os.path.join(BASE_DIR, CSV_FILES["customers"]),
        dtype={"customer_zip_code_prefix": "string"},
    )
    geo = pd.read_csv(
        os.path.join(BASE_DIR, CSV_FILES["geolocation"]),
        usecols=[
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
        ],
        dtype={"geolocation_zip_code_prefix": "string"},
    )
    geo["geolocation_lat"] = pd.to_numeric(geo["geolocation_lat"], errors="coerce")
    geo["geolocation_lng"] = pd.to_numeric(geo["geolocation_lng"], errors="coerce")
    geo = (
        geo.dropna(subset=["geolocation_lat", "geolocation_lng"])
        .groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(latitude=("geolocation_lat", "mean"), longitude=("geolocation_lng", "mean"))
    )
    customers = customers.merge(
        geo,
        left_on="customer_zip_code_prefix",
        right_on="geolocation_zip_code_prefix",
        how="left",
    )

    orders = pd.read_csv(
        os.path.join(BASE_DIR, CSV_FILES["orders"]),
        parse_dates=[
            "order_purchase_timestamp",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
    )
    orders = orders.merge(
        customers[
            [
                "customer_id",
                "customer_unique_id",
                "customer_city",
                "customer_state",
                "latitude",
                "longitude",
            ]
        ],
        on="customer_id",
        how="left",
    )

    items = pd.read_csv(os.path.join(BASE_DIR, CSV_FILES["items"]))
    sellers = pd.read_csv(
        os.path.join(BASE_DIR, CSV_FILES["sellers"]),
        usecols=["seller_id", "seller_city", "seller_state"],
    )
    products = pd.read_csv(
        os.path.join(BASE_DIR, CSV_FILES["products"]),
        usecols=["product_id", "product_category_name"],
    )
    translations = pd.read_csv(os.path.join(BASE_DIR, CSV_FILES["translations"]))
    products = products.merge(translations, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna(
        products["product_category_name"]
    )
    products["category"] = products["category"].fillna("Sem categoria")
    items = items.merge(
        products[["product_id", "category"]], on="product_id", how="left"
    )
    items = items.merge(sellers, on="seller_id", how="left")
    items["category"] = items["category"].fillna("Sem categoria")
    items_by_order = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_revenue=("price", "sum"),
            freight_value=("freight_value", "sum"),
            item_count=("order_item_id", "count"),
        )
    )
    payments = pd.read_csv(os.path.join(BASE_DIR, CSV_FILES["payments"]))
    payments_by_order = payments.groupby("order_id", as_index=False).agg(
        paid_value=("payment_value", "sum")
    )
    payment_mix = (
        payments.groupby(["order_id", "payment_type"], as_index=False)
        .agg(payment_value=("payment_value", "sum"))
    )
    reviews = pd.read_csv(
        os.path.join(BASE_DIR, CSV_FILES["reviews"]),
        usecols=["order_id", "review_score"],
    )
    reviews["review_score"] = pd.to_numeric(reviews["review_score"], errors="coerce")
    reviews_by_order = reviews.groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean")
    )

    orders = orders.merge(items_by_order, on="order_id", how="left")
    orders = orders.merge(payments_by_order, on="order_id", how="left")
    orders = orders.merge(reviews_by_order, on="order_id", how="left")
    return orders, items, payment_mix


missing_files = [
    filename
    for filename in CSV_FILES.values()
    if not os.path.exists(os.path.join(BASE_DIR, filename))
]
if missing_files:
    st.error("Arquivos CSV não encontrados: " + ", ".join(missing_files))
    st.stop()

orders, items, payment_mix = load_data()
orders = orders.dropna(subset=["order_purchase_timestamp"]).copy()
orders["purchase_date"] = orders["order_purchase_timestamp"].dt.date
orders["delivery_days"] = (
    orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400
orders["delivery_delay_days"] = (
    orders["order_delivered_customer_date"] - orders["order_estimated_delivery_date"]
).dt.total_seconds() / 86400

st.title("📦 Olist | Inteligência de lucro e entregas")
st.caption(
    "Visão integrada de vendas, produtos, clientes e logística. "
    "O conjunto de dados não contém custos de produto nem nomes de transportadoras; "
    "portanto, faturamento e frete não representam lucro líquido ou custo logístico."
)

with st.sidebar:
    st.header("Filtros")
    date_min = orders["purchase_date"].min()
    date_max = orders["purchase_date"].max()
    date_range = st.date_input(
        "Período do pedido",
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )
    states = sorted(orders["customer_state"].dropna().unique().tolist())
    selected_states = st.multiselect(
        "Estados dos clientes",
        states,
        default=states,
        format_func=lambda state: f"{BRAZILIAN_STATES.get(state, state)} ({state})",
    )
    statuses = sorted(orders["order_status"].dropna().unique().tolist())
    selected_statuses = st.multiselect(
        "Status dos pedidos",
        statuses,
        default=["delivered"] if "delivered" in statuses else statuses,
        format_func=lambda status: STATUS_NAMES.get(status, status.capitalize()),
    )
    st.caption("A seleção se aplica aos indicadores e às análises do dashboard.")

if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date = end_date = date_range

filtered = orders[
    orders["purchase_date"].between(start_date, end_date)
    & orders["customer_state"].isin(selected_states)
    & orders["order_status"].isin(selected_statuses)
].copy()

if filtered.empty:
    st.warning("Não há pedidos para os filtros selecionados.")
    st.stop()

paid_total = filtered["paid_value"].sum()
order_count = filtered["order_id"].nunique()
avg_ticket = paid_total / order_count if order_count else 0
avg_freight = filtered["freight_value"].mean()
freight_ratio = (
    filtered["freight_value"].sum() / filtered["item_revenue"].sum()
    if filtered["item_revenue"].sum()
    else 0
)

metric_cols = st.columns(5)
metric_cols[0].metric("Faturamento recebido", MONEY.format(paid_total))
metric_cols[1].metric("Pedidos", f"{order_count:,}".replace(",", "."))
metric_cols[2].metric("Ticket médio", MONEY.format(avg_ticket))
metric_cols[3].metric(
    "Frete cobrado",
    MONEY.format(filtered["freight_value"].sum()),
)
metric_cols[4].metric("Frete / valor dos itens", f"{freight_ratio:.1%}")

tabs = st.tabs(
    ["Visão executiva", "Produtos e pagamentos", "Clientes e regiões", "Entregas e mapa"]
)

with tabs[0]:
    st.subheader("Evolução do faturamento")
    monthly = (
        filtered.assign(month=filtered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)
        .agg(
            paid_value=("paid_value", "sum"),
            order_count=("order_id", "nunique"),
        )
    )
    if not monthly.empty:
        fig = px.line(
            monthly,
            x="month",
            y="paid_value",
            markers=True,
            labels={"month": "Mês", "paid_value": "Faturamento recebido (R$)"},
            title="Faturamento recebido por mês",
        )
        st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        state_sales = (
            filtered.groupby("customer_state", as_index=False)
            .agg(
                paid_value=("paid_value", "sum"),
                order_count=("order_id", "nunique"),
            )
            .sort_values("paid_value", ascending=False)
        )
        state_sales["state_name"] = state_sales["customer_state"].map(
            lambda state: BRAZILIAN_STATES.get(state, state)
        )
        fig = px.bar(
            state_sales,
            x="state_name",
            y="paid_value",
            labels={"state_name": "Estado", "paid_value": "Faturamento (R$)"},
            title="Faturamento por estado",
            color="paid_value",
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        payment_summary = payment_mix[
            payment_mix["order_id"].isin(filtered["order_id"])
        ].copy()
        payment_summary["payment_name"] = payment_summary["payment_type"].map(
            lambda value: PAYMENT_NAMES.get(value, value)
        )
        payment_summary = payment_summary.groupby(
            "payment_name", as_index=False
        )["payment_value"].sum()
        fig = px.pie(
            payment_summary,
            names="payment_name",
            values="payment_value",
            hole=0.45,
            title="Faturamento recebido por forma de pagamento",
        )
        st.plotly_chart(fig, width="stretch")

    st.subheader("Oportunidades para investigar")
    filtered_items = items[items["order_id"].isin(filtered["order_id"])]
    category_summary = (
        filtered_items.groupby("category", as_index=False)
        .agg(
            item_revenue=("price", "sum"),
            freight_value=("freight_value", "sum"),
            units=("order_item_id", "count"),
        )
        .sort_values("item_revenue", ascending=False)
    )
    insights = []
    if not category_summary.empty:
        top_category = category_summary.iloc[0]
        insights.append(
            f"Categoria com maior faturamento de itens: **{top_category['category']}** "
            f"({MONEY.format(top_category['item_revenue'])}). Avalie disponibilidade "
            "e campanhas antes de ampliar estoque."
        )
        category_summary["freight_ratio"] = (
            category_summary["freight_value"]
            / category_summary["item_revenue"].replace(0, float("nan"))
        )
        expensive_freight = category_summary.dropna(subset=["freight_ratio"]).sort_values(
            "freight_ratio", ascending=False
        )
        if not expensive_freight.empty:
            category = expensive_freight.iloc[0]
            insights.append(
                f"Maior proporção de frete sobre os itens: **{category['category']}** "
                f"({category['freight_ratio']:.1%}). Compare embalagem, regiões atendidas "
                "e opções de envio; o dataset não informa o custo pago à transportadora."
            )
    rated = filtered.dropna(subset=["review_score"])
    if not rated.empty:
        low_rated = rated[rated["review_score"] <= 2]
        if not low_rated.empty:
            late_share = (
                low_rated["delivery_delay_days"].gt(0).mean()
                if low_rated["delivery_delay_days"].notna().any()
                else float("nan")
            )
            if not math.isnan(late_share):
                insights.append(
                    f"Entre pedidos avaliados com nota 1 ou 2, "
                    f"{late_share:.1%} chegaram após a previsão. Investigue prazos "
                    "e ocorrências de entrega; essa associação não comprova causalidade."
                )
    if not insights:
        insights.append(
            "Amplie o período ou a seleção de status para encontrar padrões de "
            "categoria, frete e avaliações."
        )
    for insight in insights:
        st.markdown(f"- {insight}")
    st.info(
        "Para calcular lucro real, complemente os dados com custo dos produtos, "
        "comissões, impostos, devoluções e custo efetivo de frete."
    )

with tabs[1]:
    st.subheader("Desempenho de produtos")
    filtered_items = items[items["order_id"].isin(filtered["order_id"])]
    categories = (
        filtered_items.groupby("category", as_index=False)
        .agg(
            item_revenue=("price", "sum"),
            freight_value=("freight_value", "sum"),
            units=("order_item_id", "count"),
        )
        .sort_values("item_revenue", ascending=False)
    )
    if categories.empty:
        st.info("Não há itens de pedido para os filtros selecionados.")
    else:
        top_categories = categories.head(15)
        fig = px.bar(
            top_categories.sort_values("item_revenue"),
            x="item_revenue",
            y="category",
            orientation="h",
            text_auto=".2s",
            labels={"item_revenue": "Faturamento de itens (R$)", "category": "Categoria"},
            title="15 categorias com maior faturamento de itens",
        )
        st.plotly_chart(fig, width="stretch")
        categories["freight_ratio"] = (
            categories["freight_value"]
            / categories["item_revenue"].replace(0, float("nan"))
        )
        st.dataframe(
            categories.rename(
                columns={
                    "category": "Categoria",
                    "item_revenue": "Faturamento dos itens (R$)",
                    "freight_value": "Frete cobrado (R$)",
                    "units": "Unidades",
                    "freight_ratio": "Frete / itens",
                }
            ),
            hide_index=True,
            width="stretch",
            column_config={
                "Faturamento dos itens (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Frete cobrado (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Frete / itens": st.column_config.NumberColumn(format="percent"),
            },
        )

    payment_summary = payment_mix[
        payment_mix["order_id"].isin(filtered["order_id"])
    ].copy()
    payment_summary["Forma de pagamento"] = payment_summary["payment_type"].map(
        lambda value: PAYMENT_NAMES.get(value, value)
    )
    payment_summary = payment_summary.groupby(
        "Forma de pagamento", as_index=False
    )["payment_value"].sum().sort_values("payment_value", ascending=False)
    st.subheader("Formas de pagamento")
    st.dataframe(
        payment_summary.rename(columns={"payment_value": "Faturamento (R$)"}),
        hide_index=True,
        width="stretch",
        column_config={
            "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f")
        },
    )
    st.subheader("Desempenho por vendedor")
    seller_summary = (
        filtered_items.groupby("seller_id", as_index=False)
        .agg(
            item_revenue=("price", "sum"),
            freight_value=("freight_value", "sum"),
            units=("order_item_id", "count"),
            orders=("order_id", "nunique"),
        )
        .merge(
            filtered_items[
                ["seller_id", "seller_city", "seller_state"]
            ].drop_duplicates(),
            on="seller_id",
            how="left",
        )
        .sort_values("item_revenue", ascending=False)
        .head(20)
    )
    seller_summary["Vendedor"] = (
        seller_summary["seller_city"].fillna("Cidade não informada").str.title()
        + " - "
        + seller_summary["seller_state"].fillna("--")
    )
    seller_summary["Frete / itens"] = (
        seller_summary["freight_value"]
        / seller_summary["item_revenue"].replace(0, float("nan"))
    )
    st.dataframe(
        seller_summary[
            [
                "Vendedor",
                "orders",
                "units",
                "item_revenue",
                "freight_value",
                "Frete / itens",
            ]
        ].rename(
            columns={
                "orders": "Pedidos",
                "units": "Unidades",
                "item_revenue": "Faturamento dos itens (R$)",
                "freight_value": "Frete cobrado (R$)",
            }
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Faturamento dos itens (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Frete cobrado (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Frete / itens": st.column_config.NumberColumn(format="percent"),
        },
    )

with tabs[2]:
    st.subheader("Onde estão os clientes")
    city_summary = (
        filtered.groupby(["customer_city", "customer_state"], as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            paid_value=("paid_value", "sum"),
            unique_customers=("customer_unique_id", "nunique"),
        )
        .sort_values("orders", ascending=False)
    )
    left, right = st.columns([1, 1])
    with left:
        state_customers = (
            filtered.groupby("customer_state", as_index=False)
            .agg(customers=("customer_unique_id", "nunique"))
            .sort_values("customers", ascending=False)
        )
        state_customers["state_name"] = state_customers["customer_state"].map(
            lambda state: BRAZILIAN_STATES.get(state, state)
        )
        fig = px.bar(
            state_customers,
            x="state_name",
            y="customers",
            labels={"state_name": "Estado", "customers": "Clientes únicos"},
            title="Clientes únicos por estado",
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        st.markdown("**Principais cidades por pedidos**")
        st.dataframe(
            city_summary.head(15).rename(
                columns={
                    "customer_city": "Cidade",
                    "customer_state": "UF",
                    "orders": "Pedidos",
                    "paid_value": "Faturamento (R$)",
                    "unique_customers": "Clientes únicos",
                }
            ),
            hide_index=True,
            width="stretch",
            column_config={
                "Faturamento (R$)": st.column_config.NumberColumn(format="R$ %.2f")
            },
        )

with tabs[3]:
    st.subheader("Ponto de entrega e cobertura da transportadora")
    st.caption(
        "Selecione uma cidade com pedidos para posicionar o ponto. O nome da "
        "transportadora é informado manualmente, pois não existe nos CSVs."
    )
    city_points = (
        filtered.dropna(subset=["latitude", "longitude", "customer_city", "customer_state"])
        .groupby(["customer_city", "customer_state"], as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            latitude=("latitude", "mean"),
            longitude=("longitude", "mean"),
        )
        .sort_values("orders", ascending=False)
        .reset_index(drop=True)
    )
    if city_points.empty:
        st.warning(
            "Não foi possível obter coordenadas para as cidades destes filtros. "
            "Verifique os CEPs e o CSV de geolocalização."
        )
    else:
        map_controls = st.columns([2, 1])
        with map_controls[0]:
            city_index = st.selectbox(
                "Cidade do ponto de entrega",
                options=list(range(len(city_points))),
                format_func=lambda index: (
                    f"{city_points.iloc[index]['customer_city'].title()} - "
                    f"{city_points.iloc[index]['customer_state']} "
                    f"({city_points.iloc[index]['orders']:,} pedidos)"
                ),
            )
        with map_controls[1]:
            carrier_name = st.text_input("Transportadora", value="Minha transportadora")

        hub = city_points.iloc[city_index]
        hub_lat = float(hub["latitude"])
        hub_lng = float(hub["longitude"])
        square_area_km2 = 450
        side_km = math.sqrt(square_area_km2)
        half_side_km = side_km / 2
        lat_delta = half_side_km / 111.32
        lng_delta = half_side_km / (
            111.32 * max(math.cos(math.radians(hub_lat)), 0.01)
        )
        square = [
            [hub_lng - lng_delta, hub_lat - lat_delta],
            [hub_lng + lng_delta, hub_lat - lat_delta],
            [hub_lng + lng_delta, hub_lat + lat_delta],
            [hub_lng - lng_delta, hub_lat + lat_delta],
        ]
        hub_data = pd.DataFrame(
            [
                {
                    "longitude": hub_lng,
                    "latitude": hub_lat,
                    "name": carrier_name.strip() or "Transportadora",
                    "location": (
                        f"{hub['customer_city'].title()} - {hub['customer_state']}"
                    ),
                }
            ]
        )
        city_data = city_points.drop(index=city_index)
        layers = [
            pdk.Layer(
                "PolygonLayer",
                data=[{"coordinates": square}],
                get_polygon="coordinates",
                get_fill_color=[40, 120, 220, 35],
                get_line_color=[20, 80, 160, 220],
                line_width_min_pixels=2,
                stroked=True,
                filled=True,
                pickable=True,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=city_data,
                get_position="[longitude, latitude]",
                get_radius="orders",
                radius_scale=35,
                radius_min_pixels=3,
                radius_max_pixels=18,
                get_fill_color=[245, 155, 45, 180],
                pickable=True,
            ),
            pdk.Layer(
                "ScatterplotLayer",
                data=hub_data,
                get_position="[longitude, latitude]",
                get_radius=9000,
                get_fill_color=[210, 40, 40, 220],
                get_line_color=[255, 255, 255, 255],
                line_width_min_pixels=2,
                stroked=True,
                pickable=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=hub_data,
                get_position="[longitude, latitude]",
                get_text="name",
                get_size=16,
                get_color=[30, 30, 30, 255],
                get_pixel_offset=[0, -24],
                get_alignment_baseline="bottom",
                pickable=True,
            ),
        ]
        deck = pdk.Deck(
            layers=layers,
            initial_view_state=pdk.ViewState(
                latitude=hub_lat,
                longitude=hub_lng,
                zoom=5.2,
                pitch=0,
            ),
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            tooltip={
                "html": "<b>{name}</b><br/>{location}<br/>Pedidos: {orders}",
                "style": {"backgroundColor": "#fff", "color": "#222"},
            },
        )
        st.pydeck_chart(deck, width="stretch")
        st.metric("Área de cobertura desenhada", f"{square_area_km2} km²")
        st.caption(
            f"Quadrado de aproximadamente {side_km:.2f} km por lado, centrado "
            f"em {hub['customer_city'].title()} - {hub['customer_state']}. "
            "A área é uma aproximação cartográfica local."
        )

    st.subheader("Indicadores de prazo e satisfação")
    delivered = filtered[filtered["order_status"] == "delivered"]
    delivery_cols = st.columns(3)
    avg_days = delivered["delivery_days"].mean()
    late_rate = delivered["delivery_delay_days"].gt(0).mean()
    delivery_cols[0].metric(
        "Prazo médio (dias)",
        f"{avg_days:.1f}" if pd.notna(avg_days) else "—",
    )
    delivery_cols[1].metric(
        "Entregas após previsão",
        f"{late_rate:.1%}" if pd.notna(late_rate) else "—",
    )
    avg_review = filtered["review_score"].mean()
    delivery_cols[2].metric(
        "Nota média",
        f"{avg_review:.2f} / 5" if pd.notna(avg_review) else "—",
    )
    if not delivered.empty:
        delivery_by_state = (
            delivered.groupby("customer_state", as_index=False)
            .agg(
                delivery_days=("delivery_days", "mean"),
                delay_days=("delivery_delay_days", "mean"),
            )
            .sort_values("delay_days", ascending=False)
        )
        delivery_by_state["state_name"] = delivery_by_state["customer_state"].map(
            lambda state: BRAZILIAN_STATES.get(state, state)
        )
        fig = px.bar(
            delivery_by_state,
            x="state_name",
            y="delay_days",
            labels={"state_name": "Estado", "delay_days": "Atraso médio (dias)"},
            title="Atraso médio em relação à previsão por estado",
            color="delay_days",
            color_continuous_scale="Reds",
        )
        st.plotly_chart(fig, width="stretch")

st.caption(
    "Fonte: datasets públicos Olist. Valores monetários nominais em reais; "
    "resultados dependem dos filtros selecionados."
)
