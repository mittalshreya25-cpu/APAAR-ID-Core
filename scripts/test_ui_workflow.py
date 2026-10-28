"""Test the exact end-to-end HTTP workflow executed by the demonstration UI."""
import json
import threading
import time
import urllib.request
import urllib.error
import uvicorn
from apaar.main import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="error")

def run_workflow_test():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2.0)

    base = "http://127.0.0.1:8766"
    print("Testing browser UI workflow against live server at", base)

    # Step 1: Serving static UI
    req = urllib.request.Request(f"{base}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode("utf-8")
        assert "APAAR ID Core" in html
        assert "uploadOfferingSelect" in html
        assert "init()" in html
        assert "switchRole(\"preparer\")" in html
        print("[OK] Step 1: Served static/index.html with updated init() sequence")

    # Step 2: Preparer logs in via dev-token (what switchRole('preparer') executes)
    token_payload = json.dumps({
        "subject": "preparer-inst1@demo.synthetic",
        "roles": ["PREPARER"],
        "institution_code": "DEMO-INST-001"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/access/dev-token",
        data=token_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        token_data = json.loads(resp.read().decode("utf-8"))
        preparer_token = token_data["access_token"]
        print("[OK] Step 2: Preparer token minted successfully")

    # Step 3: Load offerings (what loadOfferings() executes)
    req = urllib.request.Request(
        f"{base}/api/v1/approvals/offerings",
        headers={"Authorization": f"Bearer {preparer_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        offerings = json.loads(resp.read().decode("utf-8"))
        assert len(offerings) > 0, "No offerings found!"
        first_offering = offerings[0]
        offering_id = first_offering["id"]
        inst_id = first_offering["institution_id"]
        print(f"[OK] Step 3: loadOfferings returned {len(offerings)} offering(s). Selected: {first_offering['course_name']} ({offering_id})")

    # Step 4: Refresh dashboard (what refreshDashboard() executes)
    req = urllib.request.Request(
        f"{base}/api/v1/reporting/intake",
        headers={"Authorization": f"Bearer {preparer_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        dashboard = json.loads(resp.read().decode("utf-8"))
        print(f"[OK] Step 4: Dashboard stats loaded: Approved={dashboard['total_approved_ordinary']}, Reported={dashboard['total_reported']}, Certified={dashboard['total_certified']}")

    # Step 5: Upload & Stage batch (what submitBatch() executes)
    boundary = "----WebKitFormBoundaryDemo123456"
    csv_bytes = (
        "local_student_id,apaar_id,entry_route,category,is_nri,is_oci,is_fn,admission_cohort,current_study_year,interval_start\r\n"
        "DEMO-2024-0001,123456789012,DIRECT,GENERAL,false,false,false,2024-25,1,2024-08-01\r\n"
        "DEMO-2024-0002,234567890123,DIRECT,SUPERNUMERARY,false,false,true,2024-25,1,2024-08-01\r\n"
    ).encode("utf-8")

    body_parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"programme_offering_id\"\r\n\r\n{offering_id}\r\n".encode("utf-8"),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"admission_cohort\"\r\n\r\n2024-25\r\n".encode("utf-8"),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"demo_batch.csv\"\r\nContent-Type: text/csv\r\n\r\n".encode("utf-8"),
        csv_bytes,
        f"\r\n--{boundary}--\r\n".encode("utf-8")
    ]
    multipart_body = b"".join(body_parts)

    req = urllib.request.Request(
        f"{base}/api/v1/submissions",
        data=multipart_body,
        headers={
            "Authorization": f"Bearer {preparer_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            assert resp.status in (200, 201)
            sub_data = json.loads(resp.read().decode("utf-8"))
            submission_id = sub_data["id"]
            print(f"[OK] Step 5: submitBatch succeeded! Submission ID: {submission_id}, Status: {sub_data['status']}")
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        print(f"[ERROR] Step 5 returned {e.code}: {err_content}")
        raise

    # Step 6: Validate submission (what auto-validation executes)
    req = urllib.request.Request(
        f"{base}/api/v1/validation/submissions/{submission_id}/validate",
        data=b"",
        headers={"Authorization": f"Bearer {preparer_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        val_data = json.loads(resp.read().decode("utf-8"))
        print(f"[OK] Step 6: Validation completed! Total findings: {val_data['total_findings']}, Blocking: {val_data['blocking_findings']}")

    # Step 7: Attempt Maker certification (expect 403 SELF_APPROVAL_DENIED)
    req = urllib.request.Request(
        f"{base}/api/v1/validation/submissions/{submission_id}/certify",
        data=b"",
        headers={"Authorization": f"Bearer {preparer_token}"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raise AssertionError("Maker certification should have failed with 403!")
    except urllib.error.HTTPError as e:
        assert e.code == 403
        err_content = e.read().decode("utf-8")
        print(f"[DEBUG] Step 7 403 body: {err_content}")
        err_body = json.loads(err_content)
        assert "detail" in err_body
        print(f"[OK] Step 7: Maker self-certification correctly rejected with 403 SELF_APPROVAL_DENIED")

    # Step 8: Switch role to Certifier (what switchRole('certifier') executes)
    cert_token_payload = json.dumps({
        "subject": "certifier-inst1@demo.synthetic",
        "roles": ["CERTIFIER"],
        "institution_code": "DEMO-INST-001"
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/access/dev-token",
        data=cert_token_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        cert_data = json.loads(resp.read().decode("utf-8"))
        certifier_token = cert_data["access_token"]
        print("[OK] Step 8: Certifier role switched and token acquired")

    # Step 9: Certify submission as Checker (expect 200 OK)
    req = urllib.request.Request(
        f"{base}/api/v1/validation/submissions/{submission_id}/certify",
        data=b"",
        headers={"Authorization": f"Bearer {certifier_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        cert_res = json.loads(resp.read().decode("utf-8"))
        print(f"[OK] Step 9: Certification succeeded! Version: {cert_res['certified_version']} committed by {cert_res['certified_by']}")

    # Step 10: Issue signed attestation JWS token
    att_req = json.dumps({
        "submission_id": submission_id,
        "record_type": "ENROLMENT_ATTESTATION",
        "purpose": "EMPLOYMENT_VERIFICATION",
        "expires_in_days": 30
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/attestations/issue",
        data=att_req,
        headers={"Authorization": f"Bearer {certifier_token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        att_res = json.loads(resp.read().decode("utf-8"))
        signed_token = att_res["signed_bytes"]
        print(f"[OK] Step 10: Signed JWS attestation issued (status={att_res['status']})")

    # Step 11: Cryptographically verify signed attestation
    verify_req = json.dumps({"signed_bytes": signed_token}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/attestations/verify",
        data=verify_req,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        ver_res = json.loads(resp.read().decode("utf-8"))
        assert ver_res["is_valid"] is True
        assert ver_res["signature_valid"] is True
        assert ver_res["issuer_trusted"] is True
        print(f"[OK] Step 11: Cryptographic verification passed: is_valid={ver_res['is_valid']}, signature_valid={ver_res['signature_valid']}")

    # Step 12: Audit trail inspection
    req = urllib.request.Request(
        f"{base}/api/v1/audit",
        headers={"Authorization": f"Bearer {certifier_token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        audit_records = json.loads(resp.read().decode("utf-8"))
        print(f"[OK] Step 12: Audit log fetched ({len(audit_records)} entries). Latest action: {audit_records[0]['action']}")

    print("\n=======================================================")
    print(">>> ALL 12 BROWSER UI STEPS PASSED WITH 100% SUCCESS! <<<")
    print("=======================================================")

if __name__ == "__main__":
    run_workflow_test()
