import pandas as pd
from io import BytesIO

def to_excel(df):
    """Converts a DataFrame to an Excel file in memory."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Extracted Data')
    return output.getvalue()
