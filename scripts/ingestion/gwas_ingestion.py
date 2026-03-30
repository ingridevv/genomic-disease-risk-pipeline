# %%
import pandas as pd
import requests
import csv
import zipfile

# %%
GWAS_URL = "https://www.ebi.ac.uk/gwas/api/search/downloads/associations/v1.0?split=false"
P_VALUE_THRESHOLD = 5e-8
KEYWORDS_IBD = "crohn|colitis|inflammatory bowel"

# %%
def download_gwas_file(url, filename="raw_gwas.zip"):
    """Download GWAS Data directly"""
    filename = "data/bronze/raw_gwas.zip"
    print(f"Downloading to {filename}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return filename

# %%
def extract_tsv_from_zip(zip_filepath):
    """Open the ZIP directly and return the first TSV file found."""
    z = zipfile.ZipFile(zip_filepath)
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
def preprocess_genomic(chunk):
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
def filter_by_phenotype(chunk, keywords):
    """Filter IBD-related diseases"""
    return chunk[
        chunk["DISEASE/TRAIT"].str.contains(keywords, case=False, na=False)
    ]

# %%
def filter_significant_threshold(chunk, threshold):
    """Apply GWAS statistical significance threshold"""
    return chunk[chunk["P-VALUE"] < threshold]

# %%
def aggregate_results(results):
    """Combine all processed chunks"""
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
    print("Ingestion started...")
    results_gold = []

    zip_filepath = download_gwas_file(GWAS_URL)
    file_obj = extract_tsv_from_zip(zip_filepath)

    with zipfile.ZipFile(zip_filepath) as z:
        file_name = z.namelist()[0]
        with z.open(file_name) as file_obj:
            for i, chunk in enumerate(read_gwas_chunks(file_obj)):
                print(f"Processing chunk {i}")
                
                chunk_silver = preprocess_genomic(chunk)
                if chunk_silver.empty: continue

                chunk_ibd = filter_by_phenotype(chunk_silver, KEYWORDS_IBD)
                if chunk_ibd.empty: continue

                chunk_gold = filter_significant_threshold(chunk_ibd, P_VALUE_THRESHOLD)
                if chunk_gold.empty: continue

                results_gold.append(chunk_gold)

    if results_gold:
        final_df = aggregate_results(results_gold)
 
        print("\nTop Genes Encountered:")
        print(final_df["MAPPED_GENE"].value_counts().head(10))

        output_path = "data/gold/gwas_ibd_cleaned.csv"

        final_df.to_csv(output_path, index=False)

        print(f"\n File saved in gold layer: {output_path}")
        print(f"Total variants filtered: {len(final_df)}")

        return final_df
    else:
        print("No data found with the applied filters")
        return None
    
if __name__ == "__main__":
    main()