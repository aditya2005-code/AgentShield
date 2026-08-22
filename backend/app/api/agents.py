import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.agent import AgentResponse
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("", response_model=List[AgentResponse], summary="Retrieve all agents")
def read_agents(db: Session = Depends(get_db)):
    """
    Fetch all agents defined in the system.
    """
    return agent_service.get_agents(db)

@router.get("/{agent_id}", response_model=AgentResponse, summary="Retrieve a single agent by ID")
def read_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch a single agent by its unique UUID.
    """
    agent = agent_service.get_agent_by_id(db, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    return agent
