import pandas as pd
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Excel",
    dependencies=["pandas"]
)

@mcp.tool()
def read_excel(file_path: str, sheet_name: str = None) -> pd.DataFrame:
    """
    Read an Excel file and return its content as a pandas DataFrame.
    
    Args:
        file_path (str): Path to the Excel file.
        sheet_name (str, optional): Name or index of the sheet to read. 
                                   If None, reads the first sheet by default.
    
    Returns:
        pd.DataFrame: DataFrame containing the Excel sheet data.
        
    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the specified sheet does not exist in the Excel file.
    """
    try:
        # If sheet_name is None, pandas will read the first sheet by default
        if sheet_name is None:
            print(f"No specific sheet requested. Reading the first sheet from {file_path}")
            return pd.read_excel(file_path, engine="openpyxl")
        else:
            print(f"Reading sheet '{sheet_name}' from {file_path}")
            return pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found at path: {file_path}")
    except ValueError as e:
        if "No sheet named" in str(e):
            raise ValueError(f"Sheet '{sheet_name}' not found in the Excel file.")
        raise e
    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")

if __name__ == "__main__":
    mcp.run()