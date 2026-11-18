import os
from flask import Blueprint, g, request, abort, send_file

import config
from backend.db import query, execute
from backend.dates import now_iso, to_iso, now_utc
from backend.routes import body
from backend.security import (ok, fail, role_required, login_required, v_int, v_text, v_choice, v_datetime, read_upload,
                              random_filename, ValidationError)
from backend.services import compliance_service
from backend.services.compliance_service import DOC_LABELS
from backend.notifications import notify
from backend.audit import log_action

bp = Blueprint("compliance", __name__)
DOC_TYPES = tuple(DOC_LABELS.keys())
FILE_TYPES = ("application/pdf", "image/jpeg", "image/png")


@bp.get("/api/owner/documents")
@role_required("owner")
def owner_docs():
    compliance_service.refresh_expired_documents()
    yachts = query("SELECT id, name FROM yachts WHERE owner_id = ? ORDER BY id", (g.user["id"],))
    for y in yachts:
        y["score"] = compliance_service.compliance_score(y["id"])
        y["missing"] = compliance_service.missing_documents(y["id"], now_utc())
        y["documents"] = query("SELECT id, doc_type, doc_number, issued_at, expires_at, status, review_notes, stored_name IS NOT NULL AS has_file "
                               "FROM compliance_documents WHERE yacht_id = ? ORDER BY doc_type, expires_at DESC", (y["id"],))
    return ok(yachts)


@bp.post("/api/owner/documents")
@role_required("owner")
def upload_doc():
    form = request.form
    yid = v_int(form, "yacht_id", "اليخت", 1, 10 ** 9)
    y = query("SELECT id, name FROM yachts WHERE id = ? AND owner_id = ?", (yid, g.user["id"]), one=True)
    if not y:
        abort(404)
    dtype = v_choice(form, "doc_type", "نوع الوثيقة", DOC_TYPES)
    number = v_text(form, "doc_number", "رقم الوثيقة", 2, 40)
    issued = v_datetime(form, "issued_at", "تاريخ الإصدار")
    expires = v_datetime(form, "expires_at", "تاريخ الانتهاء")
    if expires <= issued:
        raise ValidationError("تاريخ الانتهاء يجب أن يكون بعد تاريخ الإصدار.")
    data, mime = read_upload(request.files.get("file"), FILE_TYPES, 5 * 1024 * 1024)
    name = random_filename(mime)
    with open(os.path.join(config.UPLOAD_DIR, "documents", name), "wb") as f:
        f.write(data)
    did = execute("INSERT INTO compliance_documents (yacht_id, doc_type, doc_number, issued_at, expires_at, stored_name, status, created_at) "
                  "VALUES (?, ?, ?, ?, ?, ?, 'pending_review', ?)", (yid, dtype, number, to_iso(issued), to_iso(expires), name, now_iso()))
    for u in query("SELECT id FROM users WHERE role = 'admin' AND is_active = 1"):
        notify(u["id"], "وثيقة بانتظار المراجعة", f"{DOC_LABELS[dtype]} جديدة لليخت {y['name']}.", "/admin-compliance")
    log_action("upload_document", "compliance_documents", did)
    return ok({"id": did}, 201)


@bp.get("/media/documents/<int:did>")
@login_required
def doc_file(did):
    d = query("SELECT d.stored_name, y.owner_id FROM compliance_documents d JOIN yachts y ON y.id = d.yacht_id WHERE d.id = ?", (did,), one=True)
    if not d or not d["stored_name"] or not (g.user["role"] == "admin" or d["owner_id"] == g.user["id"]):
        abort(404)
    path = os.path.join(config.UPLOAD_DIR, "documents", os.path.basename(d["stored_name"]))
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=False, max_age=0)


@bp.get("/api/admin/documents")
@role_required("admin")
def admin_docs():
    compliance_service.refresh_expired_documents()
    status = request.args.get("status", "pending_review")
    sql = ("SELECT d.*, y.name AS yacht_name, u.full_name AS owner_name, d.stored_name IS NOT NULL AS has_file "
           "FROM compliance_documents d JOIN yachts y ON y.id = d.yacht_id JOIN users u ON u.id = y.owner_id")
    params = []
    if status in ("pending_review", "approved", "rejected", "expired"):
        sql += " WHERE d.status = ?"
        params.append(status)
    rows = query(sql + " ORDER BY d.created_at DESC LIMIT 300", params)
    for r in rows:
        r.pop("stored_name", None)
    return ok(rows)


@bp.post("/api/admin/documents/<int:did>/decision")
@role_required("admin")
def decide_doc(did):
    d = query("SELECT d.*, y.name AS yacht_name, y.owner_id FROM compliance_documents d JOIN yachts y ON y.id = d.yacht_id WHERE d.id = ?",
              (did,), one=True)
    if not d:
        abort(404)
    if d["status"] != "pending_review":
        return fail("تمت مراجعة هذه الوثيقة مسبقاً.")
    data = body()
    dec = v_choice(data, "decision", "القرار", ("approve", "reject"))
    note = v_text(data, "notes", "الملاحظة", 0, 300, required=False)
    status = "approved" if dec == "approve" else "rejected"
    execute("UPDATE compliance_documents SET status = ?, reviewed_by = ?, review_notes = ? WHERE id = ?", (status, g.user["id"], note, did))
    notify(d["owner_id"], "نتيجة مراجعة وثيقة",
           f"تم {'اعتماد' if status == 'approved' else 'رفض'} {DOC_LABELS[d['doc_type']]} لليخت {d['yacht_name']}.", "/owner-compliance")
    log_action("document_" + dec, "compliance_documents", did)
    return ok()


@bp.get("/api/admin/permits")
@role_required("admin")
def permits():
    status = request.args.get("status", "requested")
    sql = ("SELECT p.*, b.reference, b.start_at, b.end_at, b.guests, b.status AS booking_status, y.name AS yacht_name, "
           "z.name AS zone_name FROM trip_permits p JOIN bookings b ON b.id = p.booking_id JOIN yachts y ON y.id = b.yacht_id "
           "LEFT JOIN zones z ON z.id = b.route_zone_id")
    params = []
    if status in ("requested", "approved", "rejected"):
        sql += " WHERE p.status = ?"
        params.append(status)
    return ok(query(sql + " ORDER BY b.start_at LIMIT 300", params))


@bp.post("/api/admin/permits/<int:pid>/decision")
@role_required("admin")
def decide_permit(pid):
    p = query("SELECT p.*, b.reference, b.tourist_id, y.owner_id FROM trip_permits p JOIN bookings b ON b.id = p.booking_id "
              "JOIN yachts y ON y.id = b.yacht_id WHERE p.id = ?", (pid,), one=True)
    if not p:
        abort(404)
    if p["status"] != "requested":
        return fail("تم البت في هذا التصريح مسبقاً.")
    data = body()
    dec = v_choice(data, "decision", "القرار", ("approve", "reject"))
    status = "approved" if dec == "approve" else "rejected"
    execute("UPDATE trip_permits SET status = ?, decided_at = ?, notes = ? WHERE id = ?",
            (status, now_iso(), v_text(data, "notes", "الملاحظة", 0, 300, required=False), pid))
    text = f"تم {'اعتماد' if status == 'approved' else 'رفض'} تصريح الإبحار للرحلة {p['reference']}."
    notify(p["owner_id"], "قرار تصريح الإبحار", text, "/owner-bookings")
    notify(p["tourist_id"], "قرار تصريح الإبحار", text, "/my-bookings")
    log_action("permit_" + dec, "trip_permits", pid)
    return ok()
