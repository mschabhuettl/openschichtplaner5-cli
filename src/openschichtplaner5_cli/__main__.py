import argparse
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
        "--file",
        required=True,
        type=Path,
        help="Path to the DBF file"
    )

    args = parser.parse_args()
    table_name = args.table
    dbf_path = args.file

    try:
        table = load_table(table_name, dbf_path)
    except Exception as e:
        print(f"❌ Error loading table '{table_name}': {e}")
        return

    for row in table:
        print(row)


if __name__ == "__main__":
    main()
