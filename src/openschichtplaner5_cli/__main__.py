import argparse
import os
from pathlib import Path
from dbfread import DBF
from libopenschichtplaner5.registry import load_table, TABLE_NAMES
from libopenschichtplaner5.cross_reference import load_all_tables, filter_notes_by_employee_id

def print_fields_and_types(dbf_path: Path):
    dbf = DBF(dbf_path)
    print(f"\nFields and Types in {dbf_path}:")
    for field in dbf.fields:
        print(f"  - {field.name}: {field.type}")

def main():
    parser = argparse.ArgumentParser(
        description="OpenSchichtplaner5 CLI – Read single DBF table filtered by employee_id"
    )
    parser.add_argument(
        "--dir",
        required=True,
        type=Path,
        help="Directory containing the DBF files"
    )
    parser.add_argument(
        "--table",
        required=True,
        choices=TABLE_NAMES,
        help="Name of the table to load"
    )
    parser.add_argument(
        "--employee-id",
        required=False,
        type=int,
        help="Filter results by specific employee ID"
    )

    args = parser.parse_args()
    dbf_dir = args.dir
    table_name = args.table
    dbf_path = dbf_dir / f"{table_name}.DBF"

    if not dbf_path.exists():
        print(f"❌ No DBF file found for table '{table_name}' in the directory.")
        return

    print(f"\nProcessing file: {dbf_path}")
    print_fields_and_types(dbf_path)

    try:
        table = load_table(table_name, dbf_path)
        if args.employee_id and table_name == "5NOTE":
            table = filter_notes_by_employee_id(table, args.employee_id)
        for row in table:
            print(row)
    except Exception as e:
        print(f"❌ Error loading table '{table_name}': {e}")

if __name__ == "__main__":
    main()
