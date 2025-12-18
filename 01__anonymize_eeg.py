#!/usr/bin/env python3
"""
EEG Data Anonymization Script

Anonymizes EEG files (EDF, TRC, SIG formats) by removing or replacing
patient-identifiable information in file headers while preserving the
actual EEG data.

For questions: W.M. Otte (w.m.otte@umcutrecht.nl)

Usage:
    python3 anonymize_eeg.py <input_dir> [output_dir]

    If output_dir is not specified, it defaults to <input_dir>_anonymized.

Supported formats:
    - EDF/EDF+: European Data Format
    - TRC: Micromed Brain-Quick format
    - SIG: Compumedics/signal format
    - DAT: Raw binary data format

Features:
    - Supports EDF, TRC (Micromed), SIG (Compumedics), and DAT (raw) formats
    - Preserves directory structure
    - Adds _anonymized suffix to filenames
    - Skips already converted files (rerunnable)
    - Preserves recording dates while removing patient-identifiable info
    - Logs all operations to console and anonymization.log

What gets anonymized:

    | Format | Original                         | Anonymized                |
    |--------|----------------------------------|---------------------------|
    | EDF    | Patient ID, sex, birthdate, name | X X 01-JAN-1900 Anonymous |
    | EDF    | Hospital/admin info              | Anonymous_Device          |
    | TRC    | Patient ID fields                | ANONYMOUS                 |
    | SIG    | Embedded ID                      | ANONYMOUS                 |
    | DAT    | Raw data                         | Copied as-is              |

Example input structure:

    data/
    ├── subject_01/
    │   ├── 110012.EDF
    │   ├── 110060.TRC
    │   ├── D0000313-t3.sig
    │   └── raw_data_01.dat
    └── subject_02/
        ├── 120014a.EDF
        ├── 120014a.TRC
        └── D0000312-t1.sig

Example output structure:

    data_anonymized/
    ├── subject_01/
    │   ├── 110012_anonymized.EDF
    │   ├── 110060_anonymized.TRC
    │   ├── D0000313-t3_anonymized.sig
    │   └── raw_data_01_anonymized.dat
    └── subject_02/
        ├── 120014a_anonymized.EDF
        ├── 120014a_anonymized.TRC
        └── D0000312-t1_anonymized.sig
"""

import os
import sys
import shutil
import struct
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('anonymization.log')
    ]
)
logger = logging.getLogger(__name__)


class EDFAnonymizer:
    """Anonymizes EDF/EDF+ format files."""

    # EDF header field positions and lengths
    PATIENT_ID_OFFSET = 8
    PATIENT_ID_LENGTH = 80
    RECORDING_ID_OFFSET = 88
    RECORDING_ID_LENGTH = 80
    START_DATE_OFFSET = 168
    START_DATE_LENGTH = 8

    @staticmethod
    def is_edf_file(filepath: Path) -> bool:
        """Check if file is a valid EDF file."""
        try:
            with open(filepath, 'rb') as f:
                # EDF files start with '0' followed by spaces (version field)
                header = f.read(8)
                return header[0:1] == b'0'
        except Exception:
            return False

    @staticmethod
    def anonymize(input_path: Path, output_path: Path) -> bool:
        """
        Anonymize an EDF file.

        Replaces patient identification field with anonymous placeholder.
        Preserves recording date but removes hospital/technician info.
        """
        try:
            with open(input_path, 'rb') as f:
                data = bytearray(f.read())

            # Anonymize patient identification field (bytes 8-88)
            # EDF+ format: "patient_code sex birthdate patient_name"
            # Replace with: "X X X Anonymous"
            anon_patient = b'X X 01-JAN-1900 Anonymous' + b' ' * 55
            data[EDFAnonymizer.PATIENT_ID_OFFSET:
                 EDFAnonymizer.PATIENT_ID_OFFSET + EDFAnonymizer.PATIENT_ID_LENGTH] = anon_patient[:80]

            # Anonymize recording identification field (bytes 88-168)
            # Format: "Startdate dd-MMM-yyyy hospital_admin technician equipment"
            # Preserve only the startdate, anonymize the rest
            recording_field = data[EDFAnonymizer.RECORDING_ID_OFFSET:
                                   EDFAnonymizer.RECORDING_ID_OFFSET + EDFAnonymizer.RECORDING_ID_LENGTH]
            recording_str = recording_field.decode('latin-1', errors='replace')

            # Try to preserve the startdate if present
            if 'Startdate' in recording_str:
                # Extract the date portion
                parts = recording_str.split()
                if len(parts) >= 2:
                    date_part = parts[1] if parts[0] == 'Startdate' else 'X'
                    anon_recording = f'Startdate {date_part} X X Anonymous_Device'
                else:
                    anon_recording = 'Startdate X X X Anonymous_Device'
            else:
                anon_recording = 'Startdate X X X Anonymous_Device'

            anon_recording_bytes = anon_recording.encode('latin-1').ljust(80)[:80]
            data[EDFAnonymizer.RECORDING_ID_OFFSET:
                 EDFAnonymizer.RECORDING_ID_OFFSET + EDFAnonymizer.RECORDING_ID_LENGTH] = anon_recording_bytes

            # Write anonymized file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(data)

            logger.info(f"EDF anonymized: {input_path.name} -> {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to anonymize EDF {input_path}: {e}")
            return False


