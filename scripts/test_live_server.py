"""Run live uvicorn server in a background thread and test endpoints over real HTTP sockets."""
import json
import threading
import time
import urllib.request
import urllib.error
import uvicorn
from apaar.main import app

def start_server() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")

def run_tests() -> None:
    # Start uvicorn in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(2.0)  # Wait for startup

    base_url = "http://127.0.0.1:8765"
    print("Testing live HTTP endpoints on", base_url)

    # 0. UI Root
    req = urllib.request.Request(f"{base_url}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        html = resp.read().decode()
        assert "APAAR ID Core" in html
        print(f"0. GET / -> Served UI HTML ({len(html)} bytes)")

    # 1. Health
    req = urllib.request.Request(f"{base_url}/health")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("1. GET /health ->", data)

    # 2. Ready
    req = urllib.request.Request(f"{base_url}/ready")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print("2. GET /ready ->", data)

    # 3. Dev Token
    token_req_data = json.dumps({
        "subject": "preparer-inst1@demo.synthetic",
        "roles": ["PREPARER"],
        "institution_code": "DEMO-INST-001"
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/api/v1/access/dev-token",
        data=token_req_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        token_data = json.loads(resp.read().decode())
        token = token_data["access_token"]
        print("3. POST /api/v1/access/dev-token -> Generated JWT token for preparer")

    # 4. List Institutions
    req = urllib.request.Request(
        f"{base_url}/api/v1/institutions",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        insts = json.loads(resp.read().decode())
        print(f"4. GET /api/v1/institutions -> Found {len(insts)} institution(s):", [i["code"] for i in insts])

    # 5. List Offerings
    req = urllib.request.Request(
        f"{base_url}/api/v1/approvals/offerings",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        offs = json.loads(resp.read().decode())
        print(f"5. GET /api/v1/approvals/offerings -> Found {len(offs)} offering(s):", [o["course_name"] for o in offs])

    # 6. Check Identity with Mock Provider
    id_req_data = json.dumps({"apaar_id": "123456789012"}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/v1/identity/check",
        data=id_req_data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        id_res = json.loads(resp.read().decode())
        print("6. POST /api/v1/identity/check ->", id_res["outcome"], f"(synthetic={id_res['synthetic']})")

    # 7. Check Intake Report
    req = urllib.request.Request(
        f"{base_url}/api/v1/reporting/intake",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        report = json.loads(resp.read().decode())
        print(f"7. GET /api/v1/reporting/intake -> Approved Ordinary: {report['total_approved_ordinary']}, Reported: {report['total_reported']}, Certified: {report['total_certified']}")

    # 8. Certificate Record View
    req = urllib.request.Request(f"{base_url}/api/v1/attestations/certificates/00000000-0000-0000-0000-000000000001")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        cert = json.loads(resp.read().decode())
        print("8. GET /api/v1/attestations/certificates/{id} ->", {
            "apaar_id": cert["apaar_id"],
            "local_student_id": cert["local_student_id"],
            "institution": cert["institution_name"],
            "synthetic": cert["synthetic"]
        })

    # 9. Issue and Verify Signed Attestation
    att_req_data = json.dumps({
        "record_type": "ENROLMENT_ATTESTATION",
        "purpose": "EMPLOYMENT_VERIFICATION",
        "expires_in_days": 30
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/api/v1/attestations/issue",
        data=att_req_data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        att_data = json.loads(resp.read().decode())
        signed_token = att_data["signed_bytes"]
        print(f"9. POST /api/v1/attestations/issue -> Issued JWS token (status={att_data['status']})")

    # 10. Verify Attestation
    ver_req_data = json.dumps({"signed_bytes": signed_token}).encode()
    req = urllib.request.Request(
        f"{base_url}/api/v1/attestations/verify",
        data=ver_req_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        ver_res = json.loads(resp.read().decode())
        print("10. POST /api/v1/attestations/verify -> Valid:", ver_res["is_valid"], f"(signature={ver_res['signature_valid']}, issuer={ver_res['issuer_trusted']}, status={ver_res['status']})")

    # 11. Review Cases List
    req = urllib.request.Request(
        f"{base_url}/api/v1/review/cases",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        cases = json.loads(resp.read().decode())
        print(f"11. GET /api/v1/review/cases -> {len(cases)} review case(s)")

    # 12. Audit Events
    req = urllib.request.Request(
        f"{base_url}/api/v1/audit",
        headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        audits = json.loads(resp.read().decode())
        print(f"12. GET /api/v1/audit -> {len(audits)} audit log event(s)")

    print("\n>>> LIVE SERVER VERIFICATION: ALL 12 OPERATIONS SUCCEEDED OVER REAL HTTP SOCKETS! <<<")

if __name__ == "__main__":
    run_tests()
