import streamlit as st
import pandas as pd
import db_context as db
import streamlit.components.v1 as comp
from logging import exception
import altair as alt
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
import toml
from fpdf import FPDF, HTMLMixin
from fpdf.html import HTML2FPDF
from datetime import date
import base64


version_number = 1.5
#--------------------------------------------------------------
# PDF EXport Setup
#--------------------------------------------------------------
class HTMLMixinCustom(object):
    def write_html(self, text, image_map=None):
        "Parse HTML and convert it to PDF"
        h2p = HTML2FPDF(self, image_map = image_map)
        h2p.set_font('Arial',8)
        h2p.feed(text)

class myPDF(FPDF, HTMLMixinCustom):
    pass

pdf = myPDF('L','in',(11,17))
pdf.set_auto_page_break(True, margin=.5)
pdf.add_font('Lato-Regular','','resources/Lato-Regular.ttf', uni=True)
pdf.set_display_mode(zoom='fullwidth',layout='default')
pdf.set_margins(.25,.25,.25)

def create_download_link(val, filename):
    b64 = base64.b64encode(val)  # val looks like b'...'
    return f'<br/> &nbsp; 💾 &nbsp; <a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf"><b>DOWNLOAD RESULTS</b> </a>'


#--------------------------------------------------------------
# Streamlit page setup and overrides
#--------------------------------------------------------------
page_config = {"page_title" : "PS Health Check", "page_icon":":snowflake", "layout": "wide"}
st.set_page_config(**page_config)
#st.set_page_config(layout="wide", page_title="PS Health Check")

