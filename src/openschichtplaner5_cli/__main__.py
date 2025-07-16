import argparse
import os
from pathlib import Path
from libopenschichtplaner5.registry import load_table, TABLE_NAMES


def main():
    parser = argparse.ArgumentParser(
        description="OpenSchichtplaner5 CLI – Read tables from DBF files"
    )
    parser.add_argument(
        "--table",
        required=True,
        choices=TABLE_NAMES,
        help="Name of the table to load"
    )
    parser.add_argument(
        "--dir",
        required=True,
        type=Path,
        help="Directory containing the DBF files"
    )

    args = parser.parse_args()
    table_name = args.table
    dbf_dir = args.dir

    # Build the expected file name with .dbf extension
    expected_filename = f"{table_name}.DBF"

    # Check if the file exists in the directory
    dbf_path = dbf_dir / expected_filename

    if not dbf_path.exists():
        print(f"❌ No DBF file found for table '{table_name}' in the directory.")
        return

    try:
        # Load the table using the corresponding loader function
        table = load_table(table_name, dbf_path)
    except Exception as e:
        print(f"❌ Error loading table '{table_name}': {e}")
        return

    # Print out the loaded table rows
    for row in table:
        print(row)


if __name__ == "__main__":
    main()
