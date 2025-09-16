import requests
import base64
from typing import Dict, Any, Optional
import streamlit as st
import io

class OpenRouterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Cattle AI Classifier"
        }

    def encode_image_to_base64_from_buffer(self, image_buffer: io.BytesIO) -> str:
        """Convert image buffer to base64 string"""
        try:
            image_buffer.seek(0)
            return base64.b64encode(image_buffer.read()).decode('utf-8')
        except Exception as e:
            st.error(f"Error encoding image: {str(e)}")
            return ""


    def analyze_image_from_buffer(self, image_buffer: io.BytesIO, model: str, system_prompt: str) -> Dict[str, Any]:
        """Send image buffer to OpenRouter for analysis"""
        try:
            # Encode image to base64
            base64_image = self.encode_image_to_base64_from_buffer(image_buffer)
            if not base64_image:
                return {"error": "Failed to encode image"}
            
            # Always use JPEG format since we convert everything to JPEG in memory
            image_format = "jpeg"



            # Prepare the request payload
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please analyze this cattle/buffalo image according to the instructions."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            }

            # Make the API request
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    return {
                        "success": True,
                        "analysis": result['choices'][0]['message']['content'],
                        "model_used": model,
                        "tokens_used": result.get('usage', {}).get('total_tokens', 0)
                    }
                else:
                    return {"error": "No analysis returned from API"}
            else:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_detail = response.json().get('error', {}).get('message', 'Unknown error')
                    error_msg += f" - {error_detail}"
                except:
                    pass
                return {"error": error_msg}

        except requests.exceptions.Timeout:
            return {"error": "Request timed out. Please try again."}
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    def get_available_models(self) -> list:
        """Get list of available models"""
        return [
            "openrouter/sonoma-dusk-alpha",
            "openrouter/sonoma-sky-alpha", 
            "mistralai/mistral-small-3.2-24b-instruct:free",
            "moonshotai/kimi-vl-a3b-thinking:free",
            "meta-llama/llama-4-maverick:free",
            "meta-llama/llama-4-scout:free",
            "qwen/qwen2.5-vl-32b-instruct:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
            "google/gemma-3-4b-it:free",
            "google/gemma-3-12b-it:free",
            "google/gemma-3-27b-it:free",
            "qwen/qwen2.5-vl-72b-instruct:free"
        ]
