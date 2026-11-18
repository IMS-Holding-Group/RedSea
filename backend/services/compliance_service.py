"""الامتثال البحري: الوثائق الإلزامية وانتهاؤها."""
from datetime import timedelta
from backend.db import query, execute, get_db
from backend.dates import now_utc, now_iso, to_iso, format_datetime
from backend.notifications import notify

MANDATORY = ("registration", "insurance", "safety_inspection")
DOC_LABELS = {"registration": "شهادة التسجيل", "insurance": "وثيقة التأمين", "safety_inspection": "فحص السلامة",
              "navigation_license": "رخصة الملاحة", "crew_certificate": "شهادة الطاقم"}


def missing_documents(yacht_id, on_date):
    """الوثائق الإلزامية غير المعتمدة أو المنتهية في تاريخ معين."""
    missing = []
    for dt in MANDATORY:
        row = query("SELECT id FROM compliance_documents WHERE yacht_id = ? AND doc_type = ? AND status = 'approved' "
                    "AND expires_at > ?", (yacht_id, dt, to_iso(on_date)), one=True)
        if not row:
            missing.append(DOC_LABELS[dt])
    return missing


def compliance_score(yacht_id):
    ok_count = len(MANDATORY) - len(missing_documents(yacht_id, now_utc()))
    return round(ok_count * 100 / len(MANDATORY))


def refresh_expired_documents():
    now = now_iso()
    execute("UPDATE compliance_documents SET status = 'expired' WHERE status = 'approved' AND expires_at <= ?", (now,))
    for days in (30, 7):
        limit = to_iso(now_utc() + timedelta(days=days))
        rows = query("SELECT d.id, d.doc_type, d.expires_at, y.name, y.owner_id FROM compliance_documents d "
                     "JOIN yachts y ON y.id = d.yacht_id WHERE d.status = 'approved' AND d.expires_at > ? "
                     "AND d.expires_at <= ?", (now, limit))
        for r in rows:
            notify(r["owner_id"], f"وثيقة تقترب من الانتهاء خلال {days} يوماً",
                   f"{DOC_LABELS[r['doc_type']]} لليخت {r['name']} تنتهي في {format_datetime(r['expires_at'])}.",
                   "/owner-compliance", dedupe=True, commit=False)
    get_db().commit()
