# handlers/schedule/planner/timer/planner_state.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import asyncio

@dataclass
class PlannerState:
    is_running: bool = False
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    task: Optional[asyncio.Task] = None

planner_state = PlannerState()
