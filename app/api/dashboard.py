from fastapi import APIRouter

from app.services.dashboard_service import DashboardService

router = APIRouter()

service = DashboardService()

@router.get("/datasets")
def get_datasets():
    """
    Fetches list of available datasets from GCP BigQuery.
    
    Returns:
        list: List of dataset objects with name and description
    """
    return service.get_datasets()

@router.get("/tables/{dataset_name}")
def get_tables_in_dataset(dataset_name: str):
    """
    Fetches list of tables in a specific dataset.
    
    Args:
        dataset_name (str): Name of the dataset
        
    Returns:
        list: List of table names in the dataset
    """
    return service.get_tables_in_dataset(dataset_name)

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