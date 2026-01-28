"""
TraceQL Query Builder for Tempo Integration

This module provides a fluent interface for building and executing TraceQL queries
against Grafana Tempo. It automatically handles span attribute prefixing and
includes comprehensive time range support.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

from pydantic import BaseModel

# httpx is optional - only needed for live queries
if TYPE_CHECKING:
    import httpx

__all__ = [
    'TraceQLBuilder',
    'TempoClient', 
    'TempoConfig',
    'TraceQLResult',
    'TraceData',
    'SpanData',
    'TempoError',
    'QueryValidationError',
    'ConnectionError'
]

# Setup logging
logger = logging.getLogger(__name__)


# Exception classes
class TempoError(Exception):
    """Base exception for Tempo operations."""
    pass


class QueryValidationError(TempoError):
    """Raised when TraceQL query validation fails."""
    pass


class ConnectionError(TempoError):
    """Raised when connection to Tempo fails."""
    pass


# Configuration
class TempoConfig:
    """Configuration for Tempo client connection."""
    
    def __init__(self, endpoint: str, timeout: int = 30, default_lookback: str = "1h"):
        self.endpoint = endpoint.rstrip('/')  # Normalize endpoint
        self.timeout = timeout
        self.default_lookback = default_lookback


# Data models
class SpanData(BaseModel):
    """Represents span data returned from Tempo."""
    span_id: str
    trace_id: str
    operation_name: str
    attributes: Dict[str, Any]
    start_time: datetime
    end_time: datetime


class TraceData(BaseModel):
    """Represents trace data with associated spans."""
    trace_id: str
    spans: List[SpanData]
    duration_ms: int
    start_time: datetime


class TraceQLResult(BaseModel):
    """Result container for TraceQL query execution."""
    traces: List[TraceData]
    total_count: int
    execution_time_ms: int
    query: str


# Tempo client
class TempoClient:
    """Async HTTP client for Tempo API interactions."""

    def __init__(self, config: TempoConfig):
        self.endpoint = config.endpoint
        self.timeout = config.timeout
        self._client = None

    def _get_client(self):
        """Lazily initialize httpx client."""
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(timeout=self.timeout)
            except ImportError:
                raise TempoError(
                    "httpx is required for live Tempo queries. "
                    "Install with: pip install httpx"
                )
        return self._client

    async def search(self, query: str) -> Dict[str, Any]:
        """Execute TraceQL search query against Tempo."""
        import httpx

        client = self._get_client()
        try:
            logger.info(f"Executing TraceQL query: {query}")
            response = await client.get(
                f"{self.endpoint}/api/search",
                params={"q": query}
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Timeout connecting to Tempo: {e}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Error connecting to Tempo: {e}")
        except httpx.HTTPStatusError as e:
            raise TempoError(f"Tempo API error: {e.response.status_code} - {e.response.text}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
            self._client = None


# Main TraceQL builder class
class TraceQLBuilder:
    """Fluent interface for building TraceQL queries with automatic attribute prefixing."""
    
    def __init__(self, tempo_client: TempoClient, default_lookback: str = "1h"):
        self.tempo_client = tempo_client
        self.filters = []
        self.fields = []
        self.start_time = None
        self.end_time = None
        self.limit_count = 100
        
        # Set default time range if provided
        if default_lookback:
            self.end_time = datetime.utcnow()
            self.start_time = self._parse_lookback(default_lookback)

    def filter(self, expression: str) -> "TraceQLBuilder":
        """Add filter expression with automatic span attribute prefixing."""
        try:
            prefixed_expression = self._auto_prefix_attributes(expression)
            self.filters.append(prefixed_expression)
            logger.debug(f"Added filter: {prefixed_expression}")
            return self
        except Exception as e:
            raise QueryValidationError(f"Invalid filter expression '{expression}': {e}")

    def select(self, *fields: str) -> "TraceQLBuilder":
        """Add fields to select with automatic span prefixing."""
        for field in fields:
            # Auto-prefix with 'span.' if not already prefixed
            prefixed_field = field if field.startswith("span.") else f"span.{field}"
            self.fields.append(prefixed_field)
        logger.debug(f"Added select fields: {self.fields}")
        return self

    def time_range(self, start: Union[str, datetime], 
                   end: Optional[Union[str, datetime]] = None) -> "TraceQLBuilder":
        """Set time range for the query."""
        try:
            if isinstance(start, str):
                self.start_time = self._parse_time_string(start)
            else:
                self.start_time = start

            if end:
                if isinstance(end, str):
                    self.end_time = self._parse_time_string(end)
                else:
                    self.end_time = end
            else:
                self.end_time = datetime.utcnow()

            logger.debug(f"Set time range: {self.start_time} to {self.end_time}")
            return self
        except Exception as e:
            raise QueryValidationError(f"Invalid time range: {e}")

    def limit(self, count: int) -> "TraceQLBuilder":
        """Set maximum number of results to return."""
        if count <= 0:
            raise QueryValidationError("Limit must be a positive integer")
        self.limit_count = count
        return self

    def build(self) -> str:
        """Build the final TraceQL query string."""
        # Validate required components
        if not self.filters:
            raise QueryValidationError("At least one filter must be specified")
        
        if not self.start_time or not self.end_time:
            raise QueryValidationError("Time range must be specified")
            
        if self.start_time >= self.end_time:
            raise QueryValidationError("Start time must be before end time")

        # Build query components
        filter_clause = " && ".join(self.filters)
        query_parts = [f"{{{filter_clause}}}"]

        # Add select clause if fields specified
        if self.fields:
            select_clause = ", ".join(self.fields)
            query_parts.append(f"| select({select_clause})")

        # Always include time range (converted to nanoseconds for Tempo)
        start_ns = int(self.start_time.timestamp() * 1_000_000_000)
        end_ns = int(self.end_time.timestamp() * 1_000_000_000)
        query_parts.append(f"&start={start_ns}&end={end_ns}")

        # Add limit
        query_parts.append(f"&limit={self.limit_count}")

        query = " ".join(query_parts)
        logger.debug(f"Built TraceQL query: {query}")
        return query

    async def execute(self) -> TraceQLResult:
        """Execute the built query against Tempo."""
        query = self.build()
        start_time = datetime.utcnow()
        
        try:
            response_data = await self.tempo_client.search(query)
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Transform response to our model structure
            traces = self._transform_response(response_data)
            
            return TraceQLResult(
                traces=traces,
                total_count=len(traces),
                execution_time_ms=execution_time,
                query=query
            )
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise TempoError(f"Failed to execute query: {e}")

    def _auto_prefix_attributes(self, expression: str) -> str:
        """Automatically add 'span.' prefix to task attributes."""
        # Replace task attributes with span.task attributes
        expression = expression.replace("task.", "span.task.")
        
        # Handle cases where span. prefix might be missing for other attributes
        # This is a simplified implementation - production might need more sophisticated parsing
        if " = " in expression and not expression.startswith("span."):
            parts = expression.split(" = ")
            if len(parts) == 2 and not parts[0].strip().startswith("span."):
                parts[0] = f"span.{parts[0].strip()}"
                expression = " = ".join(parts)
        
        return expression

    def _parse_lookback(self, lookback: str) -> datetime:
        """Parse lookback string (e.g., '1h', '30m') to datetime."""
        now = datetime.utcnow()
        
        if lookback.endswith('h'):
            hours = int(lookback[:-1])
            return now - timedelta(hours=hours)
        elif lookback.endswith('m'):
            minutes = int(lookback[:-1])
            return now - timedelta(minutes=minutes)
        elif lookback.endswith('d'):
            days = int(lookback[:-1])
            return now - timedelta(days=days)
        else:
            raise ValueError(f"Unsupported time format: {lookback}")

    def _parse_time_string(self, time_str: str) -> datetime:
        """Parse time string to datetime object."""
        try:
            # Support ISO format
            if 'T' in time_str:
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            # Support relative time
            elif time_str.endswith(('h', 'm', 'd')):
                return self._parse_lookback(time_str)
            else:
                raise ValueError(f"Unsupported time format: {time_str}")
        except Exception as e:
            raise ValueError(f"Could not parse time '{time_str}': {e}")

    def _transform_response(self, response_data: Dict[str, Any]) -> List[TraceData]:
        """Transform Tempo API response to TraceData objects."""
        traces = []
        
        # Handle different response formats from Tempo
        trace_list = response_data.get('traces', [])
        if not trace_list and 'data' in response_data:
            trace_list = response_data['data']
        
        for trace_data in trace_list:
            spans = []
            for span_data in trace_data.get('spans', []):
                span = SpanData(
                    span_id=span_data.get('spanID', ''),
                    trace_id=span_data.get('traceID', ''),
                    operation_name=span_data.get('operationName', ''),
                    attributes=span_data.get('process', {}).get('tags', {}),
                    start_time=datetime.fromtimestamp(span_data.get('startTime', 0) / 1_000_000),
                    end_time=datetime.fromtimestamp((span_data.get('startTime', 0) + span_data.get('duration', 0)) / 1_000_000)
                )
                spans.append(span)
            
            trace = TraceData(
                trace_id=trace_data.get('traceID', ''),
                spans=spans,
                duration_ms=trace_data.get('duration', 0) // 1000,
                start_time=datetime.fromtimestamp(trace_data.get('startTime', 0) / 1_000_000)
            )
            traces.append(trace)
        
        return traces


# Convenience functions
def create_builder(endpoint: str, timeout: int = 30, default_lookback: str = "1h") -> TraceQLBuilder:
    """Create a TraceQL builder with default configuration."""
    config = TempoConfig(endpoint=endpoint, timeout=timeout, default_lookback=default_lookback)
    client = TempoClient(config)
    return TraceQLBuilder(client, default_lookback)


async def quick_query(endpoint: str, filters: List[str], 
                     fields: Optional[List[str]] = None,
                     lookback: str = "1h") -> TraceQLResult:
    """Execute a quick TraceQL query with minimal setup."""
    builder = create_builder(endpoint, default_lookback=lookback)
    
    # Add filters
    for filter_expr in filters:
        builder.filter(filter_expr)
    
    # Add fields if specified
    if fields:
        builder.select(*fields)
    
    return await builder.execute()


# CLI Integration
import click


@click.group()
def tempo_cli():
    """TraceQL query commands for Tempo."""
    pass


@tempo_cli.command()
@click.option('--endpoint', required=True, help='Tempo query endpoint URL')
@click.option('--timeout', default=30, help='Query timeout in seconds')
@click.option('--lookback', default='1h', help='Time lookback (e.g., 1h, 30m, 2d)')
@click.option('--limit', default=100, help='Maximum number of traces to return')
@click.option('--filters', multiple=True, required=True, help='Filter expressions (can be used multiple times)')
@click.option('--select', 'select_fields', multiple=True, help='Fields to select (can be used multiple times)')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), 
              help='Output format')
def live_query(endpoint, timeout, lookback, limit, filters, select_fields, output_format):
    """Execute live TraceQL query against Tempo.
    
    Example:
        contextcore-mole tempo live-query \\
            --endpoint http://tempo:3200 \\
            --filters 'span.task.status = "cancelled"' \\
            --select span.task.id \\
            --select span.task.title
    """
    async def run_query():
        try:
            # Create builder with configuration
            config = TempoConfig(endpoint=endpoint, timeout=timeout, default_lookback=lookback)
            async with TempoClient(config) as client:
                builder = TraceQLBuilder(client, lookback)
                
                # Add filters
                for filter_expr in filters:
                    builder.filter(filter_expr)
                
                # Add select fields if specified
                if select_fields:
                    builder.select(*select_fields)
                
                # Set limit
                builder.limit(limit)
                
                # Execute query
                result = await builder.execute()
                
                # Output results
                if output_format == 'json':
                    click.echo(result.json(indent=2))
                else:
                    _display_table_results(result)
                    
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()
    
    # Run the async function
    asyncio.run(run_query())


def _display_table_results(result: TraceQLResult):
    """Display query results in table format."""
    click.echo(f"\nQuery: {result.query}")
    click.echo(f"Execution time: {result.execution_time_ms}ms")
    click.echo(f"Total traces found: {result.total_count}")
    click.echo("-" * 80)
    
    if not result.traces:
        click.echo("No traces found.")
        return
    
    # Simple table output
    for i, trace in enumerate(result.traces, 1):
        click.echo(f"\nTrace {i}: {trace.trace_id}")
        click.echo(f"  Duration: {trace.duration_ms}ms")
        click.echo(f"  Spans: {len(trace.spans)}")
        click.echo(f"  Start time: {trace.start_time}")
        
        # Show span details
        for span in trace.spans[:3]:  # Limit to first 3 spans for readability
            click.echo(f"    └─ {span.operation_name} ({span.span_id[:8]}...)")
            # Show relevant attributes
            for key, value in span.attributes.items():
                if key.startswith('task.'):
                    click.echo(f"       {key}: {value}")
        
        if len(trace.spans) > 3:
            click.echo(f"    └─ ... and {len(trace.spans) - 3} more spans")


# Helper functions for time parsing
def _parse_time_range(time_spec: str) -> Tuple[datetime, datetime]:
    """Parse time specification into start and end datetime objects."""
    now = datetime.utcnow()
    
    if time_spec.endswith('h'):
        hours = int(time_spec[:-1])
        start_time = now - timedelta(hours=hours)
        return start_time, now
    elif time_spec.endswith('m'):
        minutes = int(time_spec[:-1])
        start_time = now - timedelta(minutes=minutes)
        return start_time, now
    elif time_spec.endswith('d'):
        days = int(time_spec[:-1])
        start_time = now - timedelta(days=days)
        return start_time, now
    else:
        # Try to parse as ISO format
        try:
            parsed_time = datetime.fromisoformat(time_spec.replace('Z', '+00:00'))
            return parsed_time, now
        except ValueError:
            raise ValueError(f"Unsupported time format: {time_spec}")


# Integration with existing CLI (if needed)
def add_tempo_commands(existing_cli_group):
    """Add Tempo commands to an existing Click group."""
    existing_cli_group.add_command(tempo_cli)


if __name__ == "__main__":
    # Allow module to be run directly for testing
    tempo_cli()