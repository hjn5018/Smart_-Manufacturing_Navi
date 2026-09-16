from functools import lru_cache

from fastapi import Depends, Header, HTTPException

from app.agent.baseAgent import BaseAgent
from app.agent.intentParser import IntentParser
from app.infra.db.session import get_db
from app.infra.llm.client import LLMClient
from app.domains.connection_session.infrastructure.board_session_manager import board_session_manager
from app.domains.control_contract.infrastructure.conveyor_repository import ConveyorRepository
from app.service.agentService import AgentService
from app.domains.capability_management.application.container_conveyor_service import ContainerConveyorService
from app.domains.operation_profile.application.straight_conveyor_service import StraightConveyorService


@lru_cache
def get_intent_service():
    return AgentService(get_intent_parser())

@lru_cache
def get_intent_parser()-> IntentParser:
    return IntentParser(get_llm_client())

@lru_cache
def get_base_agent()-> BaseAgent:
    return BaseAgent(get_llm_client())

@lru_cache
def get_llm_client():
   return LLMClient()


def get_container_conveyor_service(db=Depends(get_db)):
    return ContainerConveyorService(ConveyorRepository(db), board_session_manager)


def get_straight_conveyor_service(db=Depends(get_db)):
    return StraightConveyorService(ConveyorRepository(db), board_session_manager)


def get_board_connection_service(db=Depends(get_db)):
    return ContainerConveyorService(ConveyorRepository(db), board_session_manager, expected_board_type=None)


def verify_control_api_key(x_device_control_key: str | None = Header(default=None, alias="X-Device-Control-Key")):
    from app.core.application_config import settings

    if not settings.DEVICE_CONTROL_KEY:
        raise HTTPException(status_code=503, detail="DEVICE_CONTROL_KEY is not configured")
    if x_device_control_key != settings.DEVICE_CONTROL_KEY:
        raise HTTPException(status_code=401, detail="Invalid device control key")
    return True
