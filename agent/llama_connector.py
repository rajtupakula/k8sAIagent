import requests

class LlamaConnector:
    def __init__(self, host="http://localhost:11434", model="llama3"):
        self.host = host
        self.model = model

    def query(self, prompt, stream=False):
        response = requests.post(
            f"{self.host}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": stream}
        )
        if not stream:
            return response.json().get("response", "")
        return self._stream_response(response)

    def _stream_response(self, response):
        collected = ""
        for line in response.iter_lines():
            if line:
                collected += line.decode()
        return collected
