# Import python packages
import streamlit as st
from snowflake.snowpark.context import get_active_session
from streamlit_extras.stylable_container import stylable_container
import plotly.express as px

# Global Variables
if "date_changed" not in st.session_state:
    st.session_state.date_changed = 0
if "first_run" not in st.session_state:
    st.session_state.first_run = 1

# CSS Styles
card_style_metric = """
    {
        border: 1px groove #52546a;
        border-radius: 10px;
        padding-left: 25px;
        padding-top: 10px;
        padding-bottom: 10px;
        box-shadow: 3px 3px 10px 1px #29B5E8; 
    
"""

card_style_text = """
    {
        /* border-color: #29B5E8; */
        border: 2px groove red;
        border-radius: 10px;
        padding-left: 25px;
        padding-top: 10px;
        padding-bottom: 10px;
        /* box-shadow: 3px 3px 10px 1px #29B5E8; */
    }
"""
@st.cache_data
def sql_statement_count (*args):
    if len(args) ==1 and args[0] == 'all':
        stmt = """
            select count(*) as executions ,round(sum(CREDITS_ATTRIBUTED_COMPUTE)) as credits
            from snowflake.account_usage.query_attribution_history
        """
    elif len(args) == 2:
        stmt = f"""
            select count(*) as executions,round(sum(CREDITS_ATTRIBUTED_COMPUTE)) as credits 
            from snowflake.account_usage.query_attribution_history
            where start_time >= to_date('{args[0]}')
            and end_time <= dateadd(day,1,to_date('{args[1]}'))
        """
    else:
        return 0
    sql_df = session.sql (stmt).collect()
    return sql_df
    
@st.cache_data
def sql_statement_list (*args):
    if len(args) ==1 and args[0] == 'all':
        stmt = """
            select query_id as query, 
                start_time as execution_time,
                CREDITS_ATTRIBUTED_COMPUTE as credits,
                False as detail
            from snowflake.account_usage.query_attribution_history
            order by start_time desc
        """
    elif len(args) == 2:
        stmt = f"""
            select query_id as query,
                start_time as execution_time,
                CREDITS_ATTRIBUTED_COMPUTE as credits ,
                False as detail
            from snowflake.account_usage.query_attribution_history
            where start_time >= to_date('{args[0]}')
            and end_time <= dateadd(day,1,to_date('{args[1]}'))
            order by start_time desc
        """
    else:
        return 0
    
    return  session.sql (stmt).collect()

@st.cache_data
def sql_statement_list_daily (*args):
    if len(args) ==1 and args[0] == 'all':
        stmt = """
            select 
                to_date (start_time) as day,
                count(*) as executions
            from snowflake.account_usage.query_attribution_history
            group by 1
            order by 1 
        """
    elif len(args) == 2:
        stmt = f"""
            select to_date (start_time) as day,
                count(*) as executions
            from snowflake.account_usage.query_attribution_history
            where start_time >= to_date('{args[0]}')
            and end_time <= dateadd(day,1,to_date('{args[1]}'))
            group by 1
            order by 1 
        """
    else:
        return 0
    
    return  session.sql (stmt).to_pandas()
# Get the current credentials
session = get_active_session()

st.set_page_config(layout='wide')

# Sidebar processing
st.sidebar.write(sql_statement_count("all"))

# Title text
st.title("SQL Compute Cost Attribution")
st.write(
    """This walkthrough showcases the new visual aspects 
       made possible by the support of :red[unsafe_allow_html]
       and the :red[stylable_container] module from the :red[streamlit_extras] package
    """
)

st.markdown("""<hr style="background-color:#29B5E8;margin-top: 0.5em;" /> """,unsafe_allow_html=True)


with st.container(border=True): # Main Global Container 
    with st.container():
        row1_col1, _r1c2,row1_col3 = st.columns([.3,.3,.4])
        with row1_col1:
            st.markdown("## Global Data")
        with row1_col3:
            with stylable_container("Card1", css_styles=card_style_text):
                "**Notice**"
                "Data pertaining all warehouses and SQL in the account."
    st.markdown("""<hr style="background-color:#29B5E8;margin-top: 0.5em;" /> """,unsafe_allow_html=True)
    
    row2_col1, row2_col2 = st.columns([1, 2.5])
    aux_sql_attribution = sql_statement_count("all")
    aux_sql_list = sql_statement_list("all")
    aux_sql_list_daily = sql_statement_list_daily ("all")
    with row2_col1:
        with st.container():
            row3_col1,row3_col2 = st.columns([.5,.5])
            with row3_col1:
                with stylable_container("Card2", css_styles=card_style_metric):
                    st.metric("SQL Executions", f'{aux_sql_attribution[0]["EXECUTIONS"]:,}', help="Total SQL executions")

            with row3_col2:
                with stylable_container("Card2", css_styles=card_style_metric):
                    st.metric("Total SQL Credits", f'{aux_sql_attribution[0]["CREDITS"]:,}', help="Total SQL credit consumption")
            with st.container(border=True):
                # Plotly
                # df = px.data.gapminder().query("country=='Canada'")
                fig = px.line(aux_sql_list_daily, x="DAY", y="EXECUTIONS", title='SQL Executions per Day')
                st.plotly_chart(fig,use_container_width=True)
        
    with row2_col2: 
        with stylable_container("Card3", css_styles=card_style_metric):
            edited_list = st.data_editor(aux_sql_list,hide_index=True,height=500,disabled=("QUERY","EXECUTION_TIME","CREDITS"))



