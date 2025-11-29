"""
Rules API router.

Provides endpoints for trading rule management.

:copyright: (c) 2025
:license: MIT
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.auth import CurrentUser
from src.core.events import Event, EventBus, EventType, get_event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["Rules"])


class RuleCondition(BaseModel):
    """Rule condition."""

    indicator: str = Field(
        description="Technical indicator (e.g., 'price', 'rsi', 'macd')"
    )
    operator: str = Field(description="Comparison operator")
    value: Any = Field(description="Comparison value")
    timeframe: Optional[str] = Field(
        default=None, description="Timeframe for indicator"
    )


class RuleAction(BaseModel):
    """Rule action."""

    action: str = Field(description="Action type (e.g., 'buy', 'sell', 'alert')")
    quantity: Optional[int] = Field(default=None, description="Order quantity")
    quantity_percent: Optional[float] = Field(
        default=None, description="Quantity as % of capital"
    )
    order_type: str = Field(default="market", description="Order type")
    price: Optional[float] = Field(default=None, description="Limit price")


class CreateRuleRequest(BaseModel):
    """Create rule request."""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    symbol: str = Field(min_length=1, max_length=20)
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    is_active: bool = True
    priority: int = Field(default=0, ge=0)


class UpdateRuleRequest(BaseModel):
    """Update rule request."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    symbol: Optional[str] = Field(default=None, min_length=1, max_length=20)
    conditions: Optional[List[RuleCondition]] = None
    actions: Optional[List[RuleAction]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0)


class RuleResponse(BaseModel):
    """Rule response."""

    id: str
    name: str
    description: Optional[str]
    symbol: str
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    is_active: bool
    priority: int
    trigger_count: int
    last_triggered: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class RuleExecutionResponse(BaseModel):
    """Rule execution response."""

    id: str
    rule_id: str
    executed_at: datetime
    trigger_data: Dict[str, Any]
    actions_taken: List[str]
    success: bool
    error: Optional[str]


class ValidateRuleRequest(BaseModel):
    """Validate rule request."""

    conditions: List[RuleCondition]
    actions: List[RuleAction]


