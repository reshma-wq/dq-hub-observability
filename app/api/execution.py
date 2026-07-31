from fastapi import APIRouter
import traceback

from app.services.execution_service import ExecutionService
from app.services.backup import BackupService

router = APIRouter()

service = ExecutionService()
backup_service = BackupService()


@router.post("/run/{table_name}")
def run_checks(table_name: str):
    # Run checks first
    result = service.run_checks(table_name)
    
    # Record backup entry AFTER checks complete but BEFORE sending email
    try:
        print(f"📊 Recording backup for {table_name}...")
        backup_result = backup_service.record_backup_entry(
            run_id=f"RUN_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}",
            table_name=table_name
        )
        print(f"✅ Backup recorded: {backup_result}")
    except Exception as e:
        print(f"⚠️ Backup failed: {str(e)}")
        traceback.print_exc()
    
    # Send email report after backup
    try:
        print("📧 Attempting to send email after checks...")
        from app.services.email_service import EmailNotificationService
        email_service = EmailNotificationService()
        email_service.send_dq_report()
        print("✅ Email sent successfully")
    except Exception as e:
        print(f"❌ Email notification failed: {str(e)}")
        traceback.print_exc()
    
    return result


@router.post("/run-all")
def run_all_checks():
    # Run checks first (includes backup recording and anomaly execution inside)
    service = ExecutionService()
    result = service.run_checks(None)
    
    # Send email report after all checks complete
    try:
        print("📧 Attempting to send email after run-all checks...")
        from app.services.email_service import EmailNotificationService
        email_service = EmailNotificationService()
        email_service.send_dq_report()
        print("✅ Email sent successfully")
    except Exception as e:
        print(f"❌ Email notification failed: {str(e)}")
        traceback.print_exc()
    
    return result


@router.get("/status/{run_id}")
def execution_status(run_id: str):
    return service.get_status(run_id)


@router.get("/test-email")
def test_email():
    """Test endpoint to verify email is working"""
    try:
        from app.services.email_service import EmailNotificationService
        email_service = EmailNotificationService()
        result = email_service.send_dq_report()
        return {"status": "success", "message": "Test email sent", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@router.get("/backup-history/{table_name}")
def get_backup_history(table_name: str):
    """Get all historical scan records for a table"""
    return backup_service.get_all_scans(table_name)


@router.get("/anomalies/{table_name}")
def get_active_anomalies(table_name: str):
    """Fetch latest anomaly results from dq_anomaly_watchtower_results for a table"""
    return service.get_active_anomalies(table_name)


@router.get("/debug/anomalies-raw")
def debug_all_anomalies():
    """Debug endpoint: Fetch ALL data from dq_anomaly_watchtower_results table"""
    return service.debug_get_all_anomalies()


@router.get("/debug/anomalies-active/{table_name}")
def debug_active_anomalies(table_name: str):
    """Debug endpoint: Show what get_active_anomalies is returning"""
    result = service.get_active_anomalies(table_name)
    return {
        "count": len(result),
        "data": result
    }
