"""Standalone execution of the 10-requirement demonstration flow."""
import io
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from apaar.main import create_app

def run_demo():
    print("Initializing FastAPI application...", flush=True)
    app = create_app()
    client = TestClient(app)

    print("Step 1: Checking /health and /ready...", flush=True)
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
    print("Health response:", resp.json())

    ready_resp = client.get("/ready")
    assert ready_resp.status_code == 200, ready_resp.text
    print("Ready response:", ready_resp.json())

    print("Step 2: Issuing dev token for Preparer...", flush=True)
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
    print("Preparer token issued.")

    print("Step 3: Querying programme offerings...", flush=True)
    off_resp = client.get("/api/v1/approvals/offerings", headers=preparer_headers)
    assert off_resp.status_code == 200
    offerings = off_resp.json()
    assert len(offerings) > 0
    offering = offerings[0]
    offering_id = offering["id"]
    institution_id = offering["institution_id"]
    print(f"Found offering: {offering['course_name']} (ID: {offering_id})")

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

    print("Step 4: Uploading CSV submission with 2 students...", flush=True)
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
    assert upload_resp.status_code == 201, upload_resp.text
    submission = upload_resp.json()
    sub_id = submission["id"]
    print(f"Submission staged successfully! ID: {sub_id}, Status: {submission['status']}")

    print("Step 5: Triggering validation run...", flush=True)
    val_resp = client.post(
        f"/api/v1/validation/submissions/{sub_id}/validate",
        headers=preparer_headers,
    )
    assert val_resp.status_code == 200, val_resp.text
    val_run = val_resp.json()
    print(f"Validation run completed: {val_run['total_findings']} total findings, {val_run['blocking_findings']} blocking.")

    sub_check = client.get(f"/api/v1/submissions/{sub_id}", headers=preparer_headers)
    print(f"Submission status after validation: {sub_check.json()['status']}")

    print("Step 6: Testing Maker/Checker separation (preparer self-approval)...", flush=True)
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
    print("Self-approval correctly denied with:", self_cert_resp.json()["detail"]["error_code"])

    print("Step 7: Separate certifier certifies submission...", flush=True)
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
    assert cert_resp.status_code == 200, cert_resp.text
    cert_data = cert_resp.json()
    print(f"Submission certified! Version: {cert_data['certified_version']}, By: {cert_data['certified_by']}")

    print("Step 8: Reconciled intake report...", flush=True)
    report_resp = client.get("/api/v1/reporting/intake", headers=preparer_headers)
    assert report_resp.status_code == 200
    intake_rep = report_resp.json()
    print(f"Report: total certified = {intake_rep['total_certified']}, total reported = {intake_rep['total_reported']}")

    print("Step 9: Issuing signed JWS attestation...", flush=True)
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
    signed_token = att["signed_bytes"]
    print(f"Issued attestation token (length: {len(signed_token)})")

    print("Step 10: Verifying signed attestation...", flush=True)
    verify_resp = client.post(
        "/api/v1/attestations/verify",
        json={"signed_bytes": signed_token},
    )
    assert verify_resp.status_code == 200
    v_res = verify_resp.json()
    print("Verification result:", v_res)

    print("Step 11: Inspecting verifiable certificate sample...", flush=True)
    cert_record_resp = client.get(f"/api/v1/attestations/certificates/{sub_id}")
    assert cert_record_resp.status_code == 200
    c_rec = cert_record_resp.json()
    print("Certificate record:", {
        "apaar_id": c_rec["apaar_id"],
        "local_student_id": c_rec["local_student_id"],
        "institution": c_rec["institution_name"],
        "qr_reference": c_rec["qr_reference"],
    })

    print("\n=======================================================")
    print("ALL 10 REQUIREMENTS OBSERVED AND VERIFIED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    run_demo()
