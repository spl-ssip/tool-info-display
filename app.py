import streamlit as st
from datetime import datetime
import time
import pandas as pd

# import local module
from config_loader import load_config
config = load_config()

from backend import load_data, load_data_all, get_inspection_data, get_CTQ_SpecNo
from helper import set_timer_style, plot_IMR, calculate_ppk

# ---- Load app setting from config ----

PAGE_REFRESH = config['refresh']['page_refresh']
OFFSET_CACHE = config['refresh']['offset_cache']
DEFAULT_CACHE_LIFE  = PAGE_REFRESH-OFFSET_CACHE #offset to avoid race
INSPECTION_DATA_CACHE = config['refresh']['inspection_data_cache']

# ---- Caching functions ----

# Load data into cache

@st.cache_data(ttl= DEFAULT_CACHE_LIFE)
def load_data_cached():
    df_tool_data = load_data()
    df_tool_data_all = load_data_all()
    last_refresh = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return df_tool_data, df_tool_data_all, last_refresh

@st.cache_data(ttl= INSPECTION_DATA_CACHE)
def get_inspection_data_cached(sapcode, specno):
    df_inspection_data = get_inspection_data(sapcode, specno)
    return df_inspection_data

@st.cache_data(ttl= INSPECTION_DATA_CACHE)
def get_CTQ_SpecNo_cached(sapcode):
    df_inspection_data = get_CTQ_SpecNo(sapcode)
    return df_inspection_data

# ---- UI ----
# ---- Page config ----
page_title = config['app']['title']
st.set_page_config(page_title=page_title, layout="wide")

#! deprecating! UI flickers and lost session state...(filter selection etc gone...)
# html meta tags to refresh at browser level
#st.markdown(f'<meta http-equiv="refresh" content="{PAGE_REFRESH}">',unsafe_allow_html=True)

# header
st.markdown(
    f"""
    <style>
        .block-container {{
            padding-top: 3rem !important;
        }}
    </style>
    <h1 style='text-align: center;'>{page_title}</h1>
    """,
    unsafe_allow_html=True
)




# ---- Initialize state ----

# Session_state (Note: this will not persist if browser tab refresh)
if 'clicked_materialcode' not in st.session_state:
    st.session_state.clicked_materialcode = None

if 'clicked_location' not in st.session_state:
    st.session_state.clicked_location = None
    
if 'clicked_materialdesc' not in st.session_state:
    st.session_state.clicked_materialdesc = None

# ---- Information Display ----

