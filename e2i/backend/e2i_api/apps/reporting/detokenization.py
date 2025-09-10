# e2i_api/apps/reporting/detokenization.py

from typing import Any, List, Dict
from django.conf import settings
import httpx
import logging

logger = logging.getLogger(__name__)

class DetokenizationService:
    """
    Production detokenization service that calls the real tokenization service.
    """
    
    def __init__(self):
        self.endpoint = getattr(settings, 'DETOKENIZATION_ENDPOINT', None)
        self.api_key = getattr(settings, 'DETOKENIZATION_API_KEY', None)
        self.timeout = int(getattr(settings, 'DETOKENIZATION_TIMEOUT', 30))
        
        if not self.endpoint or not self.api_key:
            logger.error("Tokenization service endpoint or API key not configured!")
    
    def detokenize_row(self, row: List[Any], column_names: List[str] = None) -> List[Any]:
        """
        Detokenize a single row of data.
        """
        if not column_names:
            return row
            
        # Collect all tokens that need detokenization
        tokens_to_detokenize = []
        token_positions = []
        
        for i, value in enumerate(row):
            column_name = column_names[i] if i < len(column_names) else f"col_{i}"
            
            if self._is_tokenized_value(value, column_name):
                tokens_to_detokenize.append(str(value))
                token_positions.append(i)
        
        if not tokens_to_detokenize:
            return row  # No tokens to detokenize
        
        # Get detokenized values from tokenization service
        detokenized_mapping = self._call_tokenization_service(tokens_to_detokenize)
        
        # Replace tokens with detokenized values
        result_row = list(row)
        for pos, token in zip(token_positions, tokens_to_detokenize):
            if token in detokenized_mapping:
                result_row[pos] = detokenized_mapping[token]
            else:
                logger.warning(f"Failed to detokenize token: {token[:8]}...")
                result_row[pos] = f"[REDACTED: {str(row[pos])[:8]}...]"
        
        return result_row
    
    def detokenize_rows(self, rows: List[List[Any]], column_names: List[str] = None) -> List[List[Any]]:
        """
        Detokenize multiple rows efficiently by batching tokenization service calls.
        """
        if not rows or not column_names:
            return rows
            
        # Collect ALL tokens from ALL rows for efficient batching
        all_tokens = set()
        for row in rows:
            for i, value in enumerate(row):
                column_name = column_names[i] if i < len(column_names) else f"col_{i}"
                if self._is_tokenized_value(value, column_name):
                    all_tokens.add(str(value))
        
        if not all_tokens:
            return rows  # No tokens to detokenize
        
        # Get all detokenized values in one API call
        detokenized_mapping = self._call_tokenization_service(list(all_tokens))
        
        # Apply detokenization to all rows
        result_rows = []
        for row in rows:
            result_row = list(row)
            for i, value in enumerate(row):
                column_name = column_names[i] if i < len(column_names) else f"col_{i}"
                if self._is_tokenized_value(value, column_name):
                    token = str(value)
                    if token in detokenized_mapping:
                        result_row[i] = detokenized_mapping[token]
                    else:
                        result_row[i] = f"[REDACTED: {token[:8]}...]"
            result_rows.append(result_row)
        
        return result_rows
    
    def _is_tokenized_value(self, value: Any, column_name: str) -> bool:
        """
        Determine if a value is tokenized and needs detokenization.
        """
        if not isinstance(value, str):
            return False
            
        # Check for hash-like values in name fields (64 hex characters)
        if column_name == 'name' and len(value) == 64 and all(c in '0123456789abcdef' for c in value.lower()):
            return True
            
        # Add more token detection logic as needed
        return False
    
    def _call_tokenization_service(self, tokens: List[str]) -> Dict[str, str]:
        """
        Call the production tokenization service to detokenize tokens.
        """
        if not self.endpoint or not self.api_key:
            logger.error("Tokenization service not properly configured")
            return {}
            
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.endpoint}/api/v1/detokenize",
                    json={"tokens": tokens},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                mappings = result.get("mappings", {})
                
                logger.info(f"Successfully detokenized {len(mappings)}/{len(tokens)} tokens")
                return mappings
                
        except httpx.TimeoutException:
            logger.error("Tokenization service timeout")
            return {}
        except httpx.HTTPStatusError as e:
            logger.error(f"Tokenization service HTTP error: {e.response.status_code}")
            return {}
        except Exception as e:
            logger.error(f"Tokenization service call failed: {e}")
            return {}

# Global instance
detokenization_service = DetokenizationService()