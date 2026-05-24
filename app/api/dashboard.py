from fastapi import APIRouter

from app.services.dashboard_service import DashboardService

router = APIRouter()

service = DashboardService()


@router.get("/summary")
def get_summary():

    return service.get_summary()

@router.get("/table/{table_name}")
def get_table_details(table_name: str):

    service = DashboardService()

    return service.get_table_details(
        table_name
    )

@router.get("/latest-results")
def get_latest_results():

    return service.get_latest_results()