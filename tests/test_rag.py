# Create a test script to verify RAG works
from src.rag.knowledge_builder import KnowledgeBuilder

kb = KnowledgeBuilder()
kb.build_data_patterns_knowledge()
kb.add_business_rules()
kb.add_query_examples()
