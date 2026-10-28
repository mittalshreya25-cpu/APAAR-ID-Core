from typing import Any
"""Integration tests verifying end-to-end flow of the APAAR Core platform using TestClient."""
import io
import pytest
from fastapi.testclient import TestClient

from apaar.main import create_app


@pytest.fixture(scope="module")
def client() -> Any:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_readiness(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["synthetic_mode"] is True

    ready_resp = client.get("/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"


def test_end_to_end_demonstration_flow(client) -> None:
    """Complete 10-requirement demonstration flow:

    1. Get dev token for Preparer actor
    2. Retrieve registered offerings & approvals
    3. Upload CSV submission
    4. Trigger validation run -> inspect findings
    5. Attempt Maker self-certification -> EXPECT 403 SELF_APPROVAL_DENIED
    6. Get dev token for Certifier actor -> Certify -> EXPECT 200 OK
    7. Query reconciled intake report -> verified counts updated
    8. Issue signed attestation JWS token
    9. Verify signed attestation -> structure, signature, issuer, status verified
    10. Query certificate record -> displays both APAAR ID and local student ID
    """
    # 1. Dev token for Preparer
    tok_resp = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "preparer-inst1@demo.synthetic",
            "roles": ["PREPARER"],
            "institution_code": "DEMO-INST-001",
        },
    )
    assert tok_resp.status_code == 200
    preparer_token = tok_resp.json()["access_token"]
    preparer_headers = {"Authorization": f"Bearer {preparer_token}"}

    # 2. Retrieve offerings to get institution_id and offering_id
    off_resp = client.get("/api/v1/approvals/offerings", headers=preparer_headers)
    assert off_resp.status_code == 200
    offerings = off_resp.json()
    assert len(offerings) > 0
    offering = offerings[0]
    offering_id = offering["id"]
    institution_id = offering["institution_id"]

    # Update token with institution_id
    tok_resp2 = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "preparer-inst1@demo.synthetic",
            "roles": ["PREPARER"],
            "institution_id": institution_id,
        },
    )
    preparer_headers = {"Authorization": f"Bearer {tok_resp2.json()['access_token']}"}

    # 3. Upload CSV submission
    csv_content = (
        "local_student_id,apaar_id,entry_route,category,is_nri,is_oci,is_fn,admission_cohort,current_study_year,interval_start\n"
        "DEMO-2024-0001,123456789012,DIRECT,GENERAL,false,false,false,2024-25,1,2024-08-01\n"
        "DEMO-2024-0002,234567890123,DIRECT,SUPERNUMERARY,false,false,true,2024-25,1,2024-08-01\n"
    ).encode("utf-8")

    upload_resp = client.post(
        "/api/v1/submissions",
        headers=preparer_headers,
        data={
            "programme_offering_id": offering_id,
            "admission_cohort": "2024-25",
        },
        files={"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")},
    )
    assert upload_resp.status_code == 201
    submission = upload_resp.json()
    sub_id = submission["id"]
    assert submission["received_rows"] == 2
    assert submission["processed_rows"] == 2

    # 4. Trigger validation run
    val_resp = client.post(
        f"/api/v1/validation/submissions/{sub_id}/validate",
        headers=preparer_headers,
    )
    assert val_resp.status_code == 200
    val_run = val_resp.json()
    assert val_run["status"] == "COMPLETED"
    assert val_run["blocking_findings"] == 0

    # Check submission is now READY_FOR_CERTIFICATION
    sub_check = client.get(f"/api/v1/submissions/{sub_id}", headers=preparer_headers)
    assert sub_check.json()["status"] == "READY_FOR_CERTIFICATION"

    # 5. MAKER SELF-APPROVAL CHECK: Preparer tries to certify their own submission -> MUST FAIL
    self_cert_tok = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "preparer-inst1@demo.synthetic",
            "roles": ["CERTIFIER"],
            "institution_id": institution_id,
        },
    ).json()["access_token"]

    self_cert_resp = client.post(
        f"/api/v1/validation/submissions/{sub_id}/certify",
        headers={"Authorization": f"Bearer {self_cert_tok}"},
    )
    assert self_cert_resp.status_code == 403
    assert self_cert_resp.json()["detail"]["error_code"] == "SELF_APPROVAL_DENIED"

    # 6. Separate Certifier actor certifies -> SUCCEEDS
    certifier_tok = client.post(
        "/api/v1/access/dev-token",
        json={
            "subject": "certifier-inst1@demo.synthetic",
            "roles": ["CERTIFIER"],
            "institution_id": institution_id,
        },
    ).json()["access_token"]

    cert_resp = client.post(
        f"/api/v1/validation/submissions/{sub_id}/certify",
        headers={"Authorization": f"Bearer {certifier_tok}"},
    )
    assert cert_resp.status_code == 200
    cert_data = cert_resp.json()
    assert cert_data["status"] == "CERTIFIED"
    assert cert_data["certified_by"] == "certifier-inst1@demo.synthetic"
    assert cert_data["certified_version"] >= 1

    # 7. Check intake report
    report_resp = client.get("/api/v1/reporting/intake", headers=preparer_headers)
    assert report_resp.status_code == 200
    intake_rep = report_resp.json()
    assert intake_rep["total_certified"] >= 1

    # 8. Issue signed attestation JWS
    issue_resp = client.post(
        "/api/v1/attestations/issue",
        headers=preparer_headers,
        json={
            "submission_id": sub_id,
            "purpose": "EMPLOYMENT_VERIFICATION",
        },
    )
    assert issue_resp.status_code == 200
    att = issue_resp.json()
    assert att["status"] == "ACTIVE"
    signed_token = att["signed_bytes"]

    # 9. Verify signed attestation
    verify_resp = client.post(
        "/api/v1/attestations/verify",
        json={"signed_bytes": signed_token},
    )
    assert verify_resp.status_code == 200
    v_res = verify_resp.json()
    assert v_res["is_valid"] is True
    assert v_res["signature_valid"] is True
    assert v_res["issuer_trusted"] is True
    assert v_res["status"] == "ACTIVE"

    # 10. Certificate record view
    cert_record_resp = client.get(f"/api/v1/attestations/certificates/{sub_id}")
    assert cert_record_resp.status_code == 200
    c_rec = cert_record_resp.json()
    assert c_rec["apaar_id"] == "123456789012"
    assert c_rec["local_student_id"] == "DEMO-2024-0001"
    assert c_rec["synthetic"] is True