class TRCAnonymizer:
    """Anonymizes Micromed TRC format files."""

    # TRC header field positions (based on Micromed specification)
    HEADER_SIGNATURE = b'* MICROMED'
    PATIENT_ID_OFFSET_1 = 64  # First patient ID field
    PATIENT_ID_LENGTH_1 = 22
    PATIENT_ID_OFFSET_2 = 86  # Second patient ID field
    PATIENT_ID_LENGTH_2 = 20

    @staticmethod
    def is_trc_file(filepath: Path) -> bool:
        """Check if file is a valid TRC file."""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(16)
                return TRCAnonymizer.HEADER_SIGNATURE in header
        except Exception:
            return False

    @staticmethod
    def anonymize(input_path: Path, output_path: Path) -> bool:
        """
        Anonymize a TRC file.

        Replaces patient ID fields with anonymous placeholders.
        """
        try:
            with open(input_path, 'rb') as f:
                data = bytearray(f.read())

            # Replace patient ID fields with anonymous placeholder
            anon_id_1 = b'ANONYMOUS' + b' ' * 13  # 22 bytes
            anon_id_2 = b'ANONYMOUS' + b' ' * 11  # 20 bytes

            data[TRCAnonymizer.PATIENT_ID_OFFSET_1:
                 TRCAnonymizer.PATIENT_ID_OFFSET_1 + TRCAnonymizer.PATIENT_ID_LENGTH_1] = anon_id_1
            data[TRCAnonymizer.PATIENT_ID_OFFSET_2:
                 TRCAnonymizer.PATIENT_ID_OFFSET_2 + TRCAnonymizer.PATIENT_ID_LENGTH_2] = anon_id_2

            # Write anonymized file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(data)

            logger.info(f"TRC anonymized: {input_path.name} -> {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to anonymize TRC {input_path}: {e}")
            return False


class SIGAnonymizer:
    """Anonymizes SIG (Compumedics/Profusion) format files."""

    # SIG files have a specific header structure
    # The ID appears to be stored as UTF-16LE around offset 0x18
    ID_OFFSET = 0x18
    ID_LENGTH = 20  # 10 characters in UTF-16LE

    @staticmethod
    def is_sig_file(filepath: Path) -> bool:
        """Check if file appears to be a SIG file based on extension and structure."""
        # SIG files don't have a clear magic number, rely on extension
        return filepath.suffix.lower() == '.sig'

    @staticmethod
    def anonymize(input_path: Path, output_path: Path) -> bool:
        """
        Anonymize a SIG file.

        Replaces identifiable ID field with anonymous placeholder.
        Due to the compressed/proprietary nature of SIG files, this
        performs minimal header modification to avoid data corruption.
        """
        try:
            with open(input_path, 'rb') as f:
                data = bytearray(f.read())

            # The ID appears around offset 0x18 in UTF-16LE format
            # Replace with zeros/anonymous pattern
            # Be conservative - only modify the ID area
            anon_id = b'A\x00N\x00O\x00N\x00Y\x00M\x00O\x00U\x00S\x00 \x00'  # "ANONYMOUS " in UTF-16LE

            # Check if there's readable content at the expected offset
            if len(data) > SIGAnonymizer.ID_OFFSET + SIGAnonymizer.ID_LENGTH:
                data[SIGAnonymizer.ID_OFFSET:
                     SIGAnonymizer.ID_OFFSET + SIGAnonymizer.ID_LENGTH] = anon_id

            # Write anonymized file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(data)

            logger.info(f"SIG anonymized: {input_path.name} -> {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to anonymize SIG {input_path}: {e}")
            return False


