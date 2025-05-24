import json
import os
from typing import Dict, List, Any

class RepoRelationshipStore:
    """Manages repository relationships for cross-repo PR analysis"""
    
    def __init__(self, storage_path: str = "data/repo_relationships.json"):
        self.storage_path = storage_path
        self.relationships = self._load_relationships()

    def _load_relationships(self) -> Dict:
        """Load relationship data from storage"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        if not os.path.exists(self.storage_path):
            return {"repositories": {}, "relationships": []}
        
        with open(self.storage_path, "r") as f:
            return json.load(f)
    
    def _save_relationships(self):
        """Save relationship data to storage"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        
        with open(self.storage_path, "w") as f:
            json.dump(self.relationships, f, indent=2)
    
    def add_relationship(self, source_repo: str, target_repo: str, relationship_type: str) -> bool:
        """Add a relationship between two repositories"""
        # Add repos if they don't exist
        if source_repo not in self.relationships["repositories"]:
            self.relationships["repositories"][source_repo] = {"name": source_repo}
        
        if target_repo not in self.relationships["repositories"]:
            self.relationships["repositories"][target_repo] = {"name": target_repo}
        
        # Add relationship
        relationship = {
            "source": source_repo,
            "target": target_repo,
            "type": relationship_type
        }
        
        self.relationships["relationships"].append(relationship)
        self._save_relationships()
        return True
    
    def get_related_repos(self, repo_name: str) -> List[str]:
        """Get repositories related to the specified repository"""
        related = []
        
        for rel in self.relationships["relationships"]:
            if rel["source"] == repo_name and rel["target"] not in related:
                related.append(rel["target"])
            elif rel["target"] == repo_name and rel["source"] not in related:
                related.append(rel["source"])
        
        return related
    
    def get_all_relationships(self) -> Dict[str, Any]:
        """Get all repository relationships"""
        return self.relationships
