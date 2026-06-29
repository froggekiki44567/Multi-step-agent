import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from tools import TOOL_SCHEMAS, dispatch
from memory import ConversationMemory
from guardrails import check_input, check_output, InputCheckRe