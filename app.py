# Import python packages
## Snowflake
import streamlit as st
from snowflake.snowpark.context import get_active_session
## Others
import plotly.express as px
import base64

# Write directly to the app
st.title("Testing printing from SiS")
st.write(
    """This is a test of how to build HTML reports
       based on the Streamlit application content
    """
)

# Get the current credentials
session = get_active_session()

# Create generic plotly figure
fig = px.scatter(px.data.iris(), x="sepal_length", y="sepal_width", color="species")
st.plotly_chart(fig) 
# at the same time, save it to a variable 
# in HTML format
chart_html = fig.to_html(full_html = True, include_plotlyjs = True) # Generating the full HTML but keeping the plotly.js library

# For now, display the generated HTML
st.text(chart_html)


html_b64 = base64.b64encode(chart_html.encode('utf-8'))
st.sidebar.markdown('### :red[Right click on the "Download" link and save the file]')
st.sidebar.markdown(f'**💾 ➡️ [Download ](data:text/html;base64,{html_b64.decode()})**')

# OR...

st.sidebar.download_button(label = "Download Report",
                           data=chart_html,
                          file_name = "Jorge.html",
                          mime="text/html")
