import pandas as pd
import streamlit as st

def add_listing_to_chart(price, surface_area, province_selected):
    new_row = {"price": price, "surface_area": surface_area, "province": province_selected}

    st.session_state["highlighted_listing"] = pd.concat(
        [st.session_state["highlighted_listing"], pd.DataFrame([new_row])],
        ignore_index=True
    )