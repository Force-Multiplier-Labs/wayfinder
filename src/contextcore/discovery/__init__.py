# src/contextcore/discovery/__init__.py

"""Agent Discovery Package

This package provides agent discovery capabilities for the ContextCore project,
including agent card management, discovery endpoints, and client operations.

Public classes:
- AgentCard: Agent metadata and capabilities
- AgentCapabilities: Skill and authentication definitions  
- SkillDescriptor: Individual skill definition
- AuthConfig: Authentication configuration
- AuthScheme: Authentication scheme enumeration
- ProviderInfo: Provider metadata
- DiscoveryEndpoint: Well-known endpoint structures
- DiscoveryDocument: Structure for discovery documents
- DiscoveryClient: Client for fetching remote agent data

Usage:
    from contextcore.discovery import AgentCard, DiscoveryClient
    
    # Create agent card
    card = AgentCard(
        agent_id="my-agent", 
        name="My Agent", 
        url="http://localhost:8080"
    )
    
    # Fetch remote agent
    client = DiscoveryClient()
    remote_card = client.fetch_agent_card("http://remote-agent.com")
    
    # Generate agent card JSON
    card_json = card.to_dict()
"""

from .agentcard import (
    AgentCard,
    AgentCapabilities,
    SkillDescriptor,
    AuthConfig,
    AuthScheme,
    ProviderInfo
)
from .endpoint import DiscoveryEndpoint, DiscoveryDocument
from .client import DiscoveryClient

__all__ = [
    "AgentCard",
    "AgentCapabilities", 
    "SkillDescriptor",
    "AuthConfig",
    "AuthScheme",
    "ProviderInfo",
    "DiscoveryEndpoint",
    "DiscoveryDocument", 
    "DiscoveryClient"
]

__version__ = "1.0.0"