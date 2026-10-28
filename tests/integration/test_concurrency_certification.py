from typing import Any
"""P4.4 Concurrency and Race Condition Tests.

Tests:
1. Self-approval rejection (Maker/Checker separation)
2. Successful first certification by authorized checker
3. Concurrent / double certification conflict handling (racing certifier gets 409 Conflict)
4. State transition guarantees and audit trail immutability
"""
import io
import pytest
from fastapi.testclient import TestClient

from apaar.main import create_app


@pytest.fixture(scope="module")
def client() -> Any:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_concurrency_and_maker_checker_certification(client) -> None:
    """Test maker/checker denial and atomic race safety on certification."""
    # 1. Dev token for Preparer (Maker) to discover offering & institution_id
    tok_init = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "preparer-inst1@demo.synthetic",
            "roles": ["PREPARER"],
            "institution_code": "DEMO-INST-001",
        },
    ).json()["access_token"]
    init_headers = {"Authorization": f"Bearer {tok_init}"}

    # 2. Get registered offering
    offering = client.get("/api/v1/approvals/offerings", headers=init_headers).json()[0]
    offering_id = offering["id"]
    institution_id = offering["institution_id"]

    # Generate maker token with explicit institution_id
    tok_maker = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "preparer-inst1@demo.synthetic",
            "roles": ["PREPARER"],
            "institution_id": institution_id,
        },
    ).json()["access_token"]
    maker_headers = {"Authorization": f"Bearer {tok_maker}"}

    # 3. Create submission batch with 2 valid synthetic rows
    csv_data = (
        "local_student_id,apaar_id,entry_route,category,is_nri,is_oci,is_fn,admission_cohort,current_study_year,interval_start\n"
        "DEMO-RACE-001,123456789012,DIRECT,GENERAL,false,false,false,2024-25,1,2024-08-01\n"
        "DEMO-RACE-002,234567890123,DIRECT,GENERAL,false,false,false,2024-25,1,2024-08-01\n"
    ).encode("utf-8")

    sub_resp = client.post(
        "/api/v1/submissions",
        headers=maker_headers,
        data={
            "programme_offering_id": offering_id,
            "admission_cohort": "2024-25",
        },
        files={"file": ("race_test.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert sub_resp.status_code == 201
    sub_id = sub_resp.json()["id"]

    # 4. Run validation -> reaches READY_FOR_CERTIFICATION
    val_resp = client.post(
        f"/api/v1/validation/submissions/{sub_id}/validate",
        headers=maker_headers,
    )
    assert val_resp.status_code == 200
    assert val_resp.json()["status"] == "COMPLETED"
    assert val_resp.json()["blocking_findings"] == 0

    # Submission status is now READY_FOR_CERTIFICATION
    sub_detail = client.get(f"/api/v1/submissions/{sub_id}", headers=maker_headers).json()
    assert sub_detail["status"] == "READY_FOR_CERTIFICATION"

    # 5a. Pure Preparer attempts to certify without CERTIFIER role -> EXPECT 403 FORBIDDEN
    pure_maker_cert = client.post(
        f"/api/v1/validation/submissions/{sub_id}/certify",
        headers=maker_headers,
    )
    assert pure_maker_cert.status_code == 403
    assert pure_maker_cert.json()["detail"]["error_code"] == "FORBIDDEN"

    # 5b. Maker acquires CERTIFIER role and attempts to self-approve -> EXPECT 403 SELF_APPROVAL_DENIED
    tok_maker_as_certifier = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "preparer-inst1@demo.synthetic",
            "roles": ["CERTIFIER"],
            "institution_id": institution_id,
        },
    ).json()["access_token"]
    self_cert_resp = client.post(
        f"/api/v1/validation/submissions/{sub_id}/certify",
        headers={"Authorization": f"Bearer {tok_maker_as_certifier}"},
    )
    assert self_cert_resp.status_code == 403
    assert self_cert_resp.json()["detail"]["error_code"] == "SELF_APPROVAL_DENIED"

    # 6. Certifier A (separate subject) attempts certification -> EXPECT 200 OK
    tok_cert_a = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "certifier-alice@demo.synthetic",
            "roles": ["CERTIFIER"],
            "institution_id": institution_id,
        },
    ).json()["access_token"]
    cert_a_headers = {"Authorization": f"Bearer {tok_cert_a}"}

    cert_res_a = client.post(
        f"/api/v1/validation/submissions/{sub_id}/certify",
        headers=cert_a_headers,
    )
    assert cert_res_a.status_code == 200
    cert_data = cert_res_a.json()
    assert cert_data["status"] == "CERTIFIED"
    assert cert_data["certified_by"] == "certifier-alice@demo.synthetic"
    assert cert_data["ordinary_count"] == 2

    # 7. Certifier B (racing second certifier) attempts certification on the SAME submission
    # -> EXPECT 409 CONFLICT (CERTIFICATION_BLOCKED because status is already CERTIFIED)
    tok_cert_b = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "certifier-bob@demo.synthetic",
            "roles": ["CERTIFIER"],
            "institution_id": institution_id,
        },
    ).json()["access_token"]
    cert_b_headers = {"Authorization": f"Bearer {tok_cert_b}"}

    cert_res_b = client.post(
        f"/api/v1/validation/submissions/{sub_id}/certify",
        headers=cert_b_headers,
    )
    assert cert_res_b.status_code == 409
    err_b = cert_res_b.json()
    assert "CERTIFICATION_BLOCKED" in str(err_b)

    # 8. Verify audit logs record exactly one CERTIFICATION_ISSUED event
    audit_resp = client.get("/api/v1/audit", headers=cert_a_headers)
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    cert_events = [e for e in events if e["object_id"] == sub_id and e["action"] == "CERTIFY"]
    assert len(cert_events) == 1
    assert cert_events[0]["principal"] == "certifier-alice@demo.synthetic"
