import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import logging
from dotenv import load_dotenv
from snowflake.connector import connect, Error as SnowflakeError

# ==========================================
# 1. CORE CONFIGURATION & LOGGING
# ==========================================
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("GenomicAgnosticPipeline")

# ==========================================
# 2. DATA ACCESS LAYER (PARAMETERIZED)
# ==========================================
class SnowflakeConnector:
    """Manages secure connections and parameterized data retrieval from Snowflake."""
    
    @staticmethod
    @st.cache_data(ttl=3600)
    def fetch_data(table_name: str) -> pd.DataFrame:
        """Fetches data from a specific table, keeping the logic agnostic of the source name."""
        logger.info(f"Connecting to Snowflake to retrieve: {table_name}")
        try:
            conn = connect(
                user=os.getenv("SF_USER"),
                password=os.getenv("SF_PASSWORD"),
                account=os.getenv("SF_ACCOUNT"),
                warehouse=os.getenv("SF_WAREHOUSE"),
                database=os.getenv("SF_DATABASE"),
                schema=os.getenv("SF_GOLD_LAYER"),
                role=os.getenv("SF_ROLE")
            )
            
            query = f"SELECT * FROM {table_name}"
            df = pd.read_sql(query, conn)
            
            # Ensure columns are uppercase for consistent internal mapping
            df.columns = [col.upper() for col in df.columns]
            return df
            
        except SnowflakeError as se:
            logger.error(f"Database error: {se}")
            raise Exception(f"Could not reach {table_name}. Verify Snowflake credentials.")
        except Exception as e:
            logger.error(f"System error: {e}")
            raise

