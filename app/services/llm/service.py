import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    LOCAL = "local"

class LLMRequest(BaseModel):
    """Request model for LLM generation"""
    prompt: str = Field(..., description="The input prompt for the LLM")
    system_prompt: Optional[str] = Field(
        None,
        description="System message to set the behavior of the assistant"
    )
    max_tokens: int = Field(
        1000,
        ge=1,
        le=4000,
        description="Maximum number of tokens to generate"
    )
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Controls randomness in the output"
    )
    top_p: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )

class LLMResponse(BaseModel):
    """Response model for LLM generation"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str

class LLMService:
    """Service for interacting with various LLM providers"""
    
    def __init__(self, provider: LLMProvider = LLMProvider.OPENAI):
        self.provider = provider
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        if self.provider == LLMProvider.OPENAI:
            from openai import AsyncOpenAI
            from app.core.config import settings
            
            return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
        elif self.provider == LLMProvider.ANTHROPIC:
            from anthropic import AsyncAnthropic
            from app.core.config import settings
            
            return AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            
        elif self.provider == LLMProvider.GROQ:
            from groq import AsyncGroq
            from app.core.config import settings
            
            return AsyncGroq(api_key=settings.GROQ_API_KEY)
            
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text using the configured LLM provider"""
        try:
            if self.provider == LLMProvider.OPENAI:
                return await self._generate_openai(request)
            elif self.provider == LLMProvider.ANTHROPIC:
                return await self._generate_anthropic(request)
            elif self.provider == LLMProvider.GROQ:
                return await self._generate_groq(request)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}", exc_info=True)
            raise
    
    async def _generate_openai(self, request: LLMRequest) -> LLMResponse:
        """Generate text using OpenAI's API"""
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )
    
    async def _generate_anthropic(self, request: LLMRequest) -> LLMResponse:
        """Generate text using Anthropic's API"""
        system = request.system_prompt or ""
        
        response = await self.client.messages.create(
            model="claude-3-opus-20240229",
            system=system,
            messages=[{"role": "user", "content": request.prompt}],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
        )
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )
    
    async def _generate_groq(self, request: LLMRequest) -> LLMResponse:
        """Generate text using Groq's API"""
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        response = await self.client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )
