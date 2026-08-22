from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.demo import DemoScenarioResponse, DemoScenarioListResponse
from app.services import demo_service

router = APIRouter(prefix="/demo", tags=["Demo Scenarios"])

@router.get("/scenarios", response_model=DemoScenarioListResponse, summary="Retrieve all available demo scenarios")
def read_demo_scenarios():
    """
    Fetch the list of available demo scenarios.
    """
    return {"scenarios": demo_service.get_scenarios()}

@router.get("/scenarios/{scenario_type}", response_model=DemoScenarioResponse, summary="Retrieve detailed demo scenario data")
def read_demo_scenario(scenario_type: str, db: Session = Depends(get_db)):
    """
    Assemble and return the complete lifecycle dataset for a specific scenario dynamically queried from the Neon database.
    """
    normalized_type = scenario_type.lower()
    if normalized_type not in ("fraud", "recovery", "growth"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_type}' is not supported. Use 'fraud', 'recovery', or 'growth'."
        )
        
    scenario_data = demo_service.get_scenario_by_type(db, normalized_type)
    if not scenario_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data for scenario '{scenario_type}' could not be loaded. Please ensure the database has been seeded."
        )
        
    return scenario_data
