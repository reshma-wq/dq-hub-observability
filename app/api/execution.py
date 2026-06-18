from fastapi import APIRouter
import traceback

from app.services.execution_service import ExecutionService

router = APIRouter()

service = ExecutionService()


@router.post("/run/{table_name}")
def run_checks(table_name: str):
    result = service.run_checks(table_name)
    
    # Send email report after checks complete
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
    service = ExecutionService()
    result = service.run_checks(None)
    
    # Send email report after checks complete
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
