"""Unit tests for submission CSV and JSON parser."""
import pytest

from apaar.shared.errors import UploadError
from apaar.submissions.parser import SubmissionParser


def test_parse_valid_csv() -> None:
    csv_data = (
        "local_student_id,apaar_id,entry_route,category,is_nri,is_oci,is_fn,admission_cohort,current_study_year,interval_start\n"
        "00123,012345678901,DIRECT,GENERAL,false,false,false,2024-25,1,2024-08-01\n"
        "00124,012345678902,DIRECT,SUPERNUMERARY,false,false,true,2024-25,1,2024-08-01\n"
    ).encode("utf-8")

    parser = SubmissionParser()
    res = parser.parse(csv_data, "students.csv")

    assert res.received_rows == 2
    assert res.processed_rows == 2
    assert res.rejected_rows == 0
    # Crucial test: leading zeros MUST be preserved as strings
    assert res.rows[0].normalized_data["local_student_id"] == "00123"
    assert res.rows[0].normalized_data["apaar_id"] == "012345678901"


def test_parse_missing_required_columns() -> None:
    csv_data = "local_student_id,entry_route\n123,DIRECT\n".encode("utf-8")
    parser = SubmissionParser()
    with pytest.raises(UploadError) as exc_info:
        parser.parse(csv_data, "bad.csv")
    assert "missing required columns" in exc_info.value.message.lower()


def test_parse_json_submission() -> None:
    json_data = (
        '['
        '  {"local_student_id": "STU-01", "apaar_id": "112233445566", "entry_route": "DIRECT", '
        '   "category": "GENERAL", "is_nri": false, "is_oci": false, "is_fn": false, '
        '   "admission_cohort": "2024-25", "current_study_year": 1, "interval_start": "2024-08-01"}'
        ']'
    ).encode("utf-8")

    parser = SubmissionParser()
    res = parser.parse(json_data, "batch.json")
    assert res.received_rows == 1
    assert res.processed_rows == 1
    assert res.rows[0].normalized_data["local_student_id"] == "STU-01"

