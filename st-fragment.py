"""
# st.experimental_fragment testing
"""

# Imports
import streamlit as st
import plotly.express as px
import random


# Streamlit page configuration
st.set_page_config(
     page_title="Streamlit with Snowpark ",
     layout="wide"
 )



# Streamlit session state
if 'static_refresh' not in st.session_state:
    st.session_state.static_refresh = 0
if 'fragment_refresh' not in st.session_state:
    st.session_state.fragment_refresh = 0

countries_list = px.data.gapminder().country.unique().tolist()

@st.experimental_fragment
def chart_random_country():
    with st.container():
        option = st.selectbox("Select a Country",countries_list)
        if option:
            st.session_state.fragment_refresh += 1
            # country_choice = random.choice(countries_list)
            country_choice = option
            df = px.data.gapminder().query("country==@country_choice")
            fig = px.line(df, x="year", y="lifeExp", title='Life expectancy in '+country_choice)
            st.plotly_chart(fig, use_container_width=True)
        st.write('Fragment Refresh: '+str(st.session_state.fragment_refresh))


# Main page
st.title("""
    Walkthrough based on pyplot to highlight the use of Streamlit page fragments
""")
st.markdown("""<hr style="background-color:#29B5E8;margin-top: 0.5em;" /> """,unsafe_allow_html=True)

    

# st.write(random.choice(countries_list))

col1,col3,col2 = st.columns ([.495,.01,.495])
with col1:
    with st.container():
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.write("")
        st.session_state.static_refresh += 1
        df = px.data.gapminder().query("country=='Canada'")
        fig = px.line(df, x="year", y="lifeExp", title='Life expectancy in Canada - Static')
        st.plotly_chart(fig, use_container_width=True)
        st.write('Whole Page Refresh: '+str(st.session_state.static_refresh))
with col3:
    st.markdown(
        """
    <style>
    .vl {
        border-right: 1px solid green;
        border-left: 1px solid green;
        border-top: 1px solid green;
        border-bottom: 1px solid green;
        fill: solid green;
        height: 550px;
    }
    </style>

    <div class="vl"></div>
    """,
    unsafe_allow_html=True,
)

with col2:
    chart_random_country()


