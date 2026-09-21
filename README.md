# Dubai Real Estate Intelligence Platform

A professional portfolio project that will use official Dubai Land Department transaction data to develop practical skills in data preparation, database workflows, and business reporting. The project is being built one stage at a time, with a reproducible foundation established before later analytical work.

## Project objective

The long-term objective is to build a documented workflow for working with Dubai real estate transaction data, from validating source files to preparing data, storing it in MySQL, and creating reports in Excel and Power BI. These activities are planned for future stages.

## Current project status

**Stage 1 – Project Setup**

This stage includes the project folder structure, an initial dependency list, and a read-only raw-data validation script. Data cleaning, analysis, visualization, SQL database creation, machine learning, and Power BI work have not been performed.

## Official data source

**Dubai Land Department (DLD)** is the intended official data source. Use a small sample obtained from an official DLD source and place it at:

```text
data/raw/dld_transactions_sample_2026_01.csv
```

The sample provided locally as `dld_transactions_sample_2026_01.csv.csv` has been copied byte-for-byte to the path above; the original file is unchanged. No transaction records were generated or downloaded as part of this setup. The file's official provenance has not been independently verified. Record its official source URL and download date in `docs/` when available.

The raw sample is intentionally not excluded by `.gitignore` so that a small official sample can support portfolio reproducibility.

## Planned technology stack

| Technology | Planned purpose |
| --- | --- |
| Official DLD data | Source transaction records |
| Excel | Spreadsheet review and reporting |
| Python and Pandas | Validation and future data preparation and analysis |
| MySQL | Structured data storage and querying |
| Power BI and DAX | Future dashboards and measures |
| Git and GitHub | Version control and portfolio documentation |

## Project folder structure

```text
.
├── data/
│   ├── raw/
│   │   └── dld_transactions_sample_2026_01.csv
│   ├── processed/
│   └── external/
├── notebooks/
├── src/
│   └── 01_validate_raw_data.py
├── sql/
├── excel/
├── powerbi/
├── reports/
├── docs/
├── images/
├── README.md
├── .gitignore
├── requirements.txt
└── LICENSE
```

Empty directories contain `.gitkeep` placeholders so Git can retain the folder structure. The `processed/`, `sql/`, `excel/`, `powerbi/`, and other output folders are reserved for later stages.

## Set up the environment

Run the following commands from the project root in a macOS or Linux terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The requirements file includes the initial project dependencies. Installing them does not create a database or perform any data processing.

## Validate the raw sample

After placing the official sample at the expected path, run:

```bash
python src/01_validate_raw_data.py
```

The script prints the file name and size, row and column counts, all column names, the first five rows, Pandas data types, duplicate-row count, and missing-value counts and percentages for every column. It tries UTF-8 first and uses a fallback encoding if needed. If the file is missing, it explains where to place it.

Validation reads the CSV without modifying it or writing a processed dataset. The output is an initial check of the file's structure and completeness; it does not establish the accuracy of individual transactions or provide market findings.

## License

The project code is provided under the MIT License in `LICENSE`. Any source data remains subject to the terms specified by its official provider.