# ==========================================
# 3. BIOINFORMATICS LOGIC LAYER
# ==========================================
class GenomicProcessor:
    """Handles genomic transformations and human-readable translations."""
    
    @staticmethod
    def apply_transformations(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        # Significance Calculation
        if 'P_VALUE' in df.columns and 'MINUS_LOG10_P' not in df.columns:
            df['MINUS_LOG10_P'] = -np.log10(df['P_VALUE'].replace(0, 1e-300))
        
        # Chromosome Order
        chrom_order = [str(i) for i in range(1, 23)] + ['X', 'Y']
        df['CHROMOSOME'] = pd.Categorical(df['CHROMOSOME'].astype(str), categories=chrom_order, ordered=True)
        
        return df.sort_values(['CHROMOSOME', 'POSITION'])

    @staticmethod
    def translate_impact(gene: str, function: str) -> str:
        """Explains the significance of top genes for non-specialist stakeholders."""
        func = str(function).lower()
        if "immune" in func or "cytokine" in func:
            return f"Regulates inflammatory response; variants in {gene} can trigger immune overreaction."
        if "barrier" in func or "epithelial" in func:
            return f"Maintains gut wall integrity; defects here lead to increased tissue sensitivity."
        if "autophagy" in func:
            return f"Cellular waste disposal; failures lead to toxic buildup in the gut."
        return "Associated with signaling pathways that influence the progression of the trait."

# ==========================================
# 4. VISUALIZATION LAYER (SLATE & TEAL PALETTE)
# ==========================================
class GenomicCharts:
    """Professional plots with customized scales and a slate/teal palette."""
    
    COLOR_A = "#2C3E50"   # Dark Slate
    COLOR_B = "#5A7D9A"   # Muted Blue
    COLOR_SIG = "#1ABC9C" # Calm Teal for Significance Line
    
    @classmethod
    def manhattan_plot(cls, df: pd.DataFrame, threshold: float):
        """High-resolution Manhattan plot with increased vertical scale."""
        fig = px.scatter(
            df, x='CHROMOSOME', y='MINUS_LOG10_P', color='CHROMOSOME',
            color_discrete_sequence=[cls.COLOR_A, cls.COLOR_B] * 12,
            hover_name='MAPPED_GENE',
            hover_data={'CHROMOSOME': False, 'POSITION': ':.0f', 'MINUS_LOG10_P': ':.2f', 'ODDS_RATIO': ':.2f'},
            title="Genome-Wide Association Landscape",
            template="plotly_white",
            height=700 
        )
        # Teal Significance Line
        fig.update_traces(marker=dict(size=10, opacity=0.7, line=dict(width=0.5, color='White')))

        fig.add_hline(y=threshold, line_dash="dot", line_color=cls.COLOR_SIG, 
                      annotation_text="Significance Level", annotation_font_color=cls.COLOR_SIG)
        
        fig.update_layout(showlegend=False, xaxis_title="Chromosome", yaxis_title="-log10(p-value)")
        return fig

# ==========================================
# 5. ORCHESTRATION LAYER (UI/UX)
# ==========================================

def main():

    # --- PARAMETERIZATION BLOCK ---
    target_table = "FCT_GWAS_ANALYSIS"
    phenotype_name = "IBD"
    # ------------------------------

    st.set_page_config(page_title="Genomic Intelligence for IBD", layout="wide")
    
    # Custom CSS for Professional Presentation
    st.markdown("""
    <style>
        /* 1. GLOBAL LAYOUT: Positioning and Spacing */
        .main { 
            background-color: #FAFAFA; 
        }
        
        .block-container {
            padding-top: 2.5rem !important; /* Prevents overlap with Streamlit top bar */
            padding-bottom: 0rem !important;
        }

        [data-testid="stHeader"] {
            height: 0px;
            background: transparent;
        }

        /* 2. ADAPTIVE METRICS: Cards that flip for Dark/Light mode */
        div[data-testid="stMetric"] {
            background-color: var(--secondary-background-color); 
            border: 1px solid var(--border-color);
            padding: 15px;
            border-radius: 10px;
            border-left: 5px solid #2C3E50; /* Slate Navy branding */
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        div[data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            border-color: #1ABC9C; /* Teal highlight */
            box-shadow: 0 6px 16px rgba(0,0,0,0.1);
        }

        /* 3. METRIC TEXT: Ensuring long trait names wrap properly */
        div[data-testid="stMetricLabel"] > div {
            color: var(--text-color);
            font-weight: 500;
        }
        
        div[data-testid="stMetricValue"] > div {
            color: var(--text-color);
            font-size: 1.6rem !important;
            white-space: normal !important; 
            word-break: break-word !important;
            line-height: 1.2;
        }

        /* 4. HEADER ACTIONS: Vertical alignment for the Title + Status row */
        [data-testid="column"] {
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0px !important;
        }

        .header-right-container {
            display: flex;
            justify-content: flex-end; /* Pushes the pill to the right */
            align-items: center;
            width: 100%;
        }

        .status-pill {
            display: flex;
            align-items: center;
            padding: 5px 12px;
            border-radius: 20px;
            background-color: rgba(26, 188, 156, 0.1);
            border: 1px solid #1ABC9C;
            color: #1ABC9C;
            font-size: 0.8rem;
            font-weight: 600;
            white-space: nowrap;
        }

        /* Target the button specifically to match the pill height */
        div[data-testid="column"] button {
            width: 100% !important; /* Fills its small 0.4 column */
            height: 32px !important;
            padding: 0px !important;
            font-size: 0.8rem !important;
            border-radius: 8px !important;
            border: 1px solid var(--border-color) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Minimalist DNA Double Helix SVG Icon
    dna_icon = '''<svg width="80px" height="80px" viewBox="0 0 36.00 36.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" aria-hidden="true" role="img" class="iconify iconify--twemoji" preserveAspectRatio="xMidYMid meet" fill="#000000" stroke="#000000" stroke-width="0.00036"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"><path fill="#77B255" d="M3.019 26.246l3.432 3.432l-.923.922l-3.432-3.431z"></path><path fill="#FFD983" d="M6.362 29.587l3.431 3.432l-.923.923l-3.43-3.432z"></path><path fill="#FFAC33" d="M6.273 24.237l3.432 3.432l-.923.923L5.35 25.16z"></path><path fill="#EA596E" d="M8.998 26.962l3.432 3.432l-.923.923l-3.431-3.432zm3.909-9.359l3.431 3.432l-.923.923l-3.431-3.432z"></path><path fill="#FFAC33" d="M15.631 20.329l3.432 3.431l-.923.923l-3.432-3.431z"></path><path fill="#77B255" d="M14.97 14.377l3.432 3.432l-.922.923l-3.432-3.432z"></path><path fill="#FFD983" d="M18.277 17.683l3.432 3.432l-.923.923l-3.432-3.432z"></path><path fill="#FFAC33" d="M17.616 11.731l3.432 3.432l-.923.922l-3.432-3.431z"></path><path fill="#EA596E" d="M20.923 15.038l3.432 3.431l-.923.923l-3.431-3.432zM24.387 4.96l3.432 3.432l-.923.922l-3.432-3.431z"></path><path fill="#FFAC33" d="M27.694 8.267l3.432 3.431l-.923.923l-3.432-3.432z"></path><path fill="#77B255" d="M27.013 2.252l3.432 3.432l-.923.923l-3.432-3.432z"></path><path fill="#FFD983" d="M30.36 5.6l3.432 3.431l-.923.923l-3.432-3.431z"></path><path fill="#20bc8d" d="M24.922.812c-2.52 2.52-2.601 6.145-2.396 9.806c.501.028 1.002.061 1.502.094c.39.026.775.051 1.159.074c-.198-3.286-.199-6.299 1.606-8.104c.727-.703.955-1.653.447-2.166c-.535-.54-1.542-.497-2.318.296z"></path><path fill="#3B88C3" d="M13.146 25.65l-.153-2.66c-.026-.445-.058-.899-.074-1.332c-.296-.296-2.466-.349-2.653-.162c.013.44.047.884.071 1.327c.028.502.126 2.275.149 2.66c.054.91.096 1.806.086 2.656c.259.259 2.371.437 2.645.162a36.931 36.931 0 0 0-.071-2.651z"></path><path fill="#55ACEE" d="M13.22 28.3l-2.649-.162c-.026 2.209-.384 4.145-1.687 5.448a1.322 1.322 0 1 0 1.87 1.871c2.423-2.422 2.467-7.174 2.466-7.157z"></path><path fill="#20bc8d" d="M25.354 13.447c-.501-.028-1.003-.061-1.503-.094c-.389-.026-.775-.051-1.158-.074c.198 3.285.199 6.299-1.607 8.104c-1.804 1.804-4.813 1.805-8.094 1.607c-.386-.023-2.159-.14-2.656-.168c-3.667-.206-7.297-.126-9.82 2.397a1.322 1.322 0 0 0 1.871 1.87c1.805-1.804 4.815-1.806 8.098-1.608c.385.023 2.161.14 2.66.168c3.662.205 7.289.125 9.811-2.396c2.521-2.52 2.603-6.145 2.398-9.806z"></path><path fill="#00c288" d="M25.354 13.447c-.028-.501-.145-2.277-.168-2.66a51.95 51.95 0 0 1-.064-1.332c-.336-.021-2.1-.133-2.653-.163c.013.44.032.883.056 1.326c.028.501.145 2.277.168 2.661c.055.914.091 1.804.081 2.656c.333.021 2.094.132 2.645.162a36.316 36.316 0 0 0-.065-2.65z"></path><path fill="#55ACEE" d="M35.581 8.827c-.42-.436-1.385-.601-2.291.353c-1.805 1.805-4.817 1.806-8.104 1.607c-.384-.023-2.16-.141-2.661-.169c-3.66-.205-7.286-.123-9.806 2.397c-2.215 2.215-2.545 5.284-2.453 8.48c.553.03 2.319.142 2.653.162c-.098-2.755.113-5.214 1.671-6.772c1.805-1.805 4.818-1.805 8.104-1.607c.383.023 2.16.14 2.661.168c3.661.205 7.286.124 9.806-2.396c.886-.869.84-1.787.42-2.223z"></path></g></svg>'''
    
    # st.markdown(f"<h1>{dna_icon} Genomic Intelligence for {phenotype_name}</h1>", unsafe_allow_html=True)

    head_col1, head_col2 = st.columns([2, 1], vertical_alignment="center")

    with head_col1:
        # Using the DNA icon and the phenotype-specific title
        st.markdown(f"## {dna_icon} Genomic Intelligence for IBD", unsafe_allow_html=True)
        st.caption("Data Source: Snowflake Gold Layer • Last Sync: April 2026")

    with head_col2:
        # Use nested columns to force them onto one line
        # Ratio [1, 0.4] gives the pill more room and keeps the button small
        action_col1, action_col2 = st.columns([1, 0.4], vertical_alignment="center")
        
        with action_col1:
            # Wrap the pill in a div to apply your custom CSS
            st.markdown('<div class="header-right-container"><div class="status-pill">● System Online</div></div>', unsafe_allow_html=True)
        
        with action_col2:
            # No 'use_container_width' here so it stays compact
            if st.button("🔄 Refresh"):
                st.cache_data.clear()
                st.rerun()
    

    with st.expander("🛠️ Pipeline Infrastructure & Lineage"):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**Source Layer**")
            st.code("SNOWFLAKE_RAW.GWAS_CATALOG", language="sql")
        with col_b:
            st.markdown("**Transformation**")
            st.code("dbt Cloud (fct_gwas_analysis)", language="sql")
        with col_c:
            st.markdown("**Environment**")
            st.caption("🟢 GCP GKE Deployment")
        
        # This adds a nice visual touch to represent your dbt DAG
        st.caption("Data Flow: Raw GWAS Catalog Associations → Snowflake Bronze → dbt Silver → Gold (Production)")

    # Initialization
    try:
        raw_data = SnowflakeConnector.fetch_data(table_name=target_table)
        df = GenomicProcessor.apply_transformations(raw_data)
    except Exception as e:
        st.error(f"Execution Error: {e}"); st.stop()

    # --- SIDEBAR FILTERS ---
    with st.sidebar:
        #st.markdown(f"<div style='text-align: center'>{dna_icon}</div>", unsafe_allow_html=True)
        st.header("Pipeline Controls")

        # Gene Filter
        genes = sorted(df['MAPPED_GENE'].dropna().unique()) if 'MAPPED_GENE' in df.columns else []
        sel_genes = st.multiselect("Mapped Genes", options=genes)

        # P-Value Threshold
        p_val_threshold = st.slider("Significance Level (-log10)", 0.0, 20.0, 7.3)
        
        # Disease Trait Filter (Agnostic/Parameterized)
        traits = sorted(df['PHENOTYPE'].dropna().unique()) if 'PHENOTYPE' in df.columns else []
        sel_traits = st.multiselect("Disease Traits", options=traits, default=traits)
        
        # Chromosome Filter
        chroms = sorted(df['CHROMOSOME'].dropna().unique(), key=lambda x: str(x))
        sel_chroms = st.multiselect("Chromosomes", options=chroms, default=chroms)
            

    # --- FILTERING LOGIC ---
    mask = (df['MINUS_LOG10_P'] >= p_val_threshold)
    if sel_traits:
        mask = mask & (df['PHENOTYPE'].isin(sel_traits))
    if sel_chroms:
        mask = mask & (df['CHROMOSOME'].isin(sel_chroms))
    if sel_genes:
        mask = mask & (df['MAPPED_GENE'].isin(sel_genes))
        
    filtered_df = df[mask]

    # Metrics
    m1, m2, m3, m4 = st.columns([1, 1, 1, 2])
    m1.metric("Analyzed Markers", f"{len(df):,}")
    m2.metric("Significant Loci", f"{len(filtered_df):,}")
    m3.metric("Peak Odds Ratio", f"{filtered_df['ODDS_RATIO'].max():.2f}x" if not filtered_df.empty else "1.0x")
    m4.metric("Leading Trait", str(filtered_df['PHENOTYPE'].mode()[0]) if not filtered_df.empty else "N/A")

    st.markdown("---")
    
    # Large Manhattan Plot
    st.plotly_chart(GenomicCharts.manhattan_plot(filtered_df, p_val_threshold), use_container_width=True)

    if not filtered_df.empty and sel_genes:
        st.markdown("---")
        st.subheader("🧠 Research Context: Selected Loci")
        
        # We create a nice 'Obsidian-style' note for the first selected gene
        target_gene = sel_genes[0] 
        gene_info = filtered_df[filtered_df['MAPPED_GENE'] == target_gene].iloc[0]
        
        st.info(f"""
        **Gene Focus: {target_gene}** This variant on Chromosome {gene_info['CHROMOSOME']} shows a significance of {gene_info['MINUS_LOG10_P']:.2f}.  
        In the context of **{phenotype_name}**, this locus is typically associated with: *{gene_info['GENE_FUNCTION']}*.
        """)

    # --- EXECUTIVE INSIGHTS (PLAIN ENGLISH) ---
    st.markdown("---")
    st.subheader("Summary Statistics: Genetic Drivers")
    st.write("Translation of the top findings into clinical impact for non-technical stakeholders.")
    
    if not filtered_df.empty:
        top_loci = filtered_df.nlargest(3, 'MINUS_LOG10_P')
        insight_data = []
        for _, row in top_loci.iterrows():
            insight_data.append({
                "Gene Symbol": row['MAPPED_GENE'],
                "Significance": "Extremely High" if row['MINUS_LOG10_P'] > 12 else "High",
                "Impact Summary (Non-Expert)": GenomicProcessor.translate_impact(row['MAPPED_GENE'], row['GENE_FUNCTION'])
            })
        st.table(pd.DataFrame(insight_data))
    else:
        st.warning("Adjust filters to view insights.")

    # --- MAPPED GENES LEDGER (TECHNICAL DETAILS) ---
    st.markdown("---")
    st.subheader("Mapped Genes & Variant Ledger")
    st.write("Detailed functional context for detected associations.")
    
    technical_cols = ['MAPPED_GENE', 'CHROMOSOME', 'POSITION', 'ODDS_RATIO', 'MINUS_LOG10_P', 'GENE_FUNCTION', 'PHENOTYPE']
    technical_cols = [c for c in technical_cols if c in filtered_df.columns]
    
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Filtered Ledger to CSV",
        data=csv,
        file_name=f"{phenotype_name}_genomic_export.csv",
        mime='text/csv',
    )

    st.dataframe(
        filtered_df[technical_cols].sort_values('MINUS_LOG10_P', ascending=False),
        use_container_width=True,
        hide_index=True
    )

if __name__ == "__main__":
    main()