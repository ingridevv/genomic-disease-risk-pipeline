# %%
import pandas as pd
import requests
import csv

# %%
GWAS_URL = "https://www.ebi.ac.uk/gwas/api/search/downloads/associations/v1.0?split=false"
P_VALUE_THRESHOLD = 5e-8
KEYWORDS_IBD = "crohn|colitis|inflammatory bowel"

# %%
def download_gwas_file(url):
    "Dowload GWAS Data (zip)"
    response = requests.get(url)
    response.raise_for_status()
    return response.content

# %%
def extract_tsv_from_zip(zip_content):
    """Extract TSV file from zip content"""
    import zipfile
    import io

    with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
        file_name = z.namelist()[0] 
        return z.open(file_name)

# %%
def read_gwas_chunks(url):
    """Read GWAS data in chunks"""
    return pd.read_csv(
        url,
        sep="\t",
        encoding="latin1",
        quoting=csv.QUOTE_NONE,
        on_bad_lines="skip",
        engine="python",
        chunksize=100_000
    )

# %%
def clean_chunk(chunk):
    """Clean raw GWAS data"""

    chunk = chunk.copy()

    chunk.columns = (
        chunk.columns
        .str.strip()
        .str.upper()
        .str.replace(" ", "")
    )

    required_cols = ["DISEASE/TRAIT", "P-VALUE"]
    for col in required_cols:
        if col not in chunk.columns:
            return pd.DataFrame()

    chunk["P-VALUE"] = pd.to_numeric(chunk["P-VALUE"], errors="coerce")
    chunk = chunk.dropna(subset=["P-VALUE", "DISEASE/TRAIT"])

    return chunk

# %%
def filter_ibd(chunk, keywords):
    """Filter IBD-related diseases"""
    return chunk[
        chunk["DISEASE/TRAIT"].str.contains(keywords, case=False, na=False)
    ]

# %%
def filter_significant(chunk, threshold):
    """Apply GWAS statistical significance threshold"""
    return chunk[chunk["P-VALUE"] < threshold]

# %%
def aggregate_results(results):
    """Combine all processed chunks"""
    import pandas as pd
    return pd.concat(results, ignore_index=True)

# %%
def top_ibd_genes(df, top_n=10):
    "Most frequent genes in the filtered dataset"
    return df['MAPPED_GENE'].value_counts().head(top_n)

# %%
def save_data(df, filename="gwas_ibd_cleaned.csv"):
    "Save final results for analysis"
    df.to_csv(filename, index=False)
    print(f"Saved as: {filename}")

# %%
def main():
    results = []

    zip_content = download_gwas_file(GWAS_URL)
    file_obj = extract_tsv_from_zip(zip_content)

    for i, chunk in enumerate(read_gwas_chunks(file_obj)):
        print(f"Processing chunk {i}")

        chunk = clean_chunk(chunk)
        if chunk.empty:
            continue

        chunk = filter_ibd(chunk, KEYWORDS_IBD)
        if chunk.empty:
            continue

        chunk = filter_significant(chunk, P_VALUE_THRESHOLD)
        if chunk.empty:
            continue

        results.append(chunk)

    if not results:
        print("No data found after filtering.")
        return None

    final_df = aggregate_results(results)

    print("\nTop Genes Encountered:")
    print(final_df["MAPPED_GENE"].value_counts().head(10))

    save_data(final_df)

    return final_df