st.markdown(
    """
    <style>
    span[data-baseweb="tag"] {
    background-color: #29B5E8 !important;
    }
    .appview-container .main .block-container{
        padding-top: 1px; 
        padding-left: 20px;     }
    .reportview-container .sidebar-content {
                    padding-top: 1px;
                }
    #MainMenu {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)
comp.html("""<div
    style="background-color:#29B5E8; width: 100%; margin: 1px; padding-left: 2em; padding-top: 20px; padding-bottom: 1px;">
    <p style="color: white; font-family:Arial, Helvetica, sans-serif;">Internal Use Only</p>
</div>""")


check_types = toml.load('resources/checks.toml')
if 'defaults_override' not in st.session_state:
    st.session_state['defaults_override'] = False

if st.session_state['defaults_override'] == True:
       general_defaults = check_types['general']
       clustering_defaults = check_types['clustering']
       data_loading_defaults = check_types['data_loading']
       security_defaults = check_types['security']
       workload_defaults = check_types['workload']
else:
    general_defaults = check_types['general_defaults']
    clustering_defaults = check_types['clustering_defaults']
    data_loading_defaults = check_types['data_loading_defaults']
    security_defaults = check_types['security_defaults']
    workload_defaults = check_types['workload_defaults']
        

#--------------------------------------------------------------
# Query String Management
#--------------------------------------------------------------


query_params = st.experimental_get_query_params()

if query_params:
    if 'is_connected' in query_params:
        if query_params['is_connected'][0] == "True":
            if 'is_connected' not in st.session_state:
                st.session_state['is_connected'] = str(query_params['is_connected'][0])
                st.session_state['username'] = str(query_params['username'][0])
                st.session_state['selected_role'] = str(query_params['role'][0])
                if 'snow_conn' not in st.session_state:
                    st.session_state['snow_conn'] = db.connect_to_snowflake(
                            st.session_state['username'],
                            st.session_state['selected_role'])
                    try:
                            st.session_state['connection_details'] = db.get_connection_details(st.session_state['snow_conn'])
                            st.session_state['is_connected'] = True
                    except None as e:
                        print(e)
                    finally:
                        if 'connection_details' in st.session_state:
                            st.session_state['is_connected'] = True



#--------------------------------------------------------------
# Set Default texts based on session state variables"
#--------------------------------------------------------------

#NO CHECK TO FULLY REFRESH LIST
selected_checks = []
if 'org_list' not in st.session_state:
    st.session_state['org_list'] = []
if 'is_connected' not in st.session_state:
    st.session_state['disable_button'] = True
    st.session_state['connection_summary'] = f"""Not Connected"""
else:
    st.session_state['disable_button'] = False
    st.session_state[
        'connection_summary'] = f"""Connection Details \n Role: {st.session_state['connection_details'][1]} \n Date: {st.session_state['connection_details'][0]}"""

if 'client_list' not in st.session_state:
    st.session_state['client_list'] = []

if 'results_header' not in st.session_state:
    st.session_state['results_header'] = ''



#--------------------------------------------------------------
# Account Selector function - Uses Cache to avoid re-run"
#--------------------------------------------------------------
@st.cache(suppress_st_warning=True, show_spinner=False)
def get_account_selector(account_filters):
    st.session_state['all_accounts_map'] = db.get_accounts(
        st.session_state['snow_conn'], account_filters)
    return st.session_state['all_accounts_map']


def create_account_filters():
    if 'account_filters' in st.session_state:
        acct_list = st.session_state['account_filters'].replace("'","''").strip()
        account_filter = f"'%{acct_list}%'"
        st.session_state['client_list'] = []
    return account_filter

def filter_accounts_selector():
    if 'org_selected' in st.session_state:
         st.session_state['client_list'] = st.session_state['all_accounts_map'].loc[st.session_state['all_accounts_map']['OFFICIAL_ORG_NAME'] == st.session_state['current_org']]
    else:
         st.session_state['client_list'] = []
#--------------------------------------------------------------
# Main Function for Generating Checks"
#--------------------------------------------------------------
def generate_streams():
    #INITIALIZE PDF OBJECT
    
    

    st.session_state['results_header'] = "Health Check Results"
    account_details = st.session_state['all_accounts_map'].loc[
        st.session_state['all_accounts_map']["LABEL"] == str(
            st.session_state['account_selected'])]
    st.session_state['searchable_account_name'] = account_details['ACCCOUNT_NAME'].values[0]
    st.session_state['searchable_account_id'] = account_details['ACCOUNT_ID'].values[0]
    st.session_state['searchable_account_deployment'] = account_details['DEPLOYMENT'].values[0]
    st.session_state['searchable_account_organization'] = account_details['ORGANIZATION_NAME'].values[0]

    report_sections = 0
    pdf.add_page()
    pdf.set_font('Lato-Regular', '', 18)
    title =  f"Health Check Results for: {st.session_state['searchable_account_name']}"
    org = f"Organization: {st.session_state['org_selected']}"
    pdf.image('resources/logo-sno-blue.jpg')
    pdf.cell(8, .75,title, ln=1)
    pdf.set_font('Lato-Regular', '', 14)
    pdf.cell(8, .5,org, ln=1)
    pdf.set_font('Arial', 'I', 12)
    pdf.cell(8, .5,f'Created on: {date.today()}', ln=1)

    get_account_parameters()

    #GENERAL
    if len(general_selection) > 0:
        st.markdown('---')
        st.header("GENERAL")
    if 'Days with billable cloud services' in selected_checks:
        billing_data = get_cloud_services_billing_data()
        if len(billing_data ) > 0:
            add_report_page('GENERAL: Days with billable cloud services',\
                        'Days that have cloud services usage exceed 10% of the total compute usage',\
                        billing_data, [])
            report_sections += 1

    #CLUSTERING
    if len(clustering_selection) > 0:
        st.markdown('---')
        st.header("CLUSTERING")
        if 'Leading key types' in selected_checks:
            leading_key = get_leading_key_data_type_data()
            if len(leading_key) >0:
                add_report_page('CLUSTERING: Leading key types',\
                        'Information about leading keys',\
                        leading_key, [])
                report_sections += 1

        if 'Number of Cluster Keys' in selected_checks:
            num_clusters = get_num_cluster_keys_data()
            if len(num_clusters) >0:
                add_report_page('CLUSTERING: Number of cluster keys',\
                     'General information about clustering keys',\
                     num_clusters, [])
                report_sections += 1

        if 'Clustering Usage Information' in selected_checks:
            tbl_clustered = get_pct_tables_clustered_data()
            if len(tbl_clustered) >0:
                add_report_page('CLUSTERING: Clustering Usage Information',\
                     'General Clustering information statistics',\
                     tbl_clustered, [])
                report_sections += 1

        if 'Materialized View with auto-clustered Source' in selected_checks:
            mv_with_ac = get_mv_with_ac_source_data()
            if len(mv_with_ac) >0:
                add_report_page('CLUSTERING: Materialized View with auto-clustered Source',\
                     'Materialized views that have auto-clustering enabled.. ',\
                     mv_with_ac, [])
                report_sections += 1

    #DATA LOADING
    if len(data_loading_selection) > 0:
        st.markdown('---')
        st.header("DATA LOADING")
        if 'Avg time spent listing external files' in selected_checks:
            avg_time_ltg = get_avg_time_listing_external_files_data()
            if len(avg_time_ltg) >0:
                add_report_page('DATA LOADING: Avg time spent listing external files',\
                     'Average time spent listing files from external stages, indicates when patterns or volume might cause delays. ',\
                     avg_time_ltg, [])
                report_sections += 1

        if 'Top 100 tables with average loaded file size < 100MB or > 250MB' in selected_checks:
            data_load_met = get_data_loading_size_metric()
            if len(data_load_met) >0:
                add_report_page('DATA LOADING: Tables with data loaded > 250MB or < 100MB',\
                     'Tables with data loads outside of the recommended sizes. ',\
                     data_load_met, [])
                report_sections += 1

    #SECURITY
    if len(security_selection) > 0:
        st.markdown('---')
        st.header("SECURITY")
        if 'Number of users granted ACCOUNTADMIN' in selected_checks:
            act_admn_cnt = get_account_admin_count_data()
            if len(act_admn_cnt) >0:
                add_report_page('SECURITY: Users with Account Admin Role',\
                     'Lower Boundry 2, Higher Boundry: 5',\
                     act_admn_cnt, [])
                report_sections += 1

        if 'Percent users granted built-in role' in selected_checks:
            pct_usr_sys_role = get_pct_users_granted_system_role_data()
            if len(pct_usr_sys_role) >0:
                add_report_page('Percent users granted built-in role',\
                     'General built-in roles assignments information statistics',\
                     pct_usr_sys_role, [])
                report_sections += 1
        
    #WORKLOAD
    if len(workload_selection) > 0:
        st.markdown('---')
        st.header("WORKLOAD")
        if 'Top Queries by Credits Used' in selected_checks:
            top_queries = get_top_100_queries_data()
            if len(top_queries) >0:
                add_report_page('WORKLOAD: Analyze Top Queries Data',\
                     'Top 100 queries by Credits Used',\
                     top_queries, ['CREDITS_USED_RANK','CREDITS_USED', 'SAMPLE_QUERY_ID', 'QUERY_COUNT', 'WAREHOUSE_NAME','WAREHOUSE_SIZE','SEVERITY','RECOMMENDATION','AVG_EXECUTION_TIME_SECONDS'])
                report_sections += 1
        if 'Remote Spilling by Warehouse' in selected_checks:
            rmt_spil = get_remote_spilling_data()
            if len(rmt_spil) >0:
                add_report_page('WORKLOAD: Excessive Remote Storage Spilling Events',\
                     'Queries that have spilled data into remote storage.  ',\
                     rmt_spil, [])
                report_sections += 1

        if 'Percent time queries spent queued' in selected_checks:
            pct_queue = get_pct_queueing_of_total_dur_by_warehouse_data()
            if len(pct_queue) >0:
                add_report_page('WORKLOAD: Percent time queries spent queued',\
                     'Queries that spent a high percentage of time queued, a good indicator that scaling-out might be necessary',\
                     pct_queue, [])
                report_sections += 1

        if 'Invalid Materialized View Definitions' in selected_checks:
            invalid_mvs = get_invalid_mvs_data()
            if len(invalid_mvs) >0:
                add_report_page('WORKLOAD: Invalid Materialized Views',\
                     'Views in an invalid state. ',\
                     invalid_mvs, [])
                report_sections += 1

        if 'High Turnover Tables' in selected_checks:
            high_trnvr = get_short_lived_permanent_tables_data()
            if len(high_trnvr) >0:
                add_report_page('WORKLOAD: Analyze High Turnover Tables Data',\
                     'Tables created with a short life span.',\
                     high_trnvr, [])
                report_sections += 1

        if 'Pruning of reoccuring jobs' in selected_checks:
            poor_prooning = get_poor_pruning_repetitive_jobs_data()
            if len(poor_prooning) >0:
                add_report_page('WORKLOAD: Pruning of reoccuring jobs',\
                     'Jobs and queries with poor pruning. ',\
                     poor_prooning, [])
                report_sections += 1
        if 'High Concurrency Watermark' in selected_checks:
            high_conc_wtmk = get_wh_high_conc_watermark()
            if len(high_conc_wtmk) >0:
                add_report_page('WORKLOAD: High Concurrency Watermark',\
                    'Provides information about warehouses that might be consolidated',\
                    high_conc_wtmk, [])
                report_sections += 1

        if 'Warehouse Size Score' in selected_checks:
            wh_score = get_wh_scores()
            if len(wh_score) >0:
                add_report_page('WORKLOAD: Warehouse Scoring ',\
                    'Provides Top level recommendations on Warehouse Size.',\
                    wh_score.loc[wh_score['RECOMMENDATION']!='NO RECOMMENDATION'].sort_values(by='RECOMMENDATION'),\
                    ['WAREHOUSE','RECOMMENDATION', 'CURRENT_SIZE', 'RECOMMENDED_SIZE'])
                report_sections += 1
    if report_sections > 0:
        with left_info:
            html = create_download_link(pdf.output(dest="S").encode("latin-1"), f"HealthCheckReport-{st.session_state['searchable_account_name']}")
            st.markdown(html, unsafe_allow_html=True)
  



def generate_html_for_pdf(data):
        rowdata = "<tbody>"
        for index, row in data.iterrows():
            rowdata += "<tr>"
            for i in data.columns:
                header_width =  len(i)
                if data[f"{i}"].isnull().all():
                    width = int(header_width*.6)
                else:
                    data_width = data[f"{i}"].astype(str).str.len().max()
                    if header_width > data_width:
                        width = int(header_width*.6)
                    else:
                        width = int(data_width*.6)
                rowdata += f'<td width="{width}" height="1" align="left" > {row[f"{i}"]}</td>'
            rowdata += '</tr>'

        rowdata += '</tbody>'
        headers = "<thead><tr>"
        for i in data.columns:
            header_width =  len(i)
            if data[f"{i}"].isnull().all():
                    width = int(header_width*.6)
            else:
                data_width = data[f"{i}"].astype(str).str.len().max()
                if header_width > data_width:
                    width = int(header_width*.6)
                else:
                    width = int(data_width*.6)
            headers += f'<th width="{width}" height="1"  align="left"> {i}</th>'
        headers += "</tr></thead>"

        render_html = f'''<table>{headers}{rowdata}</table>'''
        return render_html

def add_report_page(title, description, dframe, fields):
    pdf.set_font('Lato-Regular', '', 18)
    pdf.cell(w=0,h=.6,txt=f'{title}', ln=1)
    pdf.set_font('Lato-Regular', '', 12)
    pdf.cell(w=0,h=.2,txt=f'{description}',ln=1)
    if len(fields) == 0:
        html = generate_html_for_pdf(dframe)
        pdf.write_html(html, image_map=None)
    else:
        html = generate_html_for_pdf(dframe[fields])
        pdf.write_html(html, image_map=None)
#--------------------------------------------------------------
# Generate Streams - Sub Functions"
#--------------------------------------------------------------
def get_account_parameters():
    with left_info:
        st.info("""
        ### Account Information: 
        - Account ID :{0}
        - Organization: {1}
        - Account Name: {2}
        - Deployment: {3}
        """.format(str(st.session_state['searchable_account_id']),\
            str(st.session_state['searchable_account_organization']),\
            str(st.session_state['searchable_account_name']),\
            str(st.session_state['searchable_account_deployment'])\
                ))


def get_cloud_services_billing_data():
    cloud_bill_data_pda = db.get_cloud_services_billing(st.session_state['snow_conn'], \
                                                                        str(st.session_state['searchable_account_name']),\
                                                                        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if not cloud_bill_data_pda.empty:
            with st.container():
                st.subheader("Days with billable cloud services")
            cloud_billable_chart = alt.Chart(
                cloud_bill_data_pda).mark_bar().encode(
                    alt.X("DATE:T", axis=alt.Axis(format="%b %d")),
                    y='sum(CREDITS):Q', color='TYPE:N'
                    )
            st.session_state[
                'cloud_billable_alt_chart'] = st.altair_chart(
                    cloud_billable_chart, use_container_width=True)
            with st.expander("Days with billable cloud services"):
                cloud_bill_data_pda = cloud_bill_data_pda.sort_values(by=['DATE'])
                AgGrid(cloud_bill_data_pda)
                return cloud_bill_data_pda
        else:
            st.info('Days with Billable Cloud Services : NO DATA')
            return pd.DataFrame()

def get_wh_scores():
    wh_scoring_pda = db.get_warehouse_size_scores(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']),
        str(st.session_state['searchable_account_id']))
    with st.container():
        if len(wh_scoring_pda) != 0:
            st.subheader("Warehouse Sizing Scoring")
            st.caption("These recommendations must be analyzed to determine if warehouse behavior is expected. These recommendations do not account for business rules and or needs. ")
            recommendations_row1 = st.columns(2)
            recommendations_row2 = st.columns(2)
            with recommendations_row1[0]:
                st.subheader('🔍')
                needmore = wh_scoring_pda.loc[wh_scoring_pda['RECOMMENDATION']=='REQUIRES MORE ANALYSIS']
                st.metric("Requires more Analysis",str(len(needmore[['WAREHOUSE','RECOMMENDED_ACTION']])) )
                if len(needmore)>0:
                    with st.expander(""):
                        AgGrid(needmore[['WAREHOUSE','RECOMMENDED_ACTION']], key='needmore')
            with recommendations_row1[1]:
                st.subheader('✅')
                norecom = wh_scoring_pda.loc[wh_scoring_pda['RECOMMENDATION']=='NO RECOMMENDATION']
                st.metric("No recommendations available",str(len(norecom[['WAREHOUSE','RECOMMENDED_ACTION']])) )
                if len(norecom)>0:
                    with st.expander(""):
                        AgGrid(norecom[['WAREHOUSE','RECOMMENDED_ACTION']], key='norecom')
            with recommendations_row2[0]:
                st.subheader('⬆️')
                scaleup = wh_scoring_pda.loc[wh_scoring_pda['RECOMMENDATION']=='SCALE UP']
                st.metric("Scale-Up Recommended",str(len(scaleup[['WAREHOUSE','RECOMMENDED_ACTION']])) )
                if len(scaleup) > 0:
                    with st.expander(""):
                        AgGrid(scaleup[['WAREHOUSE','RECOMMENDED_ACTION']], key='scaleup')
  
            with recommendations_row2[1]:
                st.subheader('⬇️')
                scaledown = wh_scoring_pda.loc[wh_scoring_pda['RECOMMENDATION']=='SCALE DOWN']
                st.metric("Scale-Down Recommended",str(len(scaledown[['WAREHOUSE','RECOMMENDED_ACTION']])) )
                if len(scaledown) > 0:
                    with st.expander(""):
                        AgGrid(scaledown[['WAREHOUSE','RECOMMENDED_ACTION']], key='scaledown')

            with st.expander("Warehouse Scoring Data"):
                wh_scoring_gb = GridOptionsBuilder.from_dataframe(wh_scoring_pda)
                wh_scoring_gb.configure_side_bar()
                wh_scoring_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                wh_scoring_gb.configure_auto_height = False
                wh_scoring_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                wh_scoring_gb_options = wh_scoring_gb.build()
                AgGrid(wh_scoring_pda, gridOptions=wh_scoring_gb_options, enable_enterprise_modules=True)
                return wh_scoring_pda
           

        else:
            st.info('Warehouse Sizing Scores : NO DATA')
            return pd.DataFrame()

def get_wh_high_conc_watermark():
    high_concurrency_pda = db.get_high_concurrency_wtmk(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(high_concurrency_pda) != 0:
            st.subheader("High Concurrency Watermark") 
            st.caption("This graphic represent the top 25 low concurrency , high consumption warehouses. Additional data in the Analyze section. Bar represents Average Concurrency and Tick represents Max Concurrency.")
            top_25_high_wtmk = high_concurrency_pda.sort_values(by=['CREDITS_CONSUMED', 'AVG_WATERMARK'],ascending =[False,True]).head(25)
            high_concurrency_watermark_bar = alt.Chart(top_25_high_wtmk).mark_bar(color ='#29B5E8',text='AVG_WATERMARK:Q').encode(
                    x=alt.X('WAREHOUSE',title='Warehouse'),
                    y= alt.Y('AVG_WATERMARK:Q', title='Concurrency'),
                ).properties(height=450)
            high_concurrency_watermark_max_line = alt.Chart(top_25_high_wtmk).mark_tick(color ='#11567F',thickness=5, text='MAX_WATERMARK:Q').encode(
                    x=alt.X('WAREHOUSE',title='Warehouse'),
                    y= alt.Y('MAX_WATERMARK:Q', title='Max Concurrency'),
                ).properties(height=450)


            st.altair_chart(high_concurrency_watermark_bar+high_concurrency_watermark_max_line, use_container_width=True)
            with st.expander("Analyze High Watermark Data"):
                high_wtmk_gb = GridOptionsBuilder.from_dataframe(top_25_high_wtmk)
                high_wtmk_gb.configure_side_bar()
                high_wtmk_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                high_wtmk_gb.configure_default_column(groupable=True, editable=False)
                high_wtmk_gb.configure_column(field='WAREHOUSE', enablePivot=True)
                high_wtmk_gb.configure_column(field='AVG_WATERMARK', enablePivot=True)
                high_wtmk_gb.configure_column(field='MAX_WATERMARK', enablePivot=True)
                high_wtmk_gb.configure_column(field='CREDITS_CONSUMED', enablePivot=True, aggFunc='max')
                high_wtmk_gb_options = high_wtmk_gb.build()
                AgGrid(high_concurrency_pda.sort_values(by=['CREDITS_CONSUMED', 'AVG_WATERMARK'],ascending =[False,True]), gridOptions=high_wtmk_gb_options, enable_enterprise_modules=True)
            return high_concurrency_pda
        else:
            st.info('High Concurrency Watermark : NO DATA')
            return pd.DataFrame()



def get_data_loading_size_metric():
    data_loading_size_pda = db.get_tables_data_loading_size_metric(
            st.session_state['snow_conn'],
            str(st.session_state['searchable_account_name']),
            str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(data_loading_size_pda) != 0:

            st.subheader("Tables with data loaded > 250MB or < 100MB")
            with st.expander("Results  -- ⬇️"):
                data_loading_gb = GridOptionsBuilder.from_dataframe(data_loading_size_pda)
                data_loading_gb.configure_side_bar()
                data_loading_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                data_loading_gb.configure_auto_height = False
                data_loading_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                data_loading_gb.configure_column(field='GB_SPILLED_TO_REMOTE', enablePivot=True, aggFunc='sum')
                data_loading_gb_options = data_loading_gb.build()
                AgGrid(data_loading_size_pda, gridOptions=data_loading_gb_options, enable_enterprise_modules=True)
                return data_loading_size_pda
        else:
            st.info('Tables with data loaded > 250MB or < 100MB : NO DATA')
            return pd.DataFrame()


def get_remote_spilling_data():
    remote_spilling_pda = db.get_remote_spilling(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(remote_spilling_pda) != 0:
            st.subheader("Excessive Remote Storage Spilling Events")
            with st.expander("Results  -- ⬇️"):
                remote_spilling_gb = GridOptionsBuilder.from_dataframe(remote_spilling_pda)
                remote_spilling_gb.configure_side_bar()
                remote_spilling_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                remote_spilling_gb.configure_auto_height = False
                remote_spilling_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                remote_spilling_gb.configure_column(field="EVENT_TIMESTAMP", type=["customDateTimeFormat"], custom_format_string="yyyy-MM-dd HH:mm")
                remote_spilling_gb.configure_column(field='GB_SPILLED_TO_REMOTE', enablePivot=True, aggFunc='sum')
                remote_spilling_gb_options = remote_spilling_gb.build()
                AgGrid(remote_spilling_pda, gridOptions=remote_spilling_gb_options, enable_enterprise_modules=True)
                return remote_spilling_pda
        else:
            st.info('Excessive Remote Storage Spilling Events : NO DATA')
            return pd.DataFrame()


def get_account_admin_count_data():
    try:
        admin_account_pda = db.get_account_admin_cnt(
            st.session_state['snow_conn'],
            str(st.session_state['searchable_account_name']),
            str(st.session_state['searchable_account_deployment']))
        if len(admin_account_pda) != 0:
            st.subheader("Number of Users granted Account Admin Role")
            st.metric("Lower Boundry: 2, Upper Boundry: 5",
                        admin_account_pda['VALUE'].values[0],
                        admin_account_pda['DELTA'].values[0])
            return admin_account_pda
        else:
            st.success('Number of users granted ACCOUNTADMIN :OK')
            return pd.DataFrame()
    except:
        st.error('Number of users granted ACCOUNTADMIN :Error creating visual')

def get_top_100_queries_data():
    top_queries_pda = db.get_top_100_queries(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(top_queries_pda) != 0:
            st.subheader("Top Queries")
            st.caption("Select a range in top graphic to explore details.") 
            brush = alt.selection(type='interval')
            top_queries_chart = alt.Chart(top_queries_pda).mark_bar().encode(
                alt.X('WAREHOUSE_NAME:O',scale=alt.Scale(2), title="Warehouse"),
                alt.Y('sum(CREDITS_USED):Q', title="Credits Used"),
                color=alt.condition(brush, 'SEVERITY:N', alt.value('lightgray'))
                    ).add_selection(
                        brush
                    ).properties(width=1100)
            bars = alt.Chart(top_queries_pda).mark_bar().encode(
                    alt.X('sum(QUERY_COUNT):Q', title= "Number of Query Executions"),
                    alt.Color('SEVERITY:N'),
                    alt.Y('RECOMMENDATION')
                ).transform_filter(
                    brush
                ).properties(width=1100)
            st.altair_chart(alt.vconcat(top_queries_chart.interactive(), bars), use_container_width=True)
            with st.expander("Analyze Top Queries Data"):
                top_queries_gb = GridOptionsBuilder.from_dataframe(top_queries_pda)
                top_queries_gb.configure_side_bar()
                top_queries_gb.configure_auto_height = False
                top_queries_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                top_queries_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                top_queries_gb.configure_column(field='CREDITS_USED', enablePivot=True, aggFunc='sum')
                top_queries_gb.configure_column(field='QUERY_COUNT', enablePivot=True, aggFunc='sum')
                high_wtmk_gb_options = top_queries_gb.build()
                AgGrid(top_queries_pda, gridOptions=high_wtmk_gb_options, enable_enterprise_modules=True)
                return top_queries_pda
        else:
            st.info('Top Queries : NO DATA')
            return pd.DataFrame()


def get_leading_key_data_type_data():
    leading_key_data_type_pda = db.get_leading_key_data_type(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(leading_key_data_type_pda) != 0:
            st.subheader("Leading key types")
            with st.expander("Analyze Leading Key Type Data"):
                top_queries_gb = GridOptionsBuilder.from_dataframe(leading_key_data_type_pda)
                top_queries_gb.configure_side_bar()
                top_queries_gb.configure_auto_height = False
                top_queries_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                top_queries_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                top_queries_gb.configure_column(field='CREDITS_USED', enablePivot=True, aggFunc='sum')
                top_queries_gb.configure_column(field='QUERY_COUNT', enablePivot=True, aggFunc='sum')
                high_wtmk_gb_options = top_queries_gb.build()
                AgGrid(leading_key_data_type_pda, gridOptions=high_wtmk_gb_options, enable_enterprise_modules=True)
                return leading_key_data_type_pda 
        else:
            st.info('Leading key type : NO DATA')
            return pd.DataFrame()

def get_pct_tables_clustered_data():
    pct_tables_clustered_pda = db.get_pct_tables_clustered(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(pct_tables_clustered_pda) != 0:
            st.subheader("Clustering Usage Information")
            autocluster_columns = st.columns(4)
            with autocluster_columns[0]:
                st.metric(label="Table Counts", value=pct_tables_clustered_pda['TABLE_COUNT'].values[0])
            with autocluster_columns[1]:
                st.metric(label="Clustered Table Count", value=pct_tables_clustered_pda['COUNT_CLUSTERED_TABLES'].values[0])
            with autocluster_columns[2]:
                st.metric(label="Percentage of tables with Auto_Clustering", value=f"{pct_tables_clustered_pda['PERCENT_TABLES_AUTO_CLUSTERED'].values[0]}%")
            with autocluster_columns[3]:
                st.metric(label="Percentage of tables with Explicit Clustering", value=f"{pct_tables_clustered_pda['PERCENT_TABLES_CLUSTERED'].values[0]}%")
            return pct_tables_clustered_pda
        else:
            st.info('Clustering Usage Information: NO DATA')
            return pd.DataFrame()

def get_pct_users_granted_system_role_data():
    pct_users_granted_system_role_pda = db.get_pct_users_granted_system_role(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(pct_users_granted_system_role_pda) != 0:
            st.subheader("Percent users granted built-in role")
            user_granted_sysrole_columns = st.columns(3)
            with user_granted_sysrole_columns[0]:
                st.metric(label="Number of Users", value=pct_users_granted_system_role_pda['NUM_USERS'].values[0])
            with user_granted_sysrole_columns[1]:
                st.metric(label="System Role Grants", value=pct_users_granted_system_role_pda['SYSTEM_ROLE_GRANTS'].values[0])
            with user_granted_sysrole_columns[2]:
                st.metric(label="Percent users granted built-in role", value=f"{pct_users_granted_system_role_pda['PCT_USERS_WITH_BUILT_IN_ROLE'].values[0]}%")
            return pct_users_granted_system_role_pda
        else:
            st.info('Percent users granted built-in role: NO DATA')
            return pd.DataFrame()


def get_num_cluster_keys_data():
    num_cluster_keys_pda = db.get_num_cluster_keys(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(num_cluster_keys_pda) != 0:
            st.subheader("Number of cluster keys")
            with st.expander("Analyze Number of Cluster Keys Data"):
                num_cluster_keys_gb = GridOptionsBuilder.from_dataframe(num_cluster_keys_pda)
                num_cluster_keys_gb.configure_side_bar()
                num_cluster_keys_gb.configure_auto_height = False
                num_cluster_keys_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                num_cluster_keys_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                num_cluster_keys_gb_options = num_cluster_keys_gb.build()
                AgGrid(num_cluster_keys_pda, gridOptions=num_cluster_keys_gb_options, enable_enterprise_modules=True)
                return num_cluster_keys_pda
        else:
            st.info('Number of Cluster Keys : NO DATA')
            return pd.DataFrame()


def get_pct_queueing_of_total_dur_by_warehouse_data():
    pct_queueing_of_total_dur_by_warehouse_pda = db.get_pct_queueing_of_total_dur_by_warehouse(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(pct_queueing_of_total_dur_by_warehouse_pda) != 0:
            st.subheader("Percent time queries spent queued")
            st.caption("Highlight an interval to filter graph below")
            brush = alt.selection_interval()
            total_exec_count= alt.Chart(pct_queueing_of_total_dur_by_warehouse_pda).mark_area(color='#29B5E8').encode(
                alt.X('HOUR:T', title='Date'),
                alt.Y('average(PCT_EXEC_QUEUED):Q', title="Average % time queued")
                ).add_selection(
                        brush
                ).properties(height=300,width=1100)
            details = alt.Chart(pct_queueing_of_total_dur_by_warehouse_pda).mark_bar(color='#11567F').encode(
                alt.Y('max(PCT_EXEC_QUEUED):Q', title="Max time spent queued"),
                alt.X('WAREHOUSE_NAME:N', title="Warehouse")
                ).transform_filter(
                    brush
                ).properties(height=300,width=1100)
            st.altair_chart(alt.vconcat(total_exec_count, details), use_container_width=True)
                
            with st.expander("Percent time queries spent queued Data"):
                pct_queueing_of_total_dur_by_warehouse_gb = GridOptionsBuilder.from_dataframe(pct_queueing_of_total_dur_by_warehouse_pda)
                pct_queueing_of_total_dur_by_warehouse_gb.configure_column(field="HOUR", type=["customDateTimeFormat"], custom_format_string="yyyy-MM-dd HH:mm")
                pct_queueing_of_total_dur_by_warehouse_gb.configure_side_bar()
                pct_queueing_of_total_dur_by_warehouse_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                pct_queueing_of_total_dur_by_warehouse_gb.configure_auto_height = False
                pct_queueing_of_total_dur_by_warehouse_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                pct_queueing_of_total_dur_by_warehouse_gb_options = pct_queueing_of_total_dur_by_warehouse_gb.build()
                AgGrid(pct_queueing_of_total_dur_by_warehouse_pda, gridOptions=pct_queueing_of_total_dur_by_warehouse_gb_options, enable_enterprise_modules=True)
                return pct_queueing_of_total_dur_by_warehouse_pda
        else:
            st.info('Percent time queries spent queued : NO DATA')
            return pd.DataFrame()


def get_invalid_mvs_data():
    invalid_mvs_pda = db.get_invalid_mvs(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(invalid_mvs_pda) != 0:
            st.subheader("Invalid Materialized Views")
            st.table(invalid_mvs_pda)
            return invalid_mvs_pda
        else:
            st.info('Invalid Materialized Views : NO DATA')
            return pd.DataFrame()


def get_mv_with_ac_source_data():
    mv_with_ac_source_pda = db.get_mv_with_ac_source(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(mv_with_ac_source_pda) != 0:
            st.subheader("Materialized View with auto-clustered Source")
            st.table(mv_with_ac_source_pda)
            return mv_with_ac_source_pda
        else:
            st.info('Materialized View with auto-clustered Source: NO DATA')
            return pd.DataFrame()

def get_poor_pruning_repetitive_jobs_data():
    poor_pruning_repetitive_jobs_pda = db.get_poor_pruning_repetitive_jobs(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(poor_pruning_repetitive_jobs_pda) != 0:
            st.subheader("Pruning of reoccuring jobs")
            
            worst_duration_query = poor_pruning_repetitive_jobs_pda.sort_values(by='AVG_DURATION_SEC',ascending=False).head(1)['AVG_DURATION_SEC'].values[0]
            worst_duration_qid = poor_pruning_repetitive_jobs_pda.sort_values(by='AVG_DURATION_SEC',ascending=False).head(1)['EXAMPLE_QUERY_ID'].values[0]
            worst_duration_count = poor_pruning_repetitive_jobs_pda.sort_values(by='AVG_DURATION_SEC',ascending=False).head(1)['EXECUTION_COUNT'].values[0]

            queries_scanning_100pct = poor_pruning_repetitive_jobs_pda.where(poor_pruning_repetitive_jobs_pda['AVG_FILE_SCAN_PERCENT'] > 74)
            
            st.write("Longest Average Duration for the last 7 days")
            worst_metric_columns = st.columns((1,2,1))
            with worst_metric_columns[0]:
                st.metric("Duration",worst_duration_query)
            with worst_metric_columns[1]:
                st.metric("Example Query ID",worst_duration_qid)
            with worst_metric_columns[2]:
                st.metric("Execution Count",worst_duration_count)
            
            st.write("Queries scanning more than 75% of files")
            scanning = st.columns((1,2,1))
            with scanning[0]:
                st.metric("Count of Unique Queries",str(queries_scanning_100pct['EXAMPLE_QUERY_ID'].count()))
            with scanning[1]:
                st.metric("Example Query ID",queries_scanning_100pct.sort_values(by='AVG_FILE_SCAN_PERCENT',ascending=False)['EXAMPLE_QUERY_ID'].head(1).values[0])
            with scanning[2]:
                st.metric("Sum Of Execution Counts",queries_scanning_100pct['EXECUTION_COUNT'].sum())
            
            with st.expander("Pruning of reoccuring jobs"):
                poor_pruning_repetitive_jobs_gb = GridOptionsBuilder.from_dataframe(poor_pruning_repetitive_jobs_pda)
                poor_pruning_repetitive_jobs_gb.configure_side_bar()
                poor_pruning_repetitive_jobs_gb.configure_auto_height = False
                poor_pruning_repetitive_jobs_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                poor_pruning_repetitive_jobs_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                poor_pruning_repetitive_jobs_gb_options = poor_pruning_repetitive_jobs_gb.build()
                AgGrid(poor_pruning_repetitive_jobs_pda, gridOptions=poor_pruning_repetitive_jobs_gb_options, enable_enterprise_modules=True)
                return poor_pruning_repetitive_jobs_pda
        else:
            st.info('Pruning of reoccuring jobs : NO DATA')
            return pd.DataFrame()

def get_avg_time_listing_external_files_data():
    avg_time_listing_external_files_pda = db.get_avg_time_listing_external_files(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(avg_time_listing_external_files_pda) != 0:
            st.subheader("Avg time spent listing external files")
            with st.expander("Avg time spent listing external files"):
                avg_time_listing_external_files_gb = GridOptionsBuilder.from_dataframe(avg_time_listing_external_files_pda)
                avg_time_listing_external_files_gb.configure_side_bar()
                avg_time_listing_external_files_gb.configure_auto_height = False
                avg_time_listing_external_files_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                avg_time_listing_external_files_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                avg_time_listing_external_files_gb_options = avg_time_listing_external_files_gb.build()
                AgGrid(avg_time_listing_external_files_pda, gridOptions=avg_time_listing_external_files_gb_options, enable_enterprise_modules=True)
                return avg_time_listing_external_files_pda
        else:
            st.info('Avg time spent listing external files : NO DATA')
            return pd.DataFrame()

def get_short_lived_permanent_tables_data():
    short_lived_permanent_tables_pda = db.get_short_lived_permanent_tables(
        st.session_state['snow_conn'],
        str(st.session_state['searchable_account_name']),
        str(st.session_state['searchable_account_deployment']))
    with st.container():
        if len(short_lived_permanent_tables_pda) != 0:
            st.subheader("High Turnover Tables")
            lifespan= alt.Chart(short_lived_permanent_tables_pda).mark_bar().encode(
                x='LIFESPAN_MINUTES:O',
                y='TABLES_IN_LIFESPAN',
                color='TABLE_TYPE'
                )
            st.altair_chart(lifespan, use_container_width=True)
            with st.expander("Analyze High Turnover Tables Data"):
                short_lived_permanent_tables_gb = GridOptionsBuilder.from_dataframe(short_lived_permanent_tables_pda)
                short_lived_permanent_tables_gb.configure_side_bar()
                short_lived_permanent_tables_gb.configure_auto_height = False
                short_lived_permanent_tables_gb.configure_selection(selection_mode="multiple", rowMultiSelectWithClick=True, use_checkbox=True)
                short_lived_permanent_tables_gb.configure_default_column(groupable=True, editable=False, enableRowGroup=True, enableValue=True, enablePivot=True, aggFunc='count')
                short_lived_permanent_tables_gb_options = short_lived_permanent_tables_gb.build()
                AgGrid(short_lived_permanent_tables_pda, gridOptions=short_lived_permanent_tables_gb_options, enable_enterprise_modules=True)
                return short_lived_permanent_tables_pda
        else:
            st.info('High Turnover Tables : NO DATA')
            return pd.DataFrame()

def disable_check():
    if 'auto_refresh' in st.session_state:
        st.session_state['execute_button_disabled'] = st.session_state['auto_refresh']
def select_all():
    if 'select_all' in st.session_state:
        st.session_state['defaults_override'] = st.session_state['select_all']

#----------------------------------------------------------------------
# Sidebar Initialize as Empty - 2 Empty Containers for Login and Menus"
#----------------------------------------------------------------------


sidebar = st.sidebar
login = sidebar.empty()
options_pane = sidebar.empty()

with sidebar:
    if 'is_connected' in st.session_state:
        with options_pane.container():
            st.image('resources/SNO-SnowflakeLogo_blue.png',
                    use_column_width=True)

            general_selection = st.multiselect("General",check_types['general'], default=general_defaults)
            clustering_selection = st.multiselect("Clustering", check_types['clustering'], default=clustering_defaults)
            data_loading_selection = st.multiselect("Data Loading", check_types['data_loading'], default=data_loading_defaults)
            security_selection = st.multiselect("Security", check_types['security'], default=security_defaults)
            workload_selection = st.multiselect("Workload", check_types['workload'], default=workload_defaults)
            all_checks = st.checkbox("Select All", key="select_all", on_change=select_all)
            st.text(st.session_state['connection_summary'])
            st.text(f'Version:{version_number}')

        selected_checks = []
        selected_checks.extend(general_selection)
        selected_checks.extend(clustering_selection)
        selected_checks.extend(data_loading_selection)
        selected_checks.extend(security_selection)
        selected_checks.extend(workload_selection)

        #GENERATE MARKDOWN LIST
        list = ''
        for x in selected_checks:
            list += '\n - ' + x

    else:
        options_pane.empty()
        with login.container():
            st.image('resources/SNO-SnowflakeLogo_blue.png',
                    use_column_width=True)
            st.session_state['username'] = st.text_input("Username")

            st.session_state['selected_role'] = st.selectbox(
                "Role", ['TECHNICAL_ACCOUNT_MANAGER', 'SOLUTION_ARCHITECT'])
            login = st.button("Connect")
            if login:
                if st.session_state['username'] == "":
                    st.error("Please provide username")
                else:
                    st.session_state['snow_conn'] = db.connect_to_snowflake(
                        st.session_state['username'],
                        st.session_state['selected_role'])
                    try:
                        st.session_state[
                            'connection_details'] = db.get_connection_details(
                                st.session_state['snow_conn'])
                        st.session_state['is_connected'] = True
                    except None as e:
                        print(e)
                    finally:
                        if 'connection_details' in st.session_state:
                            st.session_state['is_connected'] = True
                            st.experimental_rerun()



#----------------------------------------------------------------------
# This code gets executed on every refresh to keep list updated
#----------------------------------------------------------------------
#SUMMARY PARSING


if 'execute_button_disabled' not in st.session_state:
    st.session_state['execute_button_disabled'] = True
if 'auto_refresh_disabled' not in st.session_state:
    st.session_state['auto_refresh_disabled'] = True

#----------------------------------------------------------------------
# Main Layout - Accounty Selection dropdown and Account Information
#----------------------------------------------------------------------
information, left_info = st.columns((2,1))
with information:
    st.session_state['account_filters'] = st.text_input(
        "Add Account or Organization Filter")
    filter_acct = st.button("Filter", disabled = st.session_state['disable_button'])
    if filter_acct:
        st.session_state['account_filter_list'] = create_account_filters()
        if len(st.session_state['account_filters'].strip()) > 0:
            st.session_state['all_accounts_map'] = get_account_selector(st.session_state['account_filter_list'])
            if 'all_accounts_map' in st.session_state:
                st.session_state['org_list'] = pd.Series(st.session_state['all_accounts_map']["OFFICIAL_ORG_NAME"].unique())
                st.session_state['org_list'] = pd.concat([pd.Series([' ']),st.session_state['org_list']])
        else:
            st.error("Please enter filter.")
    st.session_state['org_selected'] = st.selectbox(
        "Select an Organization", st.session_state['org_list'], index=0, on_change=filter_accounts_selector, key='current_org')
    st.session_state['account_selected'] = st.selectbox("Select your account", st.session_state['client_list'], index=0)
    if selected_checks != []:
        st.caption("Selected Checks:")
        st.markdown(list)
        st.write("---")
        
        if st.session_state['account_selected'] == None:
            st.error("Please select account")
            st.session_state['execute_button_disabled'] = True
            st.session_state['auto_refresh_disabled'] = True
        else:
            st.session_state['execute_button_disabled'] = st.session_state['auto_refresh']
            st.session_state['auto_refresh_disabled'] = False

if 'is_connected' in st.session_state:
    execute = st.button("Execute", disabled=st.session_state['execute_button_disabled'])
    st.session_state['auto_refresh_enabled'] = st.checkbox("Auto Refresh", on_change= disable_check, key="auto_refresh", disabled=st.session_state['auto_refresh_disabled'])
    if execute or st.session_state['auto_refresh_enabled'] == True:
        generate_streams()

    st.experimental_set_query_params(
        is_connected = st.session_state['is_connected'],
        username= st.session_state['username'],
        role = st.session_state['selected_role']
    )

