import neo4j


GraphDatabase = neo4j.GraphDatabase

class Neo4jClient:
    def __init__(self):
        # 在这里设置你的Neo4j连接信息
        uri = "bolt://localhost:7687"
        user = "neo4j"
        password = "123456"
        self.client = GraphDatabase.driver(uri, auth=(user, password))

    def execute_query(self, query, parameters=None):
        with self.client.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

    def get_node_by_id(self, node_id):
        query = "MATCH (n) WHERE ID(n) = $node_id RETURN n"
        return self.execute_query(query, {'node_id': node_id})

    def create_node(self, label, properties):
        query = f"CREATE (n:{label} $props) RETURN n"
        return self.execute_query(query, {'props': properties})

    def create_relationship(self, start_id, end_id, rel_type, properties=None):
        query = """
        MATCH (a), (b)
        WHERE ID(a) = $start_id AND ID(b) = $end_id
        CREATE (a)-[r:{rel_type} $props]->(b)
        RETURN r
        """.format(rel_type=rel_type)
        return self.execute_query(query, {'start_id': start_id, 'end_id': end_id, 'props': properties or {}})


if __name__ == '__main__':
    # neo4j.bat console
    neo4j_client = Neo4jClient()
    result = neo4j_client.get_node_by_id(16)
    print(result)
