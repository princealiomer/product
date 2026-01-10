import pandas as pd
import glob
import os

try:
    # Find the most recent export file
    list_of_files = glob.glob(r'd:\product hunt\final files\*_export.csv') 
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"Reading: {latest_file}")
    
    df = pd.read_csv(latest_file)
    print("Columns:")
    print(df.columns.tolist())
    
    print("\nRow Count:", len(df))
    
    if len(df) > 0:
        print("\nSample Row 1 Reviewer:")
        print(df.iloc[0].get('reviewer_name'))
        print("\nSample Row 1 Rating:")
        print(df.iloc[0].get('rating'))
except Exception as e:
    print(e)
