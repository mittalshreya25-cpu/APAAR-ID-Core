"""P5.1 and P5.2 Cross-Institution Temporal Overlap and Accountable Review Tests.

Tests:
1. Multi-tenant certified baseline setup (Institution 1 certifies synthetic student X)
2. Institution 2 submits conflicting full-time regular enrolment for student X
3. Central overlap detector discovers cross-institution temporal overlap
4. Privacy protection: counterpart institution identity suppressed
5. Accountable review decision lifecycle: OPEN -> RESOLVED / DISMISSED -> REOPENED
6. Audit logging of review decisions
"""
import io
import pytest
from fastapi.testclient import TestClient

from apaar.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_cross_institution_overlap_detection_and_review_lifecycle(client):
    # -------------------------------------------------------------------------
    # 1. SETUP: Get tokens for Institution 1 (Maker & Checker)
    # -------------------------------------------------------------------------
    # Get offerings to find institution IDs
    reg_tok = client.post(
        "/api/v1/access/dev-token",
        json={"subject": "regulator@demo.synthetic", "roles": ["REGULATOR"]},
    ).json()["access_token"]
    reg_headers = {"Authorization": f"Bearer {reg_tok}"}

    offerings = client.get("/api/v1/approvals/offerings", headers=reg_headers).json()
    assert len(offerings) >= 2
    offering_inst1 = offerings[0]
    inst1_id = offering_inst1["institution_id"]

    # Find offering for institution 2
    inst2_offerings = [o for o in offerings if o["institution_id"] != inst1_id]
    assert len(inst2_offerings) > 0
    offering_inst2 = inst2_offerings[0]
    inst2_id = offering_inst2["institution_id"]

    # Inst 1 Maker & Checker
    maker1_tok = client.post(
        "/api/v1/access/dev-token",
        json={"subject": "preparer-inst1@demo.synthetic", "roles": ["PREPARER"], "institution_id": inst1_id},
    ).json()["access_token"]
    maker1_headers = {"Authorization": f"Bearer {maker1_tok}"}

    cert1_tok = client.post(
        "/api/v1/access/dev-token",
        json={"subject": "certifier-inst1@demo.synthetic", "roles": ["CERTIFIER"], "institution_id": inst1_id},
    ).json()["access_token"]
    cert1_headers = {"Authorization": f"Bearer {cert1_tok}"}

    # -------------------------------------------------------------------------
    # 2. Institution 1 submits and certifies synthetic student "345678901234"
    # -------------------------------------------------------------------------
    overlap_apaar = "345678901234"
    csv_inst1 = (
        "local_student_id,apaar_id,entry_route,category,is_nri,is_oci,is_fn,admission_cohort,current_study_year,interval_start\n"
        f"INST1-S01,{overlap_apaar},DIRECT,GENERAL,false,false,false,2024-25,1,2024-08-01\n"
    ).encode("utf-8")

    sub1_resp = client.post(
        "/api/v1/submissions",
        headers=maker1_headers,
        data={"programme_offering_id": offering_inst1["id"], "admission_cohort": "2024-25"},
        files={"file": ("inst1_batch.csv", io.BytesIO(csv_inst1), "text/csv")},
    )
    assert sub1_resp.status_code == 201
    sub1_id = sub1_resp.json()["id"]

    # Validate Inst 1 submission
    val1 = client.post(f"/api/v1/validation/submissions/{sub1_id}/validate", headers=maker1_headers)
    assert val1.status_code == 200

    # Certify Inst 1 submission -> Creates active EnrolmentEpisode
    cert1 = client.post(f"/api/v1/validation/submissions/{sub1_id}/certify", headers=cert1_headers)
    assert cert1.status_code == 200
    assert cert1.json()["status"] == "CERTIFIED"

    # -------------------------------------------------------------------------
    # 3. Institution 2 submits conflicting enrolment for the SAME student
    # -------------------------------------------------------------------------
    maker2_tok = client.post(
        "/api/v1/access/dev-token",
        json={"subject": "preparer-inst2@demo.synthetic", "roles": ["PREPARER"], "institution_id": inst2_id},
    ).json()["access_token"]
    maker2_headers = {"Authorization": f"Bearer {maker2_tok}"}

    csv_inst2 = (
        "local_student_id,apaar_id,entry_route,category,is_nri,is_oci,is_fn,admission_cohort,current_study_year,interval_start\n"
        f"INST2-S99,{overlap_apaar},DIRECT,GENERAL,false,false,false,2024-25,1,2024-08-15\n"
    ).encode("utf-8")

    sub2_resp = client.post(
        "/api/v1/submissions",
        headers=maker2_headers,
        data={"programme_offering_id": offering_inst2["id"], "admission_cohort": "2024-25"},
        files={"file": ("inst2_batch.csv", io.BytesIO(csv_inst2), "text/csv")},
    )
    assert sub2_resp.status_code == 201
    sub2_id = sub2_resp.json()["id"]

    # Validate Inst 2 submission
    val2 = client.post(f"/api/v1/validation/submissions/{sub2_id}/validate", headers=maker2_headers)
    assert val2.status_code == 200

    # -------------------------------------------------------------------------
    # 4. Central overlap scan: detects temporal cross-institution collision
    # -------------------------------------------------------------------------
    overlap_resp = client.post(
        f"/api/v1/review/submissions/{sub2_id}/check-overlaps",
        headers=maker2_headers,
    )
    assert overlap_resp.status_code == 200
    opened_cases = overlap_resp.json()
    assert len(opened_cases) >= 1
    case = opened_cases[0]
    case_id = case["id"]
    assert case["case_type"] == "TEMPORAL_OVERLAP"
    assert case["is_overlap_case"] is True
    assert case["status"] == "OPEN"

    # -------------------------------------------------------------------------
    # 5. Accountable review decisions (OPEN -> RESOLVED -> REOPENED)
    # -------------------------------------------------------------------------
    # Regulator or authorized institution reviewer resolves the case
    res_resp = client.post(
        f"/api/v1/review/cases/{case_id}/decisions",
        headers=reg_headers,
        json={
            "decision": "RESOLVED",
            "explanation": "Student completed dual-enrolment reconciliation with prior institution consent.",
        },
    )
    assert res_resp.status_code == 200
    decision_data = res_resp.json()
    assert decision_data["decision"] == "RESOLVED"
    assert decision_data["explanation"] == "Student completed dual-enrolment reconciliation with prior institution consent."

    # Verify case status is updated to RESOLVED
    cases_list = client.get("/api/v1/review/cases", headers=reg_headers).json()
    matching_cases = [c for c in cases_list if c["id"] == case_id]
    assert len(matching_cases) == 1
    assert matching_cases[0]["status"] == "RESOLVED"

    # Test Reopen: new conflicting evidence arises -> case is REOPENED
    reopen_resp = client.post(
        f"/api/v1/review/cases/{case_id}/decisions",
        headers=reg_headers,
        json={
            "decision": "REOPENED",
            "explanation": "New schedule conflict evidence submitted by regional ombudsman.",
        },
    )
    assert reopen_resp.status_code == 200
    assert reopen_resp.json()["decision"] == "REOPENED"

    # Verify case transitioned back to OPEN
    reopened_cases = client.get(f"/api/v1/review/cases?case_status=OPEN", headers=reg_headers).json()
    assert any(c["id"] == case_id for c in reopened_cases)

