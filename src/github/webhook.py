class WebhookListener:
    def is_pull_request_opened(self, payload):
        return payload.get("action") == "opened" and "pull_request" in payload