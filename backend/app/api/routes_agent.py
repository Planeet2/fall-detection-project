from fastapi import APIRouter, Body

from app.services.yuanjing_agent import analyze_fall_event


router = APIRouter(prefix="/agent", tags=["agent"])

AGENT_TEST_EXAMPLE = {
    "elder_name": "Ivan",
    "age": 78,
    "event": "fall_detected",
    "confidence": 0.91,
    "location": "bedroom",
    "has_chronic_disease": True,
}


@router.post("/test")
async def test_agent(
    event_data: dict = Body(
        ...,
        examples=[AGENT_TEST_EXAMPLE],
    )
):
    result = await analyze_fall_event(event_data)

    return {
        "input": event_data,
        "agent_result": result,
    }
