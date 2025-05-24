from typing import Dict, List, Any

class DependencyMapper:
    """Maps component interactions within and across services"""
    
    def __init__(self):
        pass
    
    def analyze_impacts(self, diffs: List[Dict[str, Any]], repository: str, related_repos: List[str]) -> Dict[str, Any]:
        """Analyze code diffs to identify impacted components"""
        impacted_modules = self._identify_impacted_modules(diffs)
        impacted_tests = self._identify_impacted_tests(impacted_modules, repository)
        cross_repo_impacts = self._identify_cross_repo_impacts(impacted_modules, related_repos)
        
        return {
            "impacted_modules": impacted_modules,
            "impacted_tests": impacted_tests,
            "cross_repo_impacts": cross_repo_impacts
        }
    
    def _identify_impacted_modules(self, diffs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify modules impacted by code changes"""
        impacted_modules = []
        
        for diff in diffs:
            file_path = diff["file_path"]
            
            # Java file analysis - extract package and class info
            if file_path.endswith(".java"):
                package = self._extract_package_from_path(file_path)
                class_name = self._extract_class_from_path(file_path)
                
                impacted_modules.append({
                    "file_path": file_path,
                    "package": package,
                    "class_name": class_name,
                    "type": "java_class"
                })
            
            # Handle other file types if needed
            
        return impacted_modules
    
    def _identify_impacted_tests(self, impacted_modules: List[Dict[str, Any]], repository: str) -> List[Dict[str, Any]]:
        """Identify tests that should be run based on impacted modules"""
        # This would involve static analysis to map tests to implementation classes
        # For now, return placeholder data
        impacted_tests = []
        
        for module in impacted_modules:
            if module["type"] == "java_class" and "Service" in module["class_name"]:
                test_name = f"{module['class_name']}Test"
                test_path = f"src/test/java/{module['package'].replace('.', '/')}/{test_name}.java"
                
                impacted_tests.append({
                    "test_name": test_name,
                    "test_path": test_path,
                    "related_module": module["class_name"]
                })
        
        return impacted_tests
    
    def _identify_cross_repo_impacts(self, impacted_modules: List[Dict[str, Any]], related_repos: List[str]) -> List[Dict[str, Any]]:
        """Identify potential impacts on related repositories"""
        # This would involve analyzing how services use each other
        # For now, return placeholder data
        cross_repo_impacts = []
        
        for module in impacted_modules:
            if module["type"] == "java_class" and "Api" in module["class_name"]:
                for repo in related_repos:
                    cross_repo_impacts.append({
                        "repository": repo,
                        "affected_by": module["class_name"],
                        "potential_impact": "API contract change may affect consumers"
                    })
        
        return cross_repo_impacts
    
    def _extract_package_from_path(self, file_path: str) -> str:
        """Extract Java package from file path"""
        if "java/" in file_path and file_path.endswith(".java"):
            path_parts = file_path.split("java/")[1].split("/")
            package_parts = path_parts[:-1]  # Exclude the file name
            return ".".join(package_parts)
        return ""
    
    def _extract_class_from_path(self, file_path: str) -> str:
        """Extract Java class name from file path"""
        if file_path.endswith(".java"):
            return file_path.split("/")[-1].replace(".java", "")
        return ""
