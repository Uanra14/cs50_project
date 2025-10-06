import helpers as hp
import json
import pandas as pd
import plotly.express as px
import streamlit as st
import duckdb

config = {
    "displaylogo": False,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d",
        "zoomIn", "zoomOut", "resetGeo",
        "zoomIn2d", "zoomOut2d", "autoScale2d",
        "resetScale2d", "lasso2d", "toImage",
    ]
}

# Configure streamlit app
st.set_page_config(
    page_title='NL Housing Market Dashboard',
    layout='wide',
    page_icon='🏠',
    initial_sidebar_state="expanded",
)

if "highlighted_listing" not in st.session_state:
    st.session_state["highlighted_listing"] = pd.DataFrame(columns=["price", "surface_area", "province"])


@st.cache_data
def load_data():
    with duckdb.connect('src/housing.duckdb', read_only=True) as conn:
        return conn.execute('SELECT price, wonen, province FROM listings').df()

df = load_data()
# clean_data
df = df[df['price'] < df['price'].quantile(0.99)]
df = df.rename(columns={'wonen': 'surface_area'})
df.dropna(subset=['price', 'surface_area', 'province'], inplace=True)


@st.cache_data
def load_geojson():
    with open('static/provinces_netherlands.geojson') as f:
        GEO_DATA = json.load(f)
    return GEO_DATA

GEO_DATA = load_geojson()

provinces = df['province'].unique().tolist()
PROVINCES = sorted([province for province in provinces if province != 'Unknown'])


@st.cache_data
def get_grouped_df(df):
    with duckdb.connect('src/housing.duckdb') as conn:
        return conn.execute('''SELECT
            province,
            AVG(price) AS average_price,
            AVG(wonen) AS average_surface_area,
            COUNT(*) AS total_listings
        FROM listings
        GROUP BY province
    ''').df()

df_grouped = get_grouped_df(df)

### --- SIDEBAR --- ###

with st.sidebar:
    st.title('🏠 NL Housing Market Dashboard')
    st.markdown("""
    This dashboard provides insights into the housing market in the Netherlands.
    """)

    col1, col2 = st.columns(2)
    with col1:
        price = st.number_input('Price (€)', min_value=1000, max_value=2000000, value=500000, step=1)
    with col2:
        surface_area = st.number_input('Area (m²)', min_value=10, max_value=1000, value=100, step=1)

    province_selected = st.selectbox('Select a province', ['Netherlands'] + PROVINCES)
    df_grouped["is_selected"] = df_grouped["province"] == province_selected

    st.button(
        'Add listing to chart',
        on_click=hp.add_listing_to_chart,
        args=(price, surface_area, province_selected)
    )

    st.button(
        'Clear highlighted listings',
        on_click=lambda: st.session_state.update({"highlighted_listing": pd.DataFrame(columns=["price", "surface_area", "province"])})
    )

    st.markdown("---")
    st.markdown("Developed by Arnau Duatis")

### --- MAIN PAGE --- ###
cols = st.columns((3, 2), gap = "medium")

with cols[0]:
    # dropdown selector based on province, and a whole netherlands option, displays scatterplot of price vs surface area
    selected_province_data = df if province_selected == 'Netherlands' else df[df['province'] == province_selected]
    df_grouped["price_per_m2"] = df_grouped["average_price"] / df_grouped["average_surface_area"]

    # scatterplot
    fig = px.scatter(selected_province_data, x='surface_area', y='price', title=f'Price vs Surface Area in {province_selected}', labels={'surface_area': 'Surface Area (m²)', 'price': 'Price (€)'})

    # do not show legend
    if not st.session_state["highlighted_listing"].empty:
        fig.add_scatter(
            x=st.session_state["highlighted_listing"]['surface_area'],
            y=st.session_state["highlighted_listing"]['price'],
            mode='markers',
            marker=dict(color='red', size=10, symbol='x'),
            name='Highlighted Listings'
        )
    fig.update_layout(
        showlegend=False, 
        height=400, margin={"r":0,"t":30,"l":0,"b":0},
        dragmode=False,
    )

    st.plotly_chart(fig, use_container_width=True, config=config)

with cols[1]:
    # Create a map colored by average price per province, make background black
    fig = px.choropleth(
        df_grouped, 
        geojson=GEO_DATA, 
        locations='province',
        fitbounds="locations",
        color='price_per_m2',
        labels={'price_per_m2': 'Average Price per m² (€/m²)'}, 
        featureidkey='properties.name',
        title='Average Housing Price per m² in the Netherlands',
    )

    fig.update_geos(
        fitbounds="locations", 
        visible=False,
        bgcolor="rgba(0,0,0,0)",
        center={"lat": 52.1326, "lon": 5.2913}
    )

    fig.update_layout(
        template='plotly_dark',
        title = dict(
            x=0.5,
            xanchor='center',
            y=0.99,
            yanchor='top'
        ),
        geo=dict(bgcolor='rgba(0,0,0,0)'),
        height=400,
        margin={"r":0,"t":0,"l":0,"b":0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode=False,
        coloraxis_colorbar=dict(
            orientation="h",
            yanchor="top",
            y = 0.2,
            x = 0.5,
            xanchor="center"
        )
    )

    if province_selected == 'Netherlands':
        fig.update_traces(
            marker_line_width=2,
            marker_line_color='red'
        )
    else:
        fig.update_traces(
            marker_line_width=df_grouped['is_selected'].map({True: 3, False: 0.5}),
            marker_line_color=df_grouped['is_selected'].map({True: 'red', False: 'black'})
        )

    st.plotly_chart(fig, use_container_width=True, config=config)

### --- FOOTER --- ###

# collect variables
selected_province_price = df_grouped[df_grouped['province'] == province_selected]['average_price'].values[0] if province_selected != 'Netherlands' else df['price'].mean()
selected_province_area = df_grouped[df_grouped['province'] == province_selected]['average_surface_area'].values[0] if province_selected != 'Netherlands' else df['surface_area'].mean()
price_per_m2_province = selected_province_price / selected_province_area if selected_province_area > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(f'Total Listings in {province_selected}', f"{len(selected_province_data):,}")

with col2:
    st.metric('Average Price', f"{selected_province_price:,.0f} €")

with col3:
    st.metric('Average Surface Area', f"{selected_province_area:,.0f} m²")

with col4:
    st.metric('Average Price per m²', f"{price_per_m2_province:,.0f} €")

if not st.session_state["highlighted_listing"].empty:

    # get the last added listing
    last_listing = st.session_state["highlighted_listing"].iloc[-1]
    last_listing_price = last_listing['price']
    last_listing_area = last_listing['surface_area']
    price_per_m2_last_listing = last_listing_price / last_listing_area if last_listing_area > 0 else 0

    st.markdown(
    "<hr style='margin-top:-10px; margin-bottom:0;'>",
    unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)
    # change markdown colors based on the price per m² compared to the average price per m² in the selected province
    with col2:
        st.metric('Your Listing Price', f"{last_listing_price:,.0f} €")

    with col3:
        st.metric('Your Listing Area', f"{last_listing_area:,.0f} m²")

    delta = price_per_m2_last_listing - price_per_m2_province
    delta_str = f"{delta:,.0f} € {'more' if delta > 0 else 'less'} than average" if last_listing_area > 0 else "N/A"
    
    with col4:
        if last_listing_area > 0:
            st.metric('Your Price per m²', f"{price_per_m2_last_listing:,.0f} €", delta=delta_str, delta_color="inverse")
        else:
            st.metric('Your Price per m²', "N/A")