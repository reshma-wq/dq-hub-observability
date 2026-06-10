from fastapi import APIRouter

from app.services.execution_service import ExecutionService

router = APIRouter()

service = ExecutionService()


@router.post("/run/{table_name}")
def run_checks(table_name: str):

    return service.run_checks(table_name)

@router.post("/run-all")
def run_all_checks():

    service = ExecutionService()

    return service.run_checks(
        None
    )

@router.get("/status/{run_id}")
def execution_status(run_id: str):

    return service.get_status(run_id)