class DATAnonymizer:
    """Anonymizes DAT format files."""

    @staticmethod
    def is_dat_file(filepath: Path) -> bool:
        """Check if file appears to be a DAT file based on extension."""
        return filepath.suffix.lower() == '.dat'

    @staticmethod
    def anonymize(input_path: Path, output_path: Path) -> bool:
        """
        Anonymize a DAT file.

        Currently, most DAT files in this context appear to be raw binary data
        without embedded metadata headers. This function defaults to safe copying.
        """
        try:
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Perform a copy as inspection suggests raw data
            # If specific DAT formats with headers are encountered,
            # specific logic should be added here.
            shutil.copy2(input_path, output_path)
            
            logger.info(f"DAT processed (raw data copied): {input_path.name} -> {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to process DAT {input_path}: {e}")
            return False


def get_anonymized_filename(original_path: Path) -> str:
    """Generate anonymized filename by adding _anonymized suffix before extension."""
    stem = original_path.stem
    suffix = original_path.suffix
    return f"{stem}_anonymized{suffix}"


def is_already_anonymized(filename: str) -> bool:
    """Check if filename indicates file is already anonymized."""
    return '_anonymized' in filename.lower()


def find_eeg_files(input_dir: Path) -> list:
    """Find all EEG files in the input directory (EDF, TRC, SIG, DAT)."""
    extensions = {'.edf', '.trc', '.sig', '.dat'}
    files = []

    for ext in extensions:
        files.extend(input_dir.rglob(f'*{ext}'))
        files.extend(input_dir.rglob(f'*{ext.upper()}'))

    # Remove duplicates and sort
    files = sorted(set(files))
    return files


def anonymize_file(input_path: Path, output_path: Path) -> bool:
    """Anonymize a single EEG file based on its format."""
    suffix = input_path.suffix.lower()

    if suffix == '.edf':
        if EDFAnonymizer.is_edf_file(input_path):
            return EDFAnonymizer.anonymize(input_path, output_path)
        else:
            logger.warning(f"File {input_path} has .edf extension but is not a valid EDF file")
            return False

    elif suffix == '.trc':
        if TRCAnonymizer.is_trc_file(input_path):
            return TRCAnonymizer.anonymize(input_path, output_path)
        else:
            logger.warning(f"File {input_path} has .trc extension but is not a valid TRC file")
            return False

    elif suffix == '.sig':
        return SIGAnonymizer.anonymize(input_path, output_path)

    elif suffix == '.dat':
        return DATAnonymizer.anonymize(input_path, output_path)

    else:
        logger.warning(f"Unknown file format: {input_path}")
        return False


def main():
    """Main entry point for the anonymization script."""

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python anonymize_eeg.py <input_dir> [output_dir]")
        print("\nIf output_dir is not specified, it defaults to <input_dir>_anonymized")
        sys.exit(1)

    input_dir = Path(sys.argv[1]).resolve()

    if len(sys.argv) >= 3:
        output_dir = Path(sys.argv[2]).resolve()
    else:
        output_dir = input_dir.parent / f"{input_dir.name}_anonymized"

    # Validate input directory
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        sys.exit(1)

    if not input_dir.is_dir():
        logger.error(f"Input path is not a directory: {input_dir}")
        sys.exit(1)

    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")

    # Find all EEG files
    eeg_files = find_eeg_files(input_dir)
    logger.info(f"Found {len(eeg_files)} EEG file(s)")

    if not eeg_files:
        logger.warning("No EEG files found to process")
        sys.exit(0)

    # Process each file
    processed = 0
    skipped = 0
    failed = 0

    for input_path in eeg_files:
        # Skip already anonymized files
        if is_already_anonymized(input_path.name):
            logger.info(f"Skipping already anonymized file: {input_path.name}")
            skipped += 1
            continue

        # Calculate output path preserving directory structure
        relative_path = input_path.relative_to(input_dir)
        output_filename = get_anonymized_filename(input_path)
        output_path = output_dir / relative_path.parent / output_filename

        # Skip if output file already exists
        if output_path.exists():
            logger.info(f"Skipping (output exists): {input_path.name}")
            skipped += 1
            continue

        # Anonymize the file
        if anonymize_file(input_path, output_path):
            processed += 1
        else:
            failed += 1

    # Summary
    logger.info("=" * 50)
    logger.info("Anonymization Summary:")
    logger.info(f"  Total files found: {len(eeg_files)}")
    logger.info(f"  Successfully processed: {processed}")
    logger.info(f"  Skipped (already done): {skipped}")
    logger.info(f"  Failed: {failed}")
    logger.info("=" * 50)

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