class ValidateRuleResponse(BaseModel):
    """Validate rule response."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]


async def get_rules_repository():
    """
    Get rules repository instance with managed session.

    Yields a repository with a session that is automatically
    cleaned up when the request completes.
    """
    from src.database import get_database_manager
    from src.database.repositories import PostgresRulesRepository

    db = get_database_manager()
    async with db.session() as session:
        yield PostgresRulesRepository(session)


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: CreateRuleRequest,
    user_id: CurrentUser,
    event_bus: EventBus = Depends(get_event_bus),
    rules_repo=Depends(get_rules_repository),
) -> RuleResponse:
    """
    Create a new trading rule.

    :param request: Rule details.
    :type request: CreateRuleRequest
    :param user_id: Current user ID.
    :type user_id: str
    :param event_bus: Event bus.
    :type event_bus: EventBus
    :param rules_repo: Rules repository.
    :returns: Created rule.
    :rtype: RuleResponse
    """
    from src.database.models import TradingRule

    rule = TradingRule(
        user_id=user_id,
        name=request.name,
        description=request.description,
        symbol=request.symbol,
        conditions=[c.model_dump() for c in request.conditions],
        actions=[a.model_dump() for a in request.actions],
        is_active=request.is_active,
        priority=request.priority,
    )

    created = await rules_repo.create(rule)

    await event_bus.publish(
        Event(
            type=EventType.RULE_CREATED,
            data={"rule_id": str(created.id), "name": request.name},
            user_id=user_id,
        )
    )

    logger.info(f"Rule created: {created.id} by user {user_id}")

    return RuleResponse(
        id=str(created.id),
        name=created.name,
        description=created.description,
        symbol=created.symbol,
        conditions=created.conditions,
        actions=created.actions,
        is_active=created.is_active,
        priority=created.priority,
        trigger_count=0,
        last_triggered=None,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


@router.get("/", response_model=List[RuleResponse])
async def list_rules(
    user_id: CurrentUser,
    is_active: Optional[bool] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    rules_repo=Depends(get_rules_repository),
) -> List[RuleResponse]:
    """
    List user's trading rules.

    :param user_id: Current user ID.
    :type user_id: str
    :param is_active: Filter by active status.
    :type is_active: Optional[bool]
    :param symbol: Filter by symbol.
    :type symbol: Optional[str]
    :param limit: Maximum rules to return.
    :type limit: int
    :param offset: Pagination offset.
    :type offset: int
    :param rules_repo: Rules repository.
    :returns: List of rules.
    :rtype: List[RuleResponse]
    """
    rules = await rules_repo.get_by_user(
        user_id=user_id,
        is_active=is_active,
        symbol=symbol,
        limit=limit,
        offset=offset,
    )

    return [
        RuleResponse(
            id=str(r.id),
            name=r.name,
            description=r.description,
            symbol=r.symbol,
            conditions=r.conditions,
            actions=r.actions,
            is_active=r.is_active,
            priority=r.priority,
            trigger_count=r.trigger_count,
            last_triggered=r.last_triggered,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    user_id: CurrentUser,
    rules_repo=Depends(get_rules_repository),
) -> RuleResponse:
    """
    Get a specific rule.

    :param rule_id: Rule ID.
    :type rule_id: str
    :param user_id: Current user ID.
    :type user_id: str
    :param rules_repo: Rules repository.
    :returns: Rule details.
    :rtype: RuleResponse
    :raises HTTPException: If rule not found.
    """
    rule = await rules_repo.get(rule_id)

    if not rule or str(rule.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    return RuleResponse(
        id=str(rule.id),
        name=rule.name,
        description=rule.description,
        symbol=rule.symbol,
        conditions=rule.conditions,
        actions=rule.actions,
        is_active=rule.is_active,
        priority=rule.priority,
        trigger_count=rule.trigger_count,
        last_triggered=rule.last_triggered,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    request: UpdateRuleRequest,
    user_id: CurrentUser,
    event_bus: EventBus = Depends(get_event_bus),
    rules_repo=Depends(get_rules_repository),
) -> RuleResponse:
    """
    Update a trading rule.

    :param rule_id: Rule ID.
    :type rule_id: str
    :param request: Update details.
    :type request: UpdateRuleRequest
    :param user_id: Current user ID.
    :type user_id: str
    :param event_bus: Event bus.
    :type event_bus: EventBus
    :param rules_repo: Rules repository.
    :returns: Updated rule.
    :rtype: RuleResponse
    """
    rule = await rules_repo.get(rule_id)

    if not rule or str(rule.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    update_data = request.model_dump(exclude_unset=True)
    if "conditions" in update_data:
        update_data["conditions"] = [c.model_dump() for c in request.conditions]
    if "actions" in update_data:
        update_data["actions"] = [a.model_dump() for a in request.actions]

    for key, value in update_data.items():
        setattr(rule, key, value)

    updated = await rules_repo.update(rule)

    await event_bus.publish(
        Event(
            type=EventType.RULE_UPDATED,
            data={"rule_id": rule_id},
            user_id=user_id,
        )
    )

    return RuleResponse(
        id=str(updated.id),
        name=updated.name,
        description=updated.description,
        symbol=updated.symbol,
        conditions=updated.conditions,
        actions=updated.actions,
        is_active=updated.is_active,
        priority=updated.priority,
        trigger_count=updated.trigger_count,
        last_triggered=updated.last_triggered,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: str,
    user_id: CurrentUser,
    event_bus: EventBus = Depends(get_event_bus),
    rules_repo=Depends(get_rules_repository),
) -> None:
    """
    Delete a trading rule.

    :param rule_id: Rule ID.
    :type rule_id: str
    :param user_id: Current user ID.
    :type user_id: str
    :param event_bus: Event bus.
    :type event_bus: EventBus
    :param rules_repo: Rules repository.
    """
    rule = await rules_repo.get(rule_id)

    if not rule or str(rule.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    await rules_repo.delete(rule_id)

    await event_bus.publish(
        Event(
            type=EventType.RULE_DELETED,
            data={"rule_id": rule_id},
            user_id=user_id,
        )
    )

    logger.info(f"Rule deleted: {rule_id}")


@router.post("/{rule_id}/toggle", response_model=RuleResponse)
async def toggle_rule(
    rule_id: str,
    user_id: CurrentUser,
    event_bus: EventBus = Depends(get_event_bus),
    rules_repo=Depends(get_rules_repository),
) -> RuleResponse:
    """
    Toggle rule active status.

    :param rule_id: Rule ID.
    :type rule_id: str
    :param user_id: Current user ID.
    :type user_id: str
    :param event_bus: Event bus.
    :type event_bus: EventBus
    :param rules_repo: Rules repository.
    :returns: Updated rule.
    :rtype: RuleResponse
    """
    rule = await rules_repo.get(rule_id)

    if not rule or str(rule.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    rule.is_active = not rule.is_active
    updated = await rules_repo.update(rule)

    event_type = (
        EventType.RULE_ENABLED if updated.is_active else EventType.RULE_DISABLED
    )
    await event_bus.publish(
        Event(
            type=event_type,
            data={"rule_id": rule_id, "is_active": updated.is_active},
            user_id=user_id,
        )
    )

    return RuleResponse(
        id=str(updated.id),
        name=updated.name,
        description=updated.description,
        symbol=updated.symbol,
        conditions=updated.conditions,
        actions=updated.actions,
        is_active=updated.is_active,
        priority=updated.priority,
        trigger_count=updated.trigger_count,
        last_triggered=updated.last_triggered,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.post("/validate", response_model=ValidateRuleResponse)
async def validate_rule(
    request: ValidateRuleRequest,
    _: CurrentUser,
) -> ValidateRuleResponse:
    """
    Validate rule syntax without saving.

    :param request: Rule to validate.
    :type request: ValidateRuleRequest
    :returns: Validation result.
    :rtype: ValidateRuleResponse
    """
    errors: List[str] = []
    warnings: List[str] = []

    valid_operators = {
        "gt",
        "lt",
        "eq",
        "gte",
        "lte",
        "ne",
        "crosses_above",
        "crosses_below",
    }
    valid_indicators = {"price", "rsi", "macd", "ema", "sma", "volume", "atr"}

    for i, cond in enumerate(request.conditions):
        if cond.indicator.lower() not in valid_indicators:
            warnings.append(f"Condition {i + 1}: Unknown indicator '{cond.indicator}'")

        if cond.operator.lower() not in valid_operators:
            errors.append(f"Condition {i + 1}: Invalid operator '{cond.operator}'")

    valid_actions = {"buy", "sell", "alert", "close"}

    for i, action in enumerate(request.actions):
        if action.action.lower() not in valid_actions:
            errors.append(f"Action {i + 1}: Invalid action '{action.action}'")

        if action.action.lower() in {"buy", "sell"}:
            if not action.quantity and not action.quantity_percent:
                errors.append(
                    f"Action {i + 1}: Must specify quantity or quantity_percent"
                )

    return ValidateRuleResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.get("/{rule_id}/executions", response_model=List[RuleExecutionResponse])
async def get_rule_executions(
    rule_id: str,
    user_id: CurrentUser,
    limit: int = Query(default=50, le=100),
    rules_repo=Depends(get_rules_repository),
) -> List[RuleExecutionResponse]:
    """
    Get rule execution history.

    :param rule_id: Rule ID.
    :type rule_id: str
    :param user_id: Current user ID.
    :type user_id: str
    :param limit: Maximum executions to return.
    :type limit: int
    :param rules_repo: Rules repository.
    :returns: List of executions.
    :rtype: List[RuleExecutionResponse]
    """
    rule = await rules_repo.get(rule_id)

    if not rule or str(rule.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rule not found",
        )

    executions = await rules_repo.get_executions(rule_id, limit=limit)

    return [
        RuleExecutionResponse(
            id=str(e.id),
            rule_id=str(e.rule_id),
            executed_at=e.executed_at,
            trigger_data=e.trigger_data,
            actions_taken=e.actions_taken,
            success=e.success,
            error=e.error,
        )
        for e in executions
    ]
