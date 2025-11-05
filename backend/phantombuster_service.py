import httpx
import os
import json
import csv
import io
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class PhantombusterService:
    """Service for Phantombuster API operations"""
    
    BASE_URL = "https://api.phantombuster.com/api/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-Phantombuster-Key": api_key,
            "Content-Type": "application/json"
        }
    
    async def list_agents(self) -> List[Dict]:
        """List all available Phantombuster agents"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/agents/fetch-all",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to list agents: {str(e)}")
                raise
    
    async def get_agent_output(self, agent_id: str) -> Optional[Dict]:
        """Get latest output from an agent"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/agents/fetch-output",
                    headers=self.headers,
                    params={"id": agent_id},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get agent output: {str(e)}")
                return None
    
    async def launch_agent(self, agent_id: str, arguments: Dict = None) -> Dict:
        """Launch a Phantombuster agent"""
        async with httpx.AsyncClient() as client:
            try:
                payload = {"id": agent_id}
                if arguments:
                    payload["argument"] = arguments
                
                response = await client.post(
                    f"{self.BASE_URL}/agents/launch",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to launch agent: {str(e)}")
                raise
    
    async def get_agent_status(self, agent_id: str) -> Dict:
        """Get agent execution status"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/agents/fetch",
                    headers=self.headers,
                    params={"id": agent_id},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get agent status: {str(e)}")
                raise
    
    async def download_output_file(self, output_url: str) -> str:
        """Download output file content"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(output_url, timeout=60.0)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.error(f"Failed to download output: {str(e)}")
                raise
    
    def parse_csv_output(self, csv_content: str) -> List[Dict]:
        """Parse CSV output from Phantombuster"""
        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)
            return list(reader)
        except Exception as e:
            logger.error(f"Failed to parse CSV: {str(e)}")
            return []
    
    def parse_json_output(self, json_content: str) -> List[Dict]:
        """Parse JSON output from Phantombuster"""
        try:
            data = json.loads(json_content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            return [data]
        except Exception as e:
            logger.error(f"Failed to parse JSON: {str(e)}")
            return []
    
    async def send_linkedin_message(self, profile_url: str, message: str, session_cookie: str) -> Dict:
        """Send LinkedIn message via Phantombuster"""
        # Use LinkedIn Message Sender Phantom (ID: 9227)
        arguments = {
            "sessionCookie": session_cookie,
            "profileUrls": [profile_url],
            "message": message,
            "numberOfMessagesPerLaunch": 1
        }
        
        return await self.launch_agent("9227", arguments)
    
    async def send_connection_request(self, profile_url: str, message: str, session_cookie: str) -> Dict:
        """Send LinkedIn connection request via Phantombuster"""
        # Use LinkedIn Auto Connect Phantom (ID: 2818)
        arguments = {
            "sessionCookie": session_cookie,
            "profileUrls": [profile_url],
            "message": message,
            "numberOfConnectionsPerLaunch": 1
        }
        
        return await self.launch_agent("2818", arguments)
