from abc import ABC, abstractmethod
from typing import Dict, Optional

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: Optional[Dict] = None) -> str:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
