import os
import sys
from pathlib import Path

# Add project root to sys.path for lib imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.lib.neo4j_client import neo4j_client

def seed_rbi_rules() -> None:
    """
    Seed initial RBI Section 4.1 rules into Neo4j.
    """
    print("Starting Neo4j seed process...")
    
    # RBI Section 4.1: Prohibited geographic proxies (e.g., PIN code)
    # Regulation node
    regulation_query = """
    MERGE (r:Regulation {name: 'RBI Master Directions on Digital Lending 2022'})
    SET r.code = 'RBI/2022-23/112',
        r.authority = 'Reserve Bank of India',
        r.status = 'ACTIVE'
    RETURN r
    """
    
    # Rule node
    rule_query = """
    MERGE (rule:Rule {id: 'RBI_DL_4.1'})
    SET rule.title = 'Prohibition of Geographic Proxies',
        rule.description = 'Lending models must not use geographic proxies such as PIN code for credit decisions.',
        rule.section = '4.1',
        rule.prohibited_features = ['pin_code', 'postal_code']
    RETURN rule
    """
    
    # Relationship
    relation_query = """
    MATCH (r:Regulation {name: 'RBI Master Directions on Digital Lending 2022'})
    MATCH (rule:Rule {id: 'RBI_DL_4.1'})
    MERGE (r)-[rel:HAS_RULE]->(rule)
    RETURN count(rel) as rel_count
    """

    try:
        neo4j_client.connect()
        print("Connected to Neo4j.")

        print("Seeding Regulation...")
        reg = neo4j_client.run_query(regulation_query)
        print(f"Regulation seeded: {reg[0]['r']['name']}")

        print("Seeding Rule...")
        rule = neo4j_client.run_query(rule_query)
        print(f"Rule seeded: {rule[0]['rule']['title']}")

        print("Creating Relationship...")
        rel = neo4j_client.run_query(relation_query)
        print(f"Relationship created: {rel[0]['rel_count']}")

        # Verification Read Query
        print("\n--- Verification Query ---")
        verify_query = """
        MATCH (r:Regulation)-[:HAS_RULE]->(rule:Rule)
        RETURN r.name AS regulation, rule.id AS rule_id, rule.title AS rule_title
        """
        results = neo4j_client.run_query(verify_query)
        for row in results:
            print(f"Relation Detected: {row['regulation']} -> {row['rule_id']} ({row['rule_title']})")

    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)
    finally:
        neo4j_client.close()
        print("Neo4j connection closed.")

if __name__ == "__main__":
    seed_rbi_rules()
