from flask import Flask, render_template, request, jsonify
import json
import os
import requests
from services.repo_relationship import RepoRelationshipStore
from services.pr_analyzer import PRAnalysisUtility
from services.dependency_mapper import DependencyMapper
from services.context_generator import ContextGenerator
from services.llm_engine import LLMEngine
from services.github_bot import GitHubCommentBot

app = Flask(__name__)

# Initialize services
repo_store = RepoRelationshipStore()
dependency_mapper = DependencyMapper()
context_generator = ContextGenerator()
llm_engine = LLMEngine()
github_bot = GitHubCommentBot()
pr_analyzer = PRAnalysisUtility(repo_store, dependency_mapper, context_generator, llm_engine, github_bot)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/webhook", methods=["POST"])
def github_webhook():
    """Webhook endpoint to receive GitHub PR events"""
    if request.method == "POST":
        payload = request.json
        
        # Verify it's a PR event
        if "pull_request" in payload:
            pr_analyzer.process_pr(payload)
            return jsonify({"status": "Processing PR"}), 200
        
        return jsonify({"status": "Not a PR event"}), 200
    
    return jsonify({"status": "Method not allowed"}), 405


@app.route("/api/relationships", methods=["GET", "POST"])
def manage_relationships():
    """API endpoint to manage repo relationships"""
    if request.method == "GET":
        return jsonify(repo_store.get_all_relationships())
    
    if request.method == "POST":
        data = request.json
        repo_store.add_relationship(data["source"], data["target"], data["relationship_type"])
        return jsonify({"status": "Relationship added"}), 201
