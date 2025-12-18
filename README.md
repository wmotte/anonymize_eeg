# EEG Data Anonymization Tool

A Python-based utility to anonymize EEG files (EDF, TRC, SIG formats) by removing or replacing patient-identifiable information in file headers while preserving the actual EEG data and recording dates.

## Features

- **Multi-format Support:** Handles EDF (European Data Format), TRC (Micromed Brain-Quick), SIG (Compumedics/Profusion), and DAT (Raw Binary) files.
- **Directory Preservation:** Replicates the input directory structure in the output folder.
- **Safe Output:** Adds `_anonymized` suffix to filenames to prevent accidental overwrites.
- **Idempotent:** Skips files that have already been converted or exist in the output directory.
- **Logging:** Tracks all operations in the console and a persistent `anonymization.log` file.
- **Header Cleaning:**
  - **EDF:** Replaces Patient ID, sex, birthdate, name, and hospital admin info.
  - **TRC:** Replaces Patient ID fields.
  - **SIG:** Replaces embedded IDs.
  - **DAT:** Raw copy (assumes no metadata header).

## Anonymization Details

The script modifies specific header fields to remove PII (Personally Identifiable Information).

| Format | Original Fields | Anonymized Value |
|--------|----------------|------------------|
| **EDF** | Patient ID, Sex, Birthdate, Name | `X X 01-JAN-1900 Anonymous` |
| **EDF** | Hospital/Admin Info | `Anonymous_Device` |
| **TRC** | Patient ID fields | `ANONYMOUS` |
| **SIG** | Embedded ID | `ANONYMOUS` |
| **DAT** | Raw Data | Copied as-is (no header modification) |

*Note: For EDF files, the recording start date is preserved if detected, while other administrative data is redacted.*

## Prerequisites

- **Python 3.6+**
- No external libraries required (uses standard library only).

## Installation

1. Clone this repository or download the script.
2. Ensure you have Python 3 installed.

```bash
python3 --version
```

## Usage

Run the script from the command line, providing the input directory containing your EEG data.

```bash
python3 01__anonymize_eeg.py <input_dir> [output_dir]
```

- **`<input_dir>`**: The directory containing original EEG files. The script searches recursively.
- **`[output_dir]`**: (Optional) Destination for anonymized files. If omitted, defaults to `<input_dir>_anonymized`.

### Example

```bash
# Basic usage
python3 01__anonymize_eeg.py ./data/patients

# Specifying output directory
python3 01__anonymize_eeg.py ./data/patients ./data/cleaned_eegs
```

## Directory Structure Example

**Input:**
```text
data/
├── subject_01/
│   ├── 110012.EDF
│   ├── 110021.dat
│   ├── 110060.TRC
│   └── D0000313-t3.sig
└── subject_02/
    ├── 120014a.EDF
    ├── 120014a.TRC
    └── D0000312-t1.sig
```

**Output:**
```text
data_anonymized/
├── subject_01/
│   ├── 110012_anonymized.EDF
│   ├── 110021_anonymized.dat
│   ├── 110060_anonymized.TRC
│   └── D0000313-t3_anonymized.sig
└── subject_02/
    ├── 120014a_anonymized.EDF
    ├── 120014a_anonymized.TRC
    └── D0000312-t1_anonymized.sig
```

## Contact

For questions regarding this tool, please contact:
**W.M. Otte** (w.m.otte@umcutrecht.nl)