@st.fragment(run_every=str(PAGE_REFRESH)+"s")
def ShowTimerInfo():
    df_tool_data, df_tool_data_all, last_refresh = load_data_cached()


    #! ==================== WIP --> STILL BUGGY!!
    # # ---- Auto rerun every PAGE_REFRESH seconds (without clearing session state) ----

    # if 'enable_autorefresh' not in st.session_state:
    #     st.session_state.enable_autorefresh = True

    # st.checkbox("Enable Auto Refresh", key='enable_autorefresh') #! value = True??

    # if st.session_state.enable_autorefresh:
    #     with st.empty():
    #         for i in range(PAGE_REFRESH, 0, -1):
    #             st.markdown(f"<p style='text-align:center; color:grey;'>⏳ Auto-refresh in {i}s</p>", unsafe_allow_html=True)
    #             time.sleep(1)
    #         st.rerun()
    #! ====================

    # ---- Filters ----
    with st.container():
        col1, col2, col3 = st.columns(3)

        with col2:
            location_options = list(df_tool_data["Location"].unique())
            selected_locations = st.multiselect(label = ' ', label_visibility='collapsed', options=location_options, placeholder='Choose Machine')

    filtered_df = df_tool_data.copy()

    if selected_locations:
        filtered_df = filtered_df[filtered_df["Location"].isin(selected_locations)]
    
    st.markdown(f"<p style='text-align: center; color: grey;'>Last refreshed: {last_refresh}</p>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,4,1])

        with col2:
            for index, row in filtered_df.iterrows():

                # Create 3 columns: machine name | timer | button
                col_name, col_timer, col_tool, col_button, col_LED = st.columns([3, 2, 1, 1,1])  # adjust ratios as needed

                with col_name:
                    if row['TechRequired']:
                        st.markdown(f"<div style='font-size: 50px;animation: blinker 1s linear infinite;'><strong>{row['Location']} 🧑‍🏭</strong></div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='font-size: 50px;'><strong>{row['Location']}</strong></div>", unsafe_allow_html=True)

                with col_timer:
                    color, blink_style = set_timer_style(row['DurationMins'])

                    st.markdown(
                        f"""
                        <style>
                            @keyframes blinker {{
                                50% {{ opacity: 0; }}
                            }}
                        </style>
                        <div style="color: {color}; font-size: 50px; {blink_style}">
                            {row['DurationMins']} mins
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col_tool:
                    st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)  # Top spacer

                    # Store selected location for showing details at bottom section
                    if st.button("Show 🛠️", key=f"btn_{row['Location']}", use_container_width=True):
                        # #toggle off
                        # if st.session_state.clicked_location == row['Location']:
                        #     st.session_state.clicked_location = None # clear session state
                        # #toggle on
                        # else:
                        st.session_state.clicked_location = row['Location'] # update session state

                        st.session_state.clicked_materialcode = None  # 👈 force close the clicked_materialcode button
                        st.session_state.clicked_materialdesc = None  # 👈 Reset material description

                with col_button:
                    st.markdown("<div style='height:25px;'></div>", unsafe_allow_html=True)  # Top spacer

                    # Store selected materialcode for plotting at bottom section
                    if st.button("Show 📈", key=f"btn_{row['MaterialCode']}", use_container_width=True):
                        # #toggle off
                        # if st.session_state.clicked_materialcode == row['MaterialCode']:
                        #     st.session_state.clicked_materialcode = None # clear session state
                        # #toggle on
                        # else:
                        st.session_state.clicked_materialcode = row['MaterialCode'] # update session state
                        st.session_state.clicked_materialdesc = row['MaterialDesc'] # update session state

                        st.session_state.clicked_location = None  # 👈 force close the clicked_location button
                with col_LED:
                    
                    color = (
                        'red' if row['MacLEDRed'] else
                        'yellow' if row['MacLEDYellow'] else
                        '#00FF00' if row['MacLEDGreen'] else
                        'None'
                    )
                    st.markdown(f"""
                        <style>
                            .circle-container {{
                                    display: flex;
                                    align-items: center;
                                    justify-content: flex-end;
                                    height: 100px; /* Adjust height as needed */
                            }}
                            .circle-button {{
                                    height: 30px;
                                    width: 30px;
                                    border-radius: 50%;
                                    border: 1px solid #000;
                                    box-shadow: 2px 2px 2px rgba(0, 0, 0, 0.3);
                            }}
                        </style>
                        <div class="circle-container">
                            <span class="circle-button" style=" background: {color};"></span>
                        </div>
                        """, unsafe_allow_html=True)



    # ---- Bottom Section: Show tool data for clicked_location ----
    with st.container():
        col1, col2, col3 = st.columns([1,4,1])

        with col2:
            def clear_selection_clicked_location():
                st.session_state.clicked_location = None

            if st.session_state.clicked_location:
                st.markdown('---')
                st.markdown("### 📋 Upcoming Tool Change")
                st.info(f"Showing data for: `{st.session_state.clicked_location}`")

                cols = ['Turret','Tool','Process','Balance (mins)', 'Balance (pcs)']
                df = df_tool_data_all[df_tool_data_all['Location']==st.session_state.clicked_location]
                df = df[cols]

                st.dataframe(df, hide_index= True, use_container_width = False)
                st.button("❌ Close",key = f'close_{st.session_state.clicked_location}' , on_click=clear_selection_clicked_location)
                st.markdown('---')

    # ---- Bottom Section: Show IMR Chart for clicked_materialcode ----
    with st.container():
        col1, col2, col3 = st.columns([1,4,1])

        with col2:
            def clear_selection_clicked_materialcode():
                st.session_state.clicked_materialcode = None

            if st.session_state.clicked_materialcode:
                st.markdown('---')
                st.markdown("### 🔍 Inspection Details")

                materialcode = st.session_state.clicked_materialcode
                materialdesc = st.session_state.clicked_materialdesc
                specnoList = get_CTQ_SpecNo_cached(materialcode)
                #specno = '201' #! hardcoded specno
                for specno in specnoList['BalloonNo'].unique():
                    df_inspection_data = get_inspection_data_cached(materialcode, specno)

                    if not df_inspection_data.empty:
                        # Calculate ppk
                        df_inspection_data['LSL'] = pd.to_numeric(df_inspection_data['LSL'], errors='coerce')
        
                        df_inspection_data['USL'] = pd.to_numeric(df_inspection_data['USL'], errors='coerce')

                        ppk = calculate_ppk(df_inspection_data['MeasVal'],df_inspection_data['LSL'].iloc[0],df_inspection_data['USL'].iloc[0])

                        st.info(f"Showing details for: `{st.session_state.clicked_materialcode} | {materialdesc} |SpecNo:{specno}| {df_inspection_data['Description'].iloc[0]} | Ppk = {ppk}`")
                        fig = plot_IMR(df_inspection_data,df_inspection_data['LSL'].iloc[0],df_inspection_data['USL'].iloc[0]) 
                        st.pyplot(fig)
                    else:
                        st.warning(f"No inspection data available for `{st.session_state.clicked_materialcode}`.")

                st.button("❌ Close",key = f'close_{st.session_state.clicked_materialcode}', on_click=clear_selection_clicked_materialcode)
                st.markdown('---')
                
ShowTimerInfo()

# Tooling countdown times
