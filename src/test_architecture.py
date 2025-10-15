"""
Test Architecture Component - Added While Server Was Down
This demonstrates the "never lose commits" feature of Lekhak AI
"""

class ArchitectureManager:
    """
    New architecture component for managing system architecture
    
    This was added while the server was down to test the commit bus.
    When the server comes back up, this should be automatically documented.
    """
    
    def __init__(self, config: dict):
        """
        Initialize architecture manager
        
        Args:
            config: Configuration dictionary with architecture settings
        """
        self.config = config
        self.components = []
    
    def add_component(self, name: str, component_type: str, metadata: dict = None):
        """
        Add a new architectural component
        
        Args:
            name: Component name
            component_type: Type of component (service, database, cache, etc.)
            metadata: Additional metadata about the component
        
        Returns:
            Component ID
        """
        component = {
            'name': name,
            'type': component_type,
            'metadata': metadata or {},
            'status': 'active'
        }
        self.components.append(component)
        return len(self.components) - 1
    
    def get_component(self, component_id: int):
        """
        Get component by ID
        
        Args:
            component_id: Component identifier
        
        Returns:
            Component dictionary or None
        """
        if 0 <= component_id < len(self.components):
            return self.components[component_id]
        return None
    
    def list_components(self, component_type: str = None):
        """
        List all components, optionally filtered by type
        
        Args:
            component_type: Optional filter by component type
        
        Returns:
            List of components
        """
        if component_type:
            return [c for c in self.components if c['type'] == component_type]
        return self.components
    
    def update_component_status(self, component_id: int, status: str):
        """
        Update component status
        
        Args:
            component_id: Component identifier
            status: New status (active, inactive, deprecated)
        
        Returns:
            True if updated, False otherwise
        """
        component = self.get_component(component_id)
        if component:
            component['status'] = status
            return True
        return False


# Example usage
if __name__ == "__main__":
    # Initialize architecture manager
    arch = ArchitectureManager({'version': '1.0'})
    
    # Add components
    db_id = arch.add_component('PostgreSQL', 'database', {'version': '15'})
    cache_id = arch.add_component('Redis', 'cache', {'version': '7'})
    api_id = arch.add_component('FastAPI', 'service', {'port': 8000})
    
    # List all components
    print("All components:", arch.list_components())
    
    # List only databases
    print("Databases:", arch.list_components('database'))
    
    # Update status
    arch.update_component_status(cache_id, 'deprecated')
    print("Updated cache status:", arch.get_component(cache_id))
