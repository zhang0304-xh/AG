from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any, Optional
import logging

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        
    async def close(self):
        await self.driver.close()

    async def get_node_by_id(self, node_id: int) -> Optional[Dict]:
        query = (
            "MATCH (n) "
            "WHERE id(n) = $node_id "
            "RETURN n"
        )
        try:
            async with self.driver.session() as session:
                result = await session.run(query, node_id=node_id)
                record = await result.single()
                return dict(record["n"]) if record else None
        except Exception as e:
            logging.error(f"Error getting node: {str(e)}")
            return None

    async def get_nodes_by_label(self, label: str) -> List[Dict]:
        query = f"MATCH (n:{label}) RETURN n"
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                records = await result.data()
                return [dict(record["n"]) for record in records]
        except Exception as e:
            logging.error(f"Error getting nodes by label: {str(e)}")
            return []

    async def get_relationships(self, start_node_id: int, relationship_type: str = None) -> List[Dict]:
        query = (
            "MATCH (start)-[r]->(end) "
            "WHERE id(start) = $start_id "
            + (f"AND type(r) = '{relationship_type}' " if relationship_type else "")
            + "RETURN type(r) as type, id(end) as end_id, properties(r) as properties"
        )
        try:
            async with self.driver.session() as session:
                result = await session.run(query, start_id=start_node_id)
                records = await result.data()
                return records
        except Exception as e:
            logging.error(f"Error getting relationships: {str(e)}")
            return []

    async def update_relationship(self, start_node_id: int, end_node_id: int, relationship_type: str, properties: Dict[str, Any]) -> bool:
        query = (
            "MATCH (start)-[r:" + relationship_type + "]->(end) "
            "WHERE id(start) = $start_id AND id(end) = $end_id "
            "SET r += $properties "
            "RETURN r"
        )
        try:
            async with self.driver.session() as session:
                result = await session.run(
                    query,
                    start_id=start_node_id,
                    end_id=end_node_id,
                    properties=properties
                )
                return await result.single() is not None
        except Exception as e:
            logging.error(f"Error updating relationship: {str(e)}")
            